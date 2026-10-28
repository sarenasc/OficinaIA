import pytest
from app.ai.providers import ModelCallError, providers
from conftest import create, wait_task
from test_agents import ScriptedProvider


def person(client):
    office = create(client, 'offices', name='Formato IA')
    provider = client.get('/api/providers').json()[0]
    agent = create(client, 'agents', name='Investigador', office_id=office['id'], provider_id=provider['id'], model='fixture')
    tool = next(t for t in client.get('/api/tools').json() if t['name'] == 'agents.list')
    client.put(f"/api/agents/{agent['id']}/assignments", json={'tools': [tool['id']]})
    return office, agent


def test_corrects_model_format_once_without_repeating_finished_tool(client, monkeypatch):
    office, agent = person(client)
    fixture = ScriptedProvider({agent['id']: [
        {'type': 'tool', 'name': 'agents.list', 'arguments': {}},
        ModelCallError('Respuesta sin JSON', 'invalid_model_action'),
        {'type': 'final', 'content': 'Resultado recuperado'},
    ]})
    monkeypatch.setitem(providers, 'ollama', fixture)
    task = create(client, 'tasks', office_id=office['id'], agent_id=agent['id'], request='Consulta el equipo')
    done = wait_task(client, task['id'])
    assert done['status'] == 'completed', done
    assert done['result'] == 'Resultado recuperado'
    details = client.get(f"/api/tasks/{task['id']}/details").json()
    assert sum(e['tool_name'] == 'agents.list' for e in details['executions']) == 1
    assert sum(e['action'] == 'model.format_retry' for e in details['audit']) == 1
    assert len(fixture.calls) == 3


@pytest.mark.parametrize('category,attempts', [
    ('invalid_model_action', 2), ('model_timeout', 1), ('provider_http', 1),
    ('provider_response', 1), ('model_truncated', 1), ('model_refusal', 1),
])
def test_retries_only_invalid_actions_and_only_once(client, monkeypatch, category, attempts):
    office, agent = person(client)
    fixture = ScriptedProvider({agent['id']: [ModelCallError('Error de prueba', category) for _ in range(attempts)]})
    monkeypatch.setitem(providers, 'ollama', fixture)
    task = create(client, 'tasks', office_id=office['id'], agent_id=agent['id'], request='Consulta el equipo')
    assert wait_task(client, task['id'])['status'] == 'error'
    assert len(fixture.calls) == attempts


def test_no_format_retry_when_a_fallback_already_timed_out(client, monkeypatch):
    office, agent = person(client)
    provider = client.get('/api/providers').json()[0]
    client.patch(f"/api/agents/{agent['id']}", json={'fallbacks': [{'provider_id': provider['id'], 'model': 'other-fixture'}]})
    fixture = ScriptedProvider({agent['id']: [ModelCallError('Tiempo agotado', 'model_timeout'),
                                            ModelCallError('Formato incorrecto', 'invalid_model_action')]})
    monkeypatch.setitem(providers, 'ollama', fixture)
    task = create(client, 'tasks', office_id=office['id'], agent_id=agent['id'], request='Consulta')
    assert wait_task(client, task['id'])['status'] == 'error'
    assert len(fixture.calls) == 2
