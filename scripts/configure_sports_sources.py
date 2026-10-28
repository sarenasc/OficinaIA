"""Assign verified public Chilean football sources to the sports researcher only."""
# Imports below intentionally follow the explicit local-database bootstrap.
# ruff: noqa: E402
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / 'data' / 'office.db'
if not DATABASE.is_file():
    raise RuntimeError('No existe la base local; no se creará otra base')
os.environ['OFFICE_DATABASE_URL'] = 'sqlite:///' + DATABASE.as_posix()
os.environ['OFFICE_DATA_DIR'] = str(ROOT / 'data')
sys.path.insert(0, str(ROOT / 'backend'))

from app.agents.research import research_access
from app.core.audit import audit
from app.core.db import SessionLocal
from app.models import Agent, AgentConnection, AgentResource, AgentTool, Connection, Resource, Task, Tool
from app.tools.connections import validate_connection_config
from app.tools.network import api_request, request, web_authorizer
from sqlalchemy import select

SOURCES = [
    ('ESPN Chile — partidos y estadísticas', 'https://site.api.espn.com/apis/site/v2/sports/soccer/chi.1/', 'scoreboard'),
    ('ESPN Chile — posiciones', 'https://site.web.api.espn.com/apis/v2/sports/soccer/chi.1/', 'standings'),
]
OFFICIAL = 'https://www.campeonatochileno.cl/'
MARKER = '\n\n[Fuentes deportivas verificables]\n'


def main():
    evidence = ROOT / 'data' / 'verification' / ('sports-sources-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    evidence.mkdir(parents=True, exist_ok=False)
    with sqlite3.connect(DATABASE) as source, sqlite3.connect(evidence / 'before.db') as target:
        source.backup(target)
    with SessionLocal() as session:
        people = list(session.scalars(select(Agent).where(Agent.name == 'Investigador Deportivo')))
        if len(people) != 1:
            raise ValueError('No se encontró un único Investigador Deportivo')
        agent = people[0]
        if session.scalar(select(Task.id).where(Task.office_id == agent.office_id,
                          Task.status.in_(['pending', 'executing', 'planning', 'waiting_approval']))):
            raise ValueError('Hay tareas activas en esta oficina; no se modificó su configuración')
        before = research_access(session, agent)
        connections = []
        for name, base, endpoint in SOURCES:
            connection = session.scalar(select(Connection).where(Connection.name == name, Connection.kind == 'http_api'))
            config = {'base_url': base, 'auth': 'none', 'requests_per_minute': 20}
            validate_connection_config('http_api', config, True)
            if connection is None:
                connection = Connection(name=name, kind='http_api', config=config, active=True)
                session.add(connection)
                session.flush()
            elif connection.config != config or not connection.active:
                raise ValueError('Existe una conexión con este nombre y distinta configuración; no se sobrescribe')
            assignment = session.get(AgentConnection, (agent.id, connection.id))
            if assignment is None:
                session.add(AgentConnection(agent_id=agent.id, connection_id=connection.id, permissions=['connect', 'select']))
            else:
                assignment.permissions = sorted(set(assignment.permissions) | {'connect', 'select'})
            connections.append((connection, endpoint))
        resource = session.scalar(select(Resource).where(Resource.kind == 'url', Resource.path == OFFICIAL))
        if resource is None:
            resource = Resource(name='Campeonato Chileno — fuente oficial', kind='url', path=OFFICIAL,
                                description='Liga de Primera: tabla, resultados y calendario. Verificar fecha y cobertura.', active=True)
            session.add(resource)
            session.flush()
        if not resource.active:
            raise ValueError('La fuente oficial existente está desactivada; no se reactiva automáticamente')
        assignment = session.get(AgentResource, (agent.id, resource.id))
        if assignment is None:
            session.add(AgentResource(agent_id=agent.id, resource_id=resource.id, permissions=['read']))
        else:
            assignment.permissions = sorted(set(assignment.permissions) | {'read'})
        added_tools = []
        for name in ['api.request', 'web.fetch', 'web.download', 'filesystem.read', 'csv.read']:
            tool = session.scalar(select(Tool).where(Tool.name == name, Tool.active.is_(True)))
            if not tool:
                raise ValueError('Herramienta no disponible: ' + name)
            if not session.get(AgentTool, (agent.id, tool.id)):
                session.add(AgentTool(agent_id=agent.id, tool_id=tool.id))
                added_tools.append(name)
        agent.permissions = sorted(set(agent.permissions) | {'internet.access'})
        lines = [
            'Investiga tú las fuentes; el coordinador delega y supervisa. Conserva los datos y sus URL/fechas de consulta.',
            f'Fuente oficial con web.fetch/web.download: {OFFICIAL}competition/liga-de-primera/ (recurso {resource.id}).',
        ]
        for connection, endpoint in connections:
            lines.append(f'api.request: connection_id="{connection.id}" ({connection.name}), method="GET", endpoint="{endpoint}". No requiere clave.')
        lines.extend([
            'En la conexión de partidos usa scoreboard con params dates="YYYYMMDD" y limit=100, una fecha por consulta (los rangos pueden devolver HTTP 400); teams para equipos; teams/{id}/schedule para calendario; summary con params event="id" para el detalle de un partido.',
            'En posiciones usa standings con params season=año, region="cl", lang="es". Confirma la temporada que realmente devuelve.',
            'En summary revisa boxscore.players/teams y statistics: wonCorners=córners, totalShots=tiros totales, shotsOnTarget=tiros al arco. Se comprobó una muestra real; no asumas que todos los partidos tienen esos campos ni confundas ausencia con cero.',
            'Guarda respuestas con destination en Informes usando un nombre .json nuevo. Lee archivos descargados con filesystem.read/csv.read según su formato.',
            'Verifica cobertura partido por partido de córners y tiros si la solicitud los requiere; acceso HTTP no significa cobertura completa. No inventes datos ni probabilidades. Distingue resultados, partidos pendientes y temporada. Si falta un dato, informa exactamente cuál.',
            'web.search requiere una conexión de buscador con credencial: no la uses mientras no exista. Las fuentes anteriores usan api.request o web.fetch directamente.',
        ])
        agent.instructions = (agent.instructions or '').split(MARKER)[0] + MARKER + '\n'.join(lines)
        session.flush()
        after = research_access(session, agent)
        assert after['usable_source'] and len(after['api_connections']) >= 2
        # Check the actual assigned transport, permissions and endpoints before committing.
        checks = []
        for connection, endpoint in connections:
            result = api_request(session, None, agent, {'connection_id': connection.id, 'endpoint': endpoint,
                                 'params': {'region': 'cl', 'lang': 'es'}})
            checks.append({'source': connection.name, 'status': result['status'], 'keys': list(result['data']),
                           'consulted_at': result['consulted_at']})
        official = request(OFFICIAL + 'competition/liga-de-primera/', web_authorizer(session, agent), timeout=20)
        assert official['status'] == 200
        checks.append({'source': resource.name, 'status': official['status'], 'bytes': len(official['body'])})
        session.commit()
        proof = {'agent_id': agent.id, 'agent': agent.name, 'before': before, 'after': after,
                 'added_tools': added_tools, 'checks': checks, 'backup': str(evidence / 'before.db')}
        audit(session, 'research.sources_configured', proof, agent_id=agent.id)
        (evidence / 'verification.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(proof, ensure_ascii=True))


if __name__ == '__main__':
    main()
