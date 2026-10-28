"""Configuration preflight; availability is never a claim of dataset coverage."""
import re
import unicodedata

from sqlalchemy import select

from app.models import AgentConnection, AgentResource, Connection, Resource
from app.tools.registry import assigned_tools


def research_request(request):
    text = ''.join(c for c in unicodedata.normalize('NFKD', request.lower()) if not unicodedata.combining(c))
    return bool(re.search(r'\b(partidos|encuentros)\b', text) and
                re.search(r'\b(corners?|tiros|estadisticas)\b', text) and
                re.search(r'\b(investiga\w*|recopila\w*|ultimos|datos reales|fuentes)\b', text))


def research_access(session, agent):
    tools = {t.name for t in assigned_tools(session, agent) if set(t.required_permissions).issubset(agent.permissions)}
    resources = [(r, a.permissions) for a, r in session.execute(
        select(AgentResource, Resource).join(Resource).where(AgentResource.agent_id == agent.id, Resource.active.is_(True)))]
    connections = [(c, a.permissions) for a, c in session.execute(
        select(AgentConnection, Connection).join(Connection).where(
            AgentConnection.agent_id == agent.id, Connection.active.is_(True)))]
    urls = [r.path for r, permissions in resources if r.kind == 'url' and 'read' in permissions]
    search = [c.id for c, p in connections if c.kind == 'web_search' and {'connect', 'select'}.issubset(p) and c.credential_ref]
    apis = [c.id for c, p in connections if c.kind == 'http_api' and {'connect', 'select'}.issubset(p)
            and (c.config.get('auth') == 'none' or c.credential_ref)]
    local = [r.id for r, p in resources if r.kind in {'directory', 'network_directory', 'file'} and 'read' in p and
             tools.intersection({'filesystem.read', 'excel.read', 'csv.read', 'sql.query'})]
    sql = [c.id for c, p in connections if c.kind in {'sqlite', 'sqlserver', 'postgresql', 'mysql'}
           and {'connect', 'select'}.issubset(p) and 'sql.query' in tools]
    usable = (bool(urls) and bool(tools.intersection({'web.fetch', 'web.download'})) or
              bool(search) and 'web.search' in tools or bool(apis) and 'api.request' in tools or bool(local) or bool(sql))
    return {'usable_source': bool(usable), 'tools': sorted(tools), 'readable_urls': urls,
            'search_connections': search, 'api_connections': apis, 'local_resources': local, 'sql_connections': sql,
            'create_resources': [r.id for r, p in resources if r.kind in {'directory', 'network_directory', 'file'} and 'create' in p],
            'coverage_verified': False}


def preflight(session, agent, request):
    if not research_request(request):
        return None
    access = research_access(session, agent)
    if not {t.name for t in assigned_tools(session, agent)}.intersection({'web.search', 'web.fetch', 'web.download', 'api.request'}):
        return None
    if not access['usable_source']:
        raise PermissionError('Investigación bloqueada: no hay fuente de datos utilizable. '
                              'Falta una URL asignada con read y web.fetch/web.download, una conexión de búsqueda/API '
                              'activa con connect/select y credencial cuando corresponda, o un dataset local legible. '
                              'Las herramientas asignadas por sí solas no dan acceso a datos. '
                              'La cobertura de córners y tiros por partido debe verificarse antes del análisis.')
    return access
