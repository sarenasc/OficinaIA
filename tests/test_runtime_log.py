from logging.handlers import RotatingFileHandler

from app.ai.providers import providers
from app.core import runtime_log
from conftest import create, wait_task
from test_agents import ScriptedProvider


def test_console_file_redaction_rotation_and_no_duplicate_handlers(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv('OFFICE_SESSION_TOKEN', 'private-session-example')
    path = runtime_log.configure(tmp_path)
    try:
        runtime_log.logger.error('Fallo: token=hidden-value password=hidden-password Bearer hidden-bearer')
        runtime_log.logger.info('No mostrar private-session-example')
        text = path.read_text(encoding='utf-8')
        assert 'ERROR' in text and 'Fallo:' in text
        assert all(secret not in text for secret in ['hidden-value', 'hidden-password', 'hidden-bearer', 'private-session-example'])
        assert 'Fallo:' in capsys.readouterr().err
        file = next(h for h in runtime_log.logger.handlers if isinstance(h, RotatingFileHandler))
        assert file.maxBytes == 2 * 1024 * 1024 and file.backupCount == 3
        # Exercise actual rotation, using a small limit only in the fixture.
        file.maxBytes = 300
        for _ in range(10):
            runtime_log.logger.info('Entrada de prueba ' + 'x' * 100)
        assert path.with_name(path.name + '.1').exists()
        runtime_log.configure(tmp_path)
        assert len(runtime_log.logger.handlers) == 2
    finally:
        runtime_log.close()


def test_log_file_failure_keeps_console_working(tmp_path, capsys):
    (tmp_path / 'logs').write_text('not a directory')
    runtime_log.configure(tmp_path)
    try:
        runtime_log.logger.info('La consola sigue disponible')
        output = capsys.readouterr().err
        assert 'solo en consola' in output and 'La consola sigue disponible' in output
    finally:
        runtime_log.close()


def test_actual_delegation_and_tools_are_logged_without_request_contents(client, monkeypatch):
    office = create(client, 'offices', name='Registro de prueba')
    provider = client.get('/api/providers').json()[0]
    parent = create(client, 'agents', name='Coordinador', office_id=office['id'], provider_id=provider['id'], model='fixture')
    child = create(client, 'agents', name='Investigador', office_id=office['id'], provider_id=provider['id'], model='fixture')
    create(client, 'relations', source_id=parent['id'], target_id=child['id'])
    tool = next(t for t in client.get('/api/tools').json() if t['name'] == 'agents.list')
    client.put(f"/api/agents/{child['id']}/assignments", json={'tools': [tool['id']]})
    fixture = ScriptedProvider({
        parent['id']: [{'type': 'delegate', 'agent_id': child['id'], 'request': 'PRIVATE-PROMPT'},
                       {'type': 'final', 'content': 'PRIVATE-RESULT'}],
        child['id']: [{'type': 'tool', 'name': 'agents.list', 'arguments': {}}, {'type': 'final', 'content': 'PRIVATE-CHILD-RESULT'}],
    })
    monkeypatch.setitem(providers, 'ollama', fixture)
    task = create(client, 'tasks', office_id=office['id'], agent_id=parent['id'], request='PRIVATE-ROOT-PROMPT')
    assert wait_task(client, task['id'])['status'] == 'completed'
    file = next(h for h in runtime_log.logger.handlers if isinstance(h, RotatingFileHandler))
    text = open(file.baseFilename, encoding='utf-8').read()
    assert task['number'] in text
    for event in ['Tarea iniciada', 'Tarea delegada', 'Investigador', 'Ejecutando herramienta', 'agents.list', 'Tarea completada']:
        assert event in text
    assert 'PRIVATE-' not in text
    before = text
    client.get('/api/health')
    client.get('/api/agents')
    assert open(file.baseFilename, encoding='utf-8').read() == before


def test_audit_logging_failure_does_not_break_action(client, monkeypatch):
    from app.core.audit import audit
    from app.core.db import SessionLocal
    from app.models import AuditEvent
    from sqlalchemy import select

    def broken(*args, **kwargs):
        raise OSError('Simulated console failure')

    monkeypatch.setattr(runtime_log, 'emit', broken)
    with SessionLocal() as session:
        audit(session, 'task.started', {})
        assert session.scalar(select(AuditEvent).where(AuditEvent.action == 'task.started'))
