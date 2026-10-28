import pytest
from conftest import create


def batch():
    return {"version": 1, "skills": [
        {"name": "Graficar ventas", "instructions": "Lee y agrupa usando herramientas reales.", "required_tools": ["excel.read", "excel.chart"]},
        {"name": "Revisar entregables", "instructions": "Verifica los archivos antes de informar resultados.", "examples": "Revisar ventas.xlsx", "output_format": "Hallazgos y evidencias"}]}


def test_preview_import_and_ids_without_granting_agent_permissions(client):
    office = create(client, "offices", name="Habilidades")
    agent = create(client, "agents", name="Analista", office_id=office["id"])
    assert client.post("/api/skills/import", json=batch()).json()["created"] is False
    assert client.get("/api/skills").json() == []
    response = client.post("/api/skills/import?preview=false", json=batch())
    assert response.status_code == 200, response.text
    assert len(response.json()["ids"]) == 2
    skills = client.get("/api/skills").json()
    tools = client.get("/api/tools").json()
    saved = next(s for s in skills if s["name"] == "Graficar ventas")
    assert set(saved["required_tools"]) == {t["id"] for t in tools if t["name"] in {"excel.read", "excel.chart"}}
    assert client.get(f"/api/agents/{agent['id']}/assignments").json()["skills"] == []
    assert client.post("/api/skills/import?preview=false", json=batch()).status_code == 422
    assert len(client.get("/api/skills").json()) == 2


@pytest.mark.parametrize("invalid", [
    {"name": "graficar VENTAS", "instructions": "Duplicada"},
    {"name": "Otra", "instructions": "Válida", "required_tools": ["inexistente"]},
    {"name": "Otra", "instructions": "   "},
    {"name": "Otra", "instructions": "Válida", "api_key": "no-guardar"},
])
def test_invalid_second_skill_rolls_back_entire_batch(client, invalid):
    data = batch()
    data["skills"][1] = invalid
    assert client.post("/api/skills/import?preview=false", json=data).status_code == 422
    assert client.get("/api/skills").json() == []


def test_required_tools_accept_ids_but_reject_inactive_tools(client):
    tool = next(t for t in client.get("/api/tools").json() if t["name"] == "excel.read")
    data = {"skills": [{"name": "Lectura", "instructions": "Lee Excel real", "required_tools": [tool["id"]]}]}
    assert client.post("/api/skills/import", json=data).status_code == 200
    assert client.patch(f"/api/tools/{tool['id']}", json={"active": False}).status_code == 200
    assert client.post("/api/skills/import?preview=false", json=data).status_code == 422
    assert client.get("/api/skills").json() == []
