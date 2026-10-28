import pytest
from conftest import create


def batch():
    return {"version": 1, "coordinator": "coord", "agents": [
        {"key": "coord", "name": "Coordinador", "delegates": ["analista"]},
        {"key": "analista", "name": "Analista", "tools": ["excel.read", "excel.chart"]}]}


def test_preview_and_atomic_import_with_coordinator_tools_and_delegations(client):
    office = create(client, "offices", name="Importada")
    path = f"/api/offices/{office['id']}/agents/import"
    assert client.post(path, json=batch()).json()["created"] is False
    assert client.get("/api/agents").json() == []
    response = client.post(path + "?preview=false", json=batch())
    assert response.status_code == 200, response.text
    ids = response.json()["ids"]
    assert len(client.get("/api/agents").json()) == 2
    positions = [a["position"] for a in client.get("/api/agents").json()]
    assert positions[0] != positions[1]
    assert client.get(f"/api/offices/{office['id']}").json()["coordinator_id"] == ids["coord"]
    edges = client.get("/api/relations").json()
    assert [(r["source_id"], r["target_id"]) for r in edges] == [(ids["coord"], ids["analista"])]
    assignments = client.get(f"/api/agents/{ids['analista']}/assignments").json()
    assert len(assignments["tools"]) == 2
    assert assignments["resources"] == []
    assert assignments["connections"] == []
    assert client.post(path + "?preview=false", json=batch()).status_code == 422
    assert len(client.get("/api/agents").json()) == 2


@pytest.mark.parametrize("invalid", [
    {"key": "analista", "name": "Otro", "tools": ["inexistente"]},
    {"key": "coord", "name": "Otro"},
    {"key": "analista", "name": "Otro", "delegates": ["coord"]},
    {"key": "analista", "name": "Otro", "delegates": ["no-existe"]},
    {"key": "analista", "name": "Otro", "position": {"x": 1}},
    {"key": "analista", "name": "Otro", "status": "working"},
    {"key": "analista", "name": "Otro", "api_key": "do-not-store"},
])
def test_invalid_second_agent_never_creates_first(client, invalid):
    office = create(client, "offices", name="Atomicidad")
    data = batch()
    data["agents"][1] = invalid
    response = client.post(f"/api/offices/{office['id']}/agents/import?preview=false", json=data)
    assert response.status_code == 422, response.text
    assert client.get("/api/agents").json() == []
    assert client.get("/api/relations").json() == []
    assert client.get(f"/api/offices/{office['id']}").json()["coordinator_id"] is None


def test_foreign_office_and_existing_coordinator_are_preserved(client):
    office = create(client, "offices", name="Destino")
    other = create(client, "offices", name="Otra")
    original = create(client, "agents", name="Original", office_id=office["id"])
    client.patch(f"/api/offices/{office['id']}", json={"coordinator_id": original["id"]})
    path = f"/api/offices/{office['id']}/agents/import?preview=false"
    assert client.post(path, json=batch()).status_code == 422
    data = batch()
    data.pop("coordinator")
    data["agents"][1]["office_id"] = other["id"]
    assert client.post(path, json=data).status_code == 422
    data["agents"][1].pop("office_id")
    assert client.post(path, json=data).status_code == 200
    assert client.get(f"/api/offices/{office['id']}").json()["coordinator_id"] == original["id"]
