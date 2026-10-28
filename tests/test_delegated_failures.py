from app.ai.providers import AIResponse, providers
from app.core.db import SessionLocal
from app.models import AuditEvent, Task
from conftest import create, wait_task

REQUEST = 'Investiga los últimos partidos con estadísticas de córners y tiros con datos reales'


def test_delegated_preflight_identifies_specialist_and_releases_coordinator(client, monkeypatch):
    office = create(client, 'offices', name='Delegación')
    provider = client.get('/api/providers').json()[0]
    parent = create(client, 'agents', name='Coordinador', office_id=office['id'],
                    provider_id=provider['id'], model='fixture')
    child = create(client, 'agents', name='Investigador Deportivo', office_id=office['id'],
                   provider_id=provider['id'], model='fixture', permissions=['internet.access'])
    create(client, 'relations', source_id=parent['id'], target_id=child['id'])
    tool = next(t for t in client.get('/api/tools').json() if t['name'] == 'web.fetch')
    client.put(f"/api/agents/{child['id']}/assignments", json={'tools': [tool['id']]})
    calls = []

    class Delegate:
        async def complete(self, provider, agent, model, messages):
            calls.append(agent.id)
            assert agent.id == parent['id'], 'No debe ejecutarse el modelo del investigador sin fuente'
            return AIResponse({'type': 'delegate', 'agent_id': child['id'], 'request': REQUEST}, 10, 5)

    monkeypatch.setitem(providers, 'ollama', Delegate())
    task = create(client, 'tasks', office_id=office['id'], agent_id=parent['id'], request=REQUEST)
    done = wait_task(client, task['id'])
    assert done['status'] == 'error'
    assert 'delegada a Investigador Deportivo' in done['error']
    assert 'no hay fuente de datos utilizable' in done['error']
    assert calls == [parent['id']]
    assert client.get(f"/api/agents/{parent['id']}").json()['status'] == 'active'
    assert client.get(f"/api/agents/{child['id']}").json()['status'] == 'error'
    details = client.get(f"/api/tasks/{task['id']}/details").json()
    assert details['failure']['agent_id'] == child['id']
    assert details['failure']['delegated'] is True
    assert len(details['messages']) == 1
    assert details['messages'][0]['target_id'] == child['id']
    assert any(e['action'] == 'agent.failed' and e['agent_id'] == child['id'] for e in details['audit'])
    scene = client.get(f"/api/offices/{office['id']}/scene").json()
    activity = {a['id']: a['activity'] for a in scene['agents']}
    assert 'delegada a Investigador Deportivo' in activity[parent['id']]['error']
    assert 'no hay fuente' in activity[child['id']]['error']


def test_historical_delegation_is_attributed_without_rewriting_history(client):
    office = create(client, 'offices', name='Historial')
    parent = create(client, 'agents', name='Coordinador', office_id=office['id'])
    child = create(client, 'agents', name='Investigador', office_id=office['id'])
    with SessionLocal() as session:
        task = Task(number='old-delegation', office_id=office['id'], agent_id=parent['id'],
                    request=REQUEST, status='error', error='Investigación bloqueada: no hay fuente')
        session.add(task)
        session.flush()
        session.add(AuditEvent(task_id=task.id, agent_id=child['id'], action='research.blocked', details={}))
        session.commit()
        task_id = task.id
    details = client.get(f'/api/tasks/{task_id}/details').json()
    assert details['failure']['agent_id'] == child['id']
    assert 'delegada a Investigador' in details['task']['error']
    with SessionLocal() as session:
        assert session.get(Task, task_id).error == 'Investigación bloqueada: no hay fuente'
    # A direct failure must retain its original cause and must not pretend there was delegation.
    with SessionLocal() as session:
        direct = Task(number='direct-error', office_id=office['id'], agent_id=child['id'],
                      request=REQUEST, status='error', error='Falta una fuente')
        session.add(direct)
        session.commit()
        direct_id = direct.id
    details = client.get(f'/api/tasks/{direct_id}/details').json()
    assert details['task']['error'] == 'Falta una fuente'
    assert details['failure']['delegated'] is False
