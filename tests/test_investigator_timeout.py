import json
from pathlib import Path
from runpy import run_path

import httpx
import pytest
from app.agents.engine import instructions, model_tool_result, run_agents
from app.agents.research import preflight, research_access
from app.ai.providers import AIResponse, HTTPProvider, ModelCallError, providers
from app.core.db import SessionLocal
from app.core.db import engine as database_engine
from app.models import Agent, AgentResource, AuditEvent, Execution, Provider, Resource, Task
from app.tools import network
from app.tools.registry import execute_tool
from conftest import create
from sqlalchemy import select
from test_execution_dual import native as native_worker_fixture
from test_stage3_tools import setup

native = native_worker_fixture

REQUEST = 'Investiga los córners y tiros a puerta de los últimos 20 partidos con datos reales.'


def test_sqlite_task_reader_does_not_block_audit_commit(client):
    with database_engine.connect() as reader:
        assert reader.exec_driver_sql('PRAGMA journal_mode').scalar() == 'wal'
        reader.exec_driver_sql('SELECT count(*) FROM audit_events').fetchone()
        with SessionLocal() as writer:
            writer.add(AuditEvent(action='concurrent-read-verification', details={}))
            writer.commit()
        assert reader.exec_driver_sql('SELECT count(*) FROM audit_events').scalar() >= 1


async def test_diagnostic_rejects_production_directory_before_importing_database():
    script = Path(__file__).resolve().parents[1] / 'scripts/verify_investigator_timeout.py'
    child = run_path(str(script), run_name='diagnostic_test')['child']
    with pytest.raises(ValueError, match='copia existente'):
        await child(script.parent.parent / 'data', resume=True)


@pytest.mark.parametrize('denied', [False, True])
async def test_explicit_tool_has_real_output_without_model_and_respects_permissions(client, tmp_path, native, monkeypatch, denied):
    office, person, _ = setup(client, tmp_path)
    client.put('/api/execution/preference', json={'mode': 'native'})
    class Never:
        async def complete(self, *args):
            raise AssertionError('Una operación explícita no necesita inferencia')
    monkeypatch.setitem(providers, 'ollama', Never())
    with SessionLocal() as session:
        agent = session.get(Agent, person['id'])
        if denied:
            agent.permissions = []
        request = 'Ejecuta únicamente la herramienta autorizada: ' + json.dumps({'name': 'python.execute',
                   'arguments': {'operation': 'statistics.mean', 'parameters': {'values': [2, 1, 3, 0, 4]}}})
        task = Task(number='explicit', office_id=office['id'], agent_id=agent.id, request=request, status='executing')
        session.add(task)
        session.commit()
        if denied:
            with pytest.raises(PermissionError):
                await run_agents(session, task)
            assert not task.result
        else:
            await run_agents(session, task)
            result = json.loads(task.result)['result']
            assert result['sum'] == 10 and result['backend'] == 'native' and result['worker_pid'] > 0
            assert session.scalar(select(AuditEvent).where(AuditEvent.action == 'tool.direct_verified'))
        assert not list(session.scalars(select(Execution).where(Execution.task_id == task.id, Execution.provider != '')))


def researcher(client, tmp_path):
    office, person, resource = setup(client, tmp_path)
    tools = client.get('/api/tools').json()
    assigned = [t['id'] for t in tools if t['name'] in {'web.search', 'web.fetch', 'web.download', 'api.request'}]
    client.put(f"/api/agents/{person['id']}/assignments", json={'tools': assigned,
               'resources': [{'resource_id': resource['id'], 'permissions': ['read', 'create']}]})
    return office, person, resource


async def test_preflight_blocks_original_request_without_model_and_retains_user_rules(client, tmp_path, monkeypatch):
    office, person, _ = researcher(client, tmp_path)
    class Never:
        async def complete(self, *args):
            raise AssertionError('No debe llamarse al modelo sin fuente')
    monkeypatch.setitem(providers, 'ollama', Never())
    with SessionLocal() as session:
        agent = session.get(Agent, person['id'])
        agent.instructions = 'Conservar esta instrucción del usuario.'
        prompt = instructions(session, agent)
        assert agent.instructions in prompt
        assert 'statistics.mean' not in prompt and 'excel.generate_sales' not in prompt
        assert preflight(session, agent, 'Responde HOLA') is None
        assert not research_access(session, agent)['usable_source']
        task = Task(number='preflight', office_id=office['id'], agent_id=agent.id, request=REQUEST, status='executing')
        session.add(task)
        session.commit()
        with pytest.raises(PermissionError, match='no hay fuente'):
            await run_agents(session, task)
        assert not list(session.scalars(select(Execution).where(Execution.task_id == task.id)))
        assert session.scalar(select(AuditEvent).where(AuditEvent.action == 'research.blocked'))
        url = Resource(name='Fuente', kind='url', path='https://example.com/datos')
        session.add(url)
        session.flush()
        assignment = AgentResource(agent_id=agent.id, resource_id=url.id, permissions=['read'])
        session.add(assignment)
        session.commit()
        assert preflight(session, agent, REQUEST)['usable_source']
        assert 'https://example.com/datos' in instructions(session, agent)
        agent.permissions = []
        session.commit()
        with pytest.raises(PermissionError):
            preflight(session, agent, REQUEST)


def test_saved_web_text_is_full_but_preview_bounded_and_no_write_without_permission(client, tmp_path, monkeypatch):
    office, person, resource = researcher(client, tmp_path)
    content = 'texto real de transporte simulado\n' * 1000
    calls = []
    def response(url, authorize, **kwargs):
        calls.append(url)
        return {'url': url, 'status': 200, 'content_type': 'text/plain', 'body': content.encode(),
                'consulted_at': '2026-10-09T00:00:00Z', 'errors': []}
    monkeypatch.setattr(network, 'request', response)
    with SessionLocal() as session:
        agent = session.get(Agent, person['id'])
        task = Task(number='saved-fetch', office_id=office['id'], agent_id=agent.id, request='Fixture')
        session.add(task)
        session.commit()
        result = execute_tool(session, task, agent, 'web.fetch', {'url': 'https://example.com',
                              'destination': {'resource_id': resource['id'], 'path': 'source.txt'}})
        assert Path(result['path']).read_text(encoding='utf-8') == content
        assert len(result['content']) == 2000 and result['data_saved'] and result['truncated']
        event = session.scalar(select(AuditEvent).where(AuditEvent.action == 'tool.completed'))
        assert event.details['duration_ms'] >= 0
        assignment = session.get(AgentResource, (agent.id, resource['id']))
        assignment.permissions = ['read']
        session.commit()
        with pytest.raises(PermissionError):
            execute_tool(session, task, agent, 'web.fetch', {'url': 'https://example.com',
                         'destination': {'resource_id': resource['id'], 'path': 'denied.txt'}})
        assert len(calls) == 1 and not (tmp_path / 'denied.txt').exists()
    preview = model_tool_result({'rows': [{'value': n} for n in range(1000)], 'path': 'dataset.csv',
                                'resource_id': 'resource', 'url': 'https://example.com'})
    assert preview['path'] == 'dataset.csv' and preview['resource_id'] == 'resource'
    assert preview['preview_only'] and 'rows' not in preview


async def test_repeated_tool_stops_and_task_global_budget_survives_resume(client, tmp_path, monkeypatch):
    office, person, _ = setup(client, tmp_path)
    provider = create(client, 'providers', name='Fixture', kind='ollama', url='http://127.0.0.1:11434', default_model='fixture')
    class Repeat:
        async def complete(self, *args):
            return AIResponse({'type': 'tool', 'name': 'agents.list', 'arguments': {}})
    monkeypatch.setitem(providers, 'ollama', Repeat())
    with SessionLocal() as session:
        agent = session.get(Agent, person['id'])
        agent.provider_id = provider['id']
        task = Task(number='repeat', office_id=office['id'], agent_id=agent.id, request='Lista agentes', status='executing')
        session.add(task)
        session.commit()
        with pytest.raises(ValueError, match='repetida'):
            await run_agents(session, task)
        assert len(list(session.scalars(select(Execution).where(Execution.task_id == task.id,
                         Execution.tool_name == 'agents.list')))) == 3
        assert task.context['total_steps'] == 3
        other = Task(number='budget', office_id=office['id'], agent_id=agent.id, request='Continuar', status='executing',
                     context={'total_steps': 80})
        session.add(other)
        session.commit()
        with pytest.raises(ValueError, match='Límite de pasos'):
            await run_agents(session, other)
        assert not list(session.scalars(select(Execution).where(Execution.task_id == other.id)))


@pytest.mark.parametrize('failure', ['connect', 'timeout', 'http'])
async def test_retry_only_connection_failure_and_classifies_error(monkeypatch, failure):
    calls = []
    def handler(request):
        calls.append(request)
        if failure == 'connect':
            if len(calls) == 1:
                raise httpx.ConnectError('Fixture', request=request)
            return httpx.Response(200, json={'message': {'content': json.dumps({'type': 'final', 'content': 'HOLA'})}})
        if failure == 'timeout':
            raise httpx.ReadTimeout('Fixture', request=request)
        return httpx.Response(503)
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    provider = Provider(kind='ollama', url='http://127.0.0.1:11434')
    agent = Agent(temperature=0.2, context_limit=8192)
    if failure == 'connect':
        value = await HTTPProvider().complete(provider, agent, 'fixture', [{'role': 'user', 'content': 'Hola'}])
        assert value.metrics['attempts'] == 2 and len(calls) == 2
    else:
        with pytest.raises(ModelCallError) as error:
            await HTTPProvider().complete(provider, agent, 'fixture', [{'role': 'user', 'content': 'Hola'}])
        assert error.value.category == ('model_timeout' if failure == 'timeout' else 'provider_http')
        assert len(calls) == 1
