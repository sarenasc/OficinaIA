"""Real models/tools against an isolated DB; test permissions never modify production."""
import asyncio
import csv
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
import venv
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


async def child(directory, resume=False, finish=False):
    directory = directory.resolve()
    if not directory.is_relative_to((ROOT / 'data/verification').resolve()) or not (directory / 'office.db').is_file():
        raise ValueError('El diagnóstico requiere una copia existente dentro de data/verification')
    os.environ['OFFICE_DATA_DIR'] = str(directory)
    os.environ['OFFICE_DATABASE_URL'] = 'sqlite:///' + str(directory / 'office.db')
    sys.path.insert(0, str(ROOT / 'backend'))
    from app.agents.engine import instructions, run_agents
    from app.agents.research import research_access
    from app.core.audit import redact
    from app.core.config import DATA_DIR, DATABASE_URL
    from app.core.db import SessionLocal
    from app.models import Agent, AgentResource, AuditEvent, Execution, Resource, Task
    from app.tools.builtins import register_builtins
    from app.tools.registry import execute_tool

    if DATA_DIR.resolve() != directory or DATABASE_URL != os.environ['OFFICE_DATABASE_URL']:
        raise RuntimeError('La configuración cargada no corresponde a la copia aislada; no se permite escribir')
    from sqlalchemy import select

    evidence = json.loads((directory / 'verification.json').read_text(encoding='utf-8')) if resume else {'production_modified': False, 'models_simulated': False, 'stages': []}

    def record(stage, task, start, expected=None):
        session.commit()
        executions = [{key: getattr(e, key) for key in ('id', 'agent_id', 'tool_name', 'provider', 'model',
                       'status', 'duration_ms', 'tokens_in', 'tokens_out', 'error', 'input', 'output')}
                      for e in session.scalars(select(Execution).where(Execution.task_id == task.id))]
        value = {'stage': stage, 'task_id': task.id, 'status': task.status, 'error': task.error, 'result': task.result,
                 'elapsed_ms': int((time.monotonic() - start) * 1000), 'executions': executions,
                 'audit': [{'action': e.action, 'details': e.details} for e in session.scalars(
                     select(AuditEvent).where(AuditEvent.task_id == task.id))]}
        if expected:
            value['accepted'] = expected(task)
        evidence['stages'].append(value)
        (directory / 'verification.json').write_text(json.dumps(redact(evidence), ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({k: value[k] for k in ('stage', 'status', 'elapsed_ms', 'error')}, ensure_ascii=True), flush=True)

    async def model(stage, agent, request, expected=None):
        task = Task(number='VERIFY-' + uuid4().hex[:8], office_id=agent.office_id, agent_id=agent.id,
                    request=request, status='executing')
        session.add(task)
        session.commit()
        start = time.monotonic()
        try:
            await run_agents(session, task)
            task.status = 'completed'
        except Exception as exc:
            task.status, task.error = 'error', redact(str(exc))
        record(stage, task, start, expected)
        return task

    def tool(stage, agent, name, arguments):
        task = Task(number='VERIFY-' + uuid4().hex[:8], office_id=agent.office_id, agent_id=agent.id,
                    request=stage, status='executing')
        session.add(task)
        session.commit()
        start = time.monotonic()
        output = None
        try:
            output = execute_tool(session, task, agent, name, arguments)
            task.status, task.result = 'completed', json.dumps(output, ensure_ascii=False)
        except Exception as exc:
            task.status, task.error = 'error', redact(str(exc))
        record(stage, task, start)
        return output

    with SessionLocal() as session:
        register_builtins(session)
        original = session.scalar(select(Task).where(Task.number == 'TASK-2026-2259E43A'))
        researcher = session.scalar(select(Agent).where(Agent.name == 'Investigador Deportivo'))
        analyst = session.scalar(select(Agent).where(Agent.name == 'Analista Deportivo'))
        coordinator = session.get(Agent, original.agent_id)
        if not resume:
            evidence['access_original'] = research_access(session, researcher)
            historical = session.scalar(select(Execution).where(Execution.task_id == original.id, Execution.provider == 'ollama'))
            evidence['prompt_before'] = sum(len(m['content']) for m in historical.input['messages'])
            evidence['prompt_after'] = len(instructions(session, researcher)) + len(historical.input['messages'][-1]['content'])
            await model('original_request_current_permissions', researcher, historical.input['messages'][-1]['content'])
            await model('1_hola', researcher, 'Responde únicamente HOLA en una acción final JSON. No uses herramientas.',
                        lambda t: t.status == 'completed' and t.result.strip() == 'HOLA')
            await model('2_available_tools', researcher,
                        'Devuelve en una acción final la lista exacta de nombres de tus herramientas autorizadas. No ejecutes herramientas.',
                        lambda t: t.status == 'completed' and all(name in t.result for name in evidence['access_original']['tools']))
            url = 'https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json'
            tool('3_web_current_permissions', researcher, 'web.fetch', {'url': url})
            tool('3_search_current_connections', researcher, 'web.search', {'query': 'Colo-Colo córners tiros últimos 20 partidos'})
            tool('4_download_current_permissions', researcher, 'web.download', {'url': url, 'destination': {
                'resource_id': evidence['access_original']['create_resources'][0]}, 'filename': 'competitions.json'})
        # Explicit fixtures: same agents/models, narrowly scoped URL and workspace output.
        output_dir = directory / 'datasets'
        output_dir.mkdir(exist_ok=True)
        output = session.scalar(select(Resource).where(Resource.path == str(output_dir)))
        if not output:
            output = Resource(name='Fixture de diagnóstico', kind='directory', path=str(output_dir))
            session.add(output)
            session.flush()
            for agent in (researcher, analyst):
                session.add(AgentResource(agent_id=agent.id, resource_id=output.id, permissions=['read', 'create']))
        url = 'https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json'
        for allowed in (url, 'https://football-data.co.uk/new/Chile.csv',
                        'https://football-data.co.uk/mmz4281/2526/E0.csv', 'https://www.football-data.co.uk/new/Chile.csv',
                        'https://www.football-data.co.uk/mmz4281/2526/E0.csv'):
            if session.scalar(select(Resource).where(Resource.path == allowed)):
                continue
            resource = Resource(name='URL pública de prueba', kind='url', path=allowed)
            session.add(resource)
            session.flush()
            session.add(AgentResource(agent_id=researcher.id, resource_id=resource.id, permissions=['read']))
        session.commit()
        evidence['fixture_permissions_only'] = True
        if not resume:
            tool('3_web_fixture_authorized', researcher, 'web.fetch', {'url': url, 'destination': {
                'resource_id': output.id, 'path': 'competitions.txt'}})
            stats = tool('4_download_public_catalog', researcher, 'web.download', {'url': url, 'destination': {
                'resource_id': output.id}, 'filename': 'competitions.json'})
            if stats:
                catalog = json.loads(Path(stats['path']).read_text(encoding='utf-8'))
                evidence['statsbomb_chile_competitions'] = [r for r in catalog if r.get('country_name') == 'Chile']
        if not finish:
            await model('6_coordinator_to_researcher_recheck', coordinator,
                        f'Delega una única vez al agente {researcher.id} la solicitud: Devuelve exactamente '
                        '{"type":"final","content":"HOLA"}, sin herramientas ni delegaciones. '
                        'Tras recibir su resultado, confirma recepción en una acción final breve sin otras acciones.')
        for label, dataset_url, filename in (
            ('chile_coverage', 'https://www.football-data.co.uk/new/Chile.csv', 'Chile.csv'),
            ('public_match_dataset', 'https://www.football-data.co.uk/mmz4281/2526/E0.csv', 'E0.csv')):
            if finish and label == 'chile_coverage':
                continue  # known HTTP 404 is not recoverable; do not repeat it
            cached = output_dir / filename
            if cached.is_file():
                prior = next((stage for stage in evidence['stages'] if stage['stage'] == '4_' + label and stage['status'] == 'completed'), None)
                expected_hash = json.loads(prior['result'])['sha256'] if prior else None
                if not expected_hash or hashlib.sha256(cached.read_bytes()).hexdigest() != expected_hash:
                    raise ValueError('El dataset en caché no coincide con la descarga auditada')
                downloaded = {'path': str(cached)}
            else:
                downloaded = tool('4_' + label, researcher, 'web.download', {'url': dataset_url, 'destination': {
                    'resource_id': output.id}, 'filename': filename})
            if downloaded:
                with Path(downloaded['path']).open(encoding='utf-8-sig', newline='') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    evidence[label] = {'url': dataset_url, 'columns': reader.fieldnames, 'rows': len(rows),
                                       'requested_columns_present': all(c in reader.fieldnames for c in ('HC', 'AC', 'HS', 'AS', 'HST', 'AST'))}
                if filename == 'E0.csv':
                    # Keep the raw file. Project real statistics to fit the existing 100-column worker contract.
                    columns = ['Date', 'HomeTeam', 'AwayTeam', 'HC', 'AC', 'HS', 'AS', 'HST', 'AST']
                    if any(reader.fieldnames.count(column) != 1 for column in columns):
                        raise ValueError('Campos deportivos faltantes o duplicados; no se puede normalizar')
                    clean = output_dir / 'E0-stats.csv'
                    with clean.open('w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=columns)
                        writer.writeheader()
                        writer.writerows({key: row[key] for key in columns} for row in rows)
                    evidence['normalization'] = {'input': downloaded['path'], 'output': str(clean),
                        'columns': columns, 'rows': len(rows), 'invented_values': False,
                        'sha256': hashlib.sha256(clean.read_bytes()).hexdigest()}
                    tool('5_process_real_dataset', analyst, 'python.execute', {'operation': 'sports.group',
                         'parameters': {'resource_id': output.id, 'path': 'E0-stats.csv', 'group_column': 'HomeTeam', 'value_column': 'HC'}})
                    operation = {'name': 'python.execute', 'arguments': {'operation': 'sports.group',
                        'parameters': {'resource_id': output.id, 'path': 'E0-stats.csv',
                                       'group_column': 'HomeTeam', 'value_column': 'HC'}}}
                    child_request = 'Ejecuta únicamente la herramienta autorizada: ' + json.dumps(operation, ensure_ascii=False)
                    delegate = {'type': 'delegate', 'agent_id': analyst.id, 'request': child_request}
                    await model('7_deliver_dataset_to_analyst_explicit', coordinator,
                                'La primera acción debe ser exactamente este JSON: ' + json.dumps(delegate, ensure_ascii=False) +
                                '\nDespués de recibir al Analista, confirma en una acción final breve, sin más herramientas. '
                                'Es un dataset de prueba de Inglaterra, no Colo-Colo. No agregues texto a request.',
                                lambda task: bool(session.scalar(select(Execution).where(Execution.task_id == task.id,
                                    Execution.agent_id == analyst.id, Execution.tool_name == 'python.execute',
                                    Execution.status == 'completed'))))
        # Save coverage inspections added after individual records.
        (directory / 'verification.json').write_text(json.dumps(redact(evidence), ensure_ascii=False, indent=2), encoding='utf-8')
        print('EVIDENCE ' + str(directory), flush=True)


def main():
    if len(sys.argv) > 1:
        asyncio.run(child(Path(sys.argv[1]), resume="--resume" in sys.argv or "--finish" in sys.argv, finish="--finish" in sys.argv))
        return
    directory = ROOT / 'data/verification' / ('investigator-real-' + uuid4().hex[:8])
    directory.mkdir(parents=True)
    with sqlite3.connect('file:' + str(ROOT / 'data/office.db') + '?mode=ro', uri=True) as source:
        if source.execute("SELECT count(*) FROM tasks WHERE status IN ('pending','executing','waiting_approval')").fetchone()[0]:
            raise RuntimeError('Espere las tareas activas antes del diagnóstico')
        with sqlite3.connect(directory / 'office.db') as target:
            source.backup(target)
    venv.EnvBuilder(with_pip=False).create(directory / 'runtime/native-venv')
    env = dict(os.environ, OFFICE_DATA_DIR=str(directory), OFFICE_DATABASE_URL='sqlite:///' + str(directory / 'office.db'))
    subprocess.run([sys.executable, str(Path(__file__).resolve()), str(directory)], env=env, check=True)


if __name__ == '__main__':
    main()
