import sqlite3

from app.core.config import DATA_DIR
from app.core.db import SessionLocal
from app.models import Execution, Task
from app.security.windows_runtime import windows_runtime
from conftest import create


def test_sqlite_backup_contains_persistent_data(client):
    office = create(client, "offices", name="Backup oficina")
    response = client.post("/api/backups")
    assert response.status_code == 200, response.text
    name = response.json()["name"]
    with sqlite3.connect(DATA_DIR / "backups" / name) as db:
        assert db.execute("SELECT name FROM offices WHERE id=?", (office["id"],)).fetchone()[0] == "Backup oficina"
    assert client.get(f"/api/backups/{name}/download").status_code == 200
    assert client.get("/api/backups/not-a-backup/download").status_code == 422


def test_consumption_preserves_unknown_cost(client):
    office = create(client, "offices", name="O")
    agent = create(client, "agents", name="A", office_id=office["id"])
    with SessionLocal() as session:
        task = Task(
            number="TEST-consumption", office_id=office["id"], agent_id=agent["id"], request="test", status="completed"
        )
        session.add(task)
        session.flush()
        session.add_all(
            [
                Execution(
                    task_id=task.id,
                    agent_id=agent["id"],
                    provider="ollama",
                    model="local",
                    tokens_in=10,
                    tokens_out=20,
                    cost=0,
                    status="completed",
                ),
                Execution(
                    task_id=task.id,
                    agent_id=agent["id"],
                    provider="openai",
                    model="test",
                    tokens_in=100,
                    tokens_out=200,
                    cost=None,
                    status="completed",
                ),
            ]
        )
        session.commit()
    result = client.get("/api/consumption").json()
    assert result["total"]["local_calls"] == 1
    assert result["total"]["external_calls"] == 1
    assert result["total"]["unpriced_calls"] == 1
    assert result["day"]["tokens_in"] == 110
    assert result["by_office"][office["id"]]["tokens_out"] == 220


def test_runtime_does_not_accept_arbitrary_paths(client):
    assert client.post("/api/artifacts/nonexistent/open").status_code == 422
    assert ".exe" not in windows_runtime.SAFE_EXTENSIONS
    assert ".ps1" not in windows_runtime.SAFE_EXTENSIONS


def test_websocket_authenticated_progress(client):
    office = create(client, "offices", name="O")
    agent = create(client, "agents", name="A", office_id=office["id"])
    with SessionLocal() as session:
        task = Task(
            number="TEST-websocket",
            office_id=office["id"],
            agent_id=agent["id"],
            request="test",
            status="completed",
            result="ready",
        )
        session.add(task)
        session.commit()
        id = task.id
    with client.websocket_connect(f"/ws/tasks/{id}", headers={"Origin": "http://127.0.0.1:1420"}) as socket:
        socket.send_json({"token": "test-session-only"})
        result = socket.receive_json()
        assert result["task"]["status"] == "completed"
        assert result["task"]["result"] == "ready"
