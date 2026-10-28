import json
import threading

import pytest
from app.agents.engine import model_tool_result
from app.ai.providers import providers
from app.tools import network, sandbox
from conftest import create, wait_task
from test_agents import ScriptedProvider
from test_stage3_tools import run, setup


def test_brave_search_contract_without_real_key_or_paid_call(client, tmp_path, monkeypatch):
    office, agent, _ = setup(client, tmp_path)
    connection = create(client, "connections", name="Brave de prueba", kind="web_search", config={"provider": "brave"})
    assignments = client.get(f"/api/agents/{agent['id']}/assignments").json()
    assignments["connections"] = [{"connection_id": connection["id"], "permissions": ["connect", "select"]}]
    client.put(f"/api/agents/{agent['id']}/assignments", json=assignments)
    # TEST ONLY: no credentials are stored and no search provider is billed.
    monkeypatch.setattr(network.secrets, "get", lambda ref: "contract-test-key")
    def transport(url, authorize, **kwargs):
        assert "search_lang=es" in url and "freshness=pw" in url
        assert kwargs["headers"]["X-Subscription-Token"] == "contract-test-key"
        return {"status": 200, "body": json.dumps({"web": {"results": [{"title": "Resultado de contrato", "url": "https://example.org", "description": "Fixture", "page_age": "2026-10-08"}]}}).encode(),
                "consulted_at": "2026-10-08T00:00:00Z"}
    monkeypatch.setattr(network, "request", transport)
    result = run(client, office, agent, "web.search", {"query": "fútbol", "language": "es", "date_range": "pw", "max_results": 1})
    assert result["status"] == "completed", result
    assert json.loads(result["result"])["results"][0]["source"] == "Brave Search"
    details = client.get(f"/api/tasks/{result['id']}/details").json()
    assert "contract-test-key" not in json.dumps(details)


def test_sandbox_concurrency_limit_rejects_extra_jobs(monkeypatch):
    slots = threading.BoundedSemaphore(2)
    assert slots.acquire() and slots.acquire()
    monkeypatch.setattr(sandbox, "_slots", slots)
    with pytest.raises(ValueError, match="simultáneas"):
        sandbox.execute_python(None, None, None, "not executed", [], 1)
    slots.release()
    slots.release()


def test_large_api_results_do_not_fill_model_context():
    result = {"data": [{"match_id": index, "text": "dato" * 200} for index in range(500)], "status": 200}
    preview = model_tool_result(result)
    assert preview["preview_only"]
    assert len(json.dumps(preview)) < 3000
    assert len(result["data"]) == 500


def test_delegation_executes_real_file_tool_with_child_permissions(client, tmp_path, monkeypatch):
    office = create(client, "offices", name="Orquestación Etapa 3")
    provider = client.get("/api/providers").json()[0]
    parent = create(client, "agents", name="Coordinador", office_id=office["id"], provider_id=provider["id"], model="contract-only")
    child = create(client, "agents", name="Creador", office_id=office["id"], provider_id=provider["id"], model="contract-only")
    resource = create(client, "resources", name="Archivos de prueba", path=str(tmp_path))
    tool = next(t for t in client.get("/api/tools").json() if t["name"] == "filesystem.write")
    client.put(f"/api/agents/{child['id']}/assignments", json={"tools": [tool["id"]],
               "resources": [{"resource_id": resource["id"], "permissions": ["read", "create"]}]})
    create(client, "relations", source_id=parent["id"], target_id=child["id"])
    fixture = ScriptedProvider({parent["id"]: [
        {"type": "delegate", "agent_id": child["id"], "request": "Crear evidencia.txt"},
        {"type": "final", "content": "Archivo confirmado por la herramienta del hijo"}],
        child["id"]: [{"type": "tool", "name": "filesystem.write", "arguments": {"resource_id": resource["id"], "path": "evidencia.txt", "content": "Verificación de delegación real"}},
                       {"type": "final", "content": "evidencia.txt creado con herramienta"}]})
    monkeypatch.setitem(providers, "ollama", fixture)
    task = create(client, "tasks", office_id=office["id"], agent_id=parent["id"], request="Delega creación de evidencia")
    assert wait_task(client, task["id"])["status"] == "completed"
    assert (tmp_path / "evidencia.txt").read_text(encoding="utf-8") == "Verificación de delegación real"
    details = client.get(f"/api/tasks/{task['id']}/details").json()
    assert any(e["agent_id"] == child["id"] and e["tool_name"] == "filesystem.write" and e["status"] == "completed" for e in details["executions"])
    assert details["messages"] and details["artifacts"]
