import pytest
from app.ai.providers import providers
from app.core.db import SessionLocal
from app.models import Agent, Execution, Task
from app.tools import network
from app.tools.registry import ToolArgumentsError, execute_tool
from conftest import create, wait_task
from sqlalchemy import select
from test_agents import ScriptedProvider


def setup(client, tmp_path):
    office = create(client, 'offices', name='Formato web')
    provider = client.get('/api/providers').json()[0]
    agent = create(client, 'agents', name='Investigador', office_id=office['id'], provider_id=provider['id'],
                   model='fixture', mode='trusted', permissions=['internet.access'])
    source = create(client, 'resources', name='Fuente', kind='url', path='https://example.org/sports/')
    output = create(client, 'resources', name='Informes', kind='directory', path=str(tmp_path))
    tool = next(t for t in client.get('/api/tools').json() if t['name'] == 'web.fetch')
    client.put(f"/api/agents/{agent['id']}/assignments", json={'tools': [tool['id']], 'resources': [
        {'resource_id': source['id'], 'permissions': ['read']},
        {'resource_id': output['id'], 'permissions': ['read', 'create']},
    ]})
    return office, agent, output


def fetch_action(resource, path):
    return {'type': 'tool', 'name': 'web.fetch', 'arguments': {'url': 'https://example.org/sports/',
            'destination': {'resource_id': resource['id'], 'path': path}}}


def test_model_can_correct_html_to_text_without_losing_task(client, tmp_path, monkeypatch):
    office, agent, output = setup(client, tmp_path)
    fixture = ScriptedProvider({agent['id']: [fetch_action(output, 'raw.html'), fetch_action(output, 'source.txt'),
                                            {'type': 'final', 'content': 'Texto consultado y guardado'}]})
    monkeypatch.setitem(providers, 'ollama', fixture)
    calls = []

    def response(url, authorize, **kwargs):
        authorize(url)
        calls.append(url)
        return {'url': url, 'status': 200, 'content_type': 'text/html',
                'body': b'<html><body><h1>Datos reales de prueba</h1></body></html>', 'errors': []}

    monkeypatch.setattr(network, 'request', response)
    task = create(client, 'tasks', office_id=office['id'], agent_id=agent['id'], request='Lee la página autorizada')
    done = wait_task(client, task['id'])
    assert done['status'] == 'completed', done
    assert len(calls) == 1
    assert not (tmp_path / 'raw.html').exists()
    assert (tmp_path / 'source.txt').read_text() == 'Datos reales de prueba'
    assert len(fixture.calls) == 3
    assert 'debe terminar en .txt' in str(fixture.calls[1][3])
    with SessionLocal() as session:
        executions = list(session.scalars(select(Execution).where(Execution.task_id == task['id'], Execution.tool_name == 'web.fetch')
                                         .order_by(Execution.created_at)))
        assert [e.status for e in executions] == ['error', 'completed']


def test_bad_format_is_rejected_before_network_and_does_not_bypass_url_permissions(client, tmp_path, monkeypatch):
    office, agent, output = setup(client, tmp_path)
    calls = []

    def response(url, authorize, **kwargs):
        calls.append(url)
        authorize(url)
        raise AssertionError('No debe consultar destinos no autorizados')

    monkeypatch.setattr(network, 'request', response)
    with SessionLocal() as session:
        person = session.get(Agent, agent['id'])
        task = Task(number='format-check', agent_id=person.id, office_id=office['id'], request='Verificación')
        session.add(task)
        session.commit()
        with pytest.raises(ToolArgumentsError, match='web.download'):
            execute_tool(session, task, person, 'web.fetch', fetch_action(output, 'dataset.csv')['arguments'])
        assert not calls
        args = fetch_action(output, 'source.txt')['arguments']
        args['url'] = 'https://other.example/data'
        with pytest.raises(PermissionError, match='URL no asignada'):
            execute_tool(session, task, person, 'web.fetch', args)
    assert not (tmp_path / 'source.txt').exists()


def test_invalid_format_retries_are_bounded(client, tmp_path, monkeypatch):
    office, agent, output = setup(client, tmp_path)
    fixture = ScriptedProvider({agent['id']: [fetch_action(output, 'raw.html') for _ in range(3)]})
    monkeypatch.setitem(providers, 'ollama', fixture)

    def never(*args, **kwargs):
        raise AssertionError('Los formatos inválidos no deben iniciar HTTP')

    monkeypatch.setattr(network, 'request', never)
    task = create(client, 'tasks', office_id=office['id'], agent_id=agent['id'], request='Lee una página')
    done = wait_task(client, task['id'])
    assert done['status'] == 'error'
    assert 'debe terminar en .txt' in done['error']
    assert len(fixture.calls) == 3
    assert not (tmp_path / 'raw.html').exists()
