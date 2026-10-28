import pytest
from conftest import create
from starlette.websockets import WebSocketDisconnect


def test_office_websocket_auth_and_updates(client):
    office = create(client, "offices", name="En vivo")
    agent = create(client, "agents", name="Ana", office_id=office["id"])
    endpoint = f"/ws/offices/{office['id']}"
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(endpoint, headers={"origin": "https://invalid.example"}) as socket:
            socket.receive_json()
    with client.websocket_connect(endpoint, headers={"origin": "http://127.0.0.1:1420"}) as socket:
        socket.send_json({"token": "incorrect"})
        with pytest.raises(WebSocketDisconnect):
            socket.receive_json()
    with client.websocket_connect(endpoint, headers={"origin": "http://127.0.0.1:1420"}) as socket:
        socket.send_json({"token": "test-session-only"})
        initial = socket.receive_json()
        assert initial["agents"][0]["id"] == agent["id"]
        client.patch(f"/api/agents/{agent['id']}", json={"status": "disabled"})
        updated = socket.receive_json()
        assert updated["agents"][0]["status"] == "disabled"
        client.put(
            f"/api/offices/{office['id']}/layout", json={"revision": 0, "desks": {agent["id"]: {"x": 450, "y": 250}}}
        )
        updated = socket.receive_json()
        assert updated["layout"]["revision"] == 1


def test_ollama_status_requires_installed_model(client, monkeypatch):
    import httpx
    from app.http import runtime

    office = create(client, "offices", name="Modelos")
    provider = client.get("/api/providers").json()[0]
    agent = create(
        client, "agents", name="Ana", office_id=office["id"], provider_id=provider["id"], model="installed:latest"
    )
    original = httpx.AsyncClient
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"models": [{"name": "installed:latest"}]})
    )
    monkeypatch.setattr(runtime.httpx, "AsyncClient", lambda **kwargs: original(transport=transport, **kwargs))
    status = client.get("/api/ollama/status").json()
    assert status["reachable"] is True
    assert status["providers"][0]["ready_agents"] == [agent["id"]]
    client.patch(f"/api/agents/{agent['id']}", json={"model": "missing:latest"})
    assert client.get("/api/ollama/status").json()["ready_agents"] == 0


def test_ollama_status_reports_unreachable(client, monkeypatch):
    import httpx
    from app.http import runtime

    original = httpx.AsyncClient

    def unavailable(request):
        raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr(
        runtime.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(unavailable), **kwargs)
    )
    status = client.get("/api/ollama/status").json()
    assert status["reachable"] is False
    assert status["ready_agents"] == 0


def test_scene_layout_persistence_and_conflict(client):
    office = create(client, "offices", name="Plano")
    agent = create(client, "agents", name="Ana", office_id=office["id"])
    url = f"/api/offices/{office['id']}"
    initial = client.get(url + "/scene").json()
    assert initial["agents"][0]["id"] == agent["id"]
    payload = {"revision": 0, "desks": {agent["id"]: {"x": 320, "y": 250}}}
    assert client.put(url + "/layout", json=payload).status_code == 200
    assert client.put(url + "/layout", json=payload).status_code == 409
    assert client.get(url + "/scene").json()["layout"]["desks"][agent["id"]]["x"] == 320
    assert client.get("/api/agents/" + agent["id"]).json()["position"] == agent["position"]
    clone = client.post(url + "/duplicate").json()
    copied = client.get(f"/api/offices/{clone['id']}/scene").json()
    assert agent["id"] not in copied["layout"]["desks"]
    assert copied["agents"][0]["id"] in copied["layout"]["desks"]


def test_scene_rejects_foreign_agents_and_bad_coordinates(client):
    office = create(client, "offices", name="Uno")
    other = create(client, "offices", name="Dos")
    agent = create(client, "agents", name="Ana", office_id=other["id"])
    url = f"/api/offices/{office['id']}/layout"
    assert client.put(url, json={"revision": 0, "desks": {agent["id"]: {"x": 320, "y": 250}}}).status_code == 422
    assert client.put(url, json={"revision": 0, "desks": {agent["id"]: {"x": -1, "y": 250}}}).status_code == 422
    assert client.get(f"/api/offices/{office['id']}/scene", headers={"Authorization": ""}).status_code == 401


def test_scene_activity_exposes_operation_error_and_newer_task(client, tmp_path):
    from datetime import datetime, timedelta, timezone

    from app.core.db import SessionLocal
    from app.models import Execution, Task

    office = create(client, "offices", name="Actividad")
    agent = create(client, "agents", name="Ana", office_id=office["id"])
    resource = create(client, "resources", name="Prueba Oficina", path=str(tmp_path))
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        task = Task(
            number="activity-old",
            office_id=office["id"],
            agent_id=agent["id"],
            request="Lee ventas",
            status="error",
            created_at=now,
        )
        session.add(task)
        session.flush()
        session.add(
            Execution(
                task_id=task.id,
                agent_id=agent["id"],
                tool_name="excel.read",
                status="error",
                input={"resource_id": resource["id"], "path": "/ventas", "password": "hidden-secret"},
                error="La ruta resuelta escapa del recurso autorizado token=private",
                created_at=now + timedelta(seconds=1),
            )
        )
        session.commit()
    endpoint = f"/api/offices/{office['id']}/scene"
    activity = client.get(endpoint).json()["agents"][0]["activity"]
    assert activity["tool"] == "excel.read"
    assert activity["path"] == "/ventas"
    assert activity["resource"] == "Prueba Oficina"
    assert "escapa" in activity["error"]
    assert "private" not in activity["error"]
    assert "hidden-secret" not in str(activity)
    with SessionLocal() as session:
        session.add(
            Task(
                number="activity-new",
                office_id=office["id"],
                agent_id=agent["id"],
                request="Nueva tarea",
                status="pending",
                created_at=now + timedelta(seconds=2),
            )
        )
        session.commit()
    activity = client.get(endpoint).json()["agents"][0]["activity"]
    assert activity["request"] == "Nueva tarea"
    assert activity["error"] == ""
    assert activity["tool"] == ""
