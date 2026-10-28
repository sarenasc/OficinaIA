"""Concise live activity in the launcher's console and bounded diagnostic files."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.audit import redact
from app.models import Agent, Task

logger = logging.getLogger('oficina')
logger.propagate = False


class SafeFormatter(logging.Formatter):
    def format(self, record):
        text = redact(super().format(record))
        token = os.environ.get('OFFICE_SESSION_TOKEN', '')
        return text.replace(token, '[REDACTED]') if token else text


def configure(data_dir):
    close()
    logger.setLevel(logging.INFO)
    formatter = SafeFormatter('%(asctime)s | %(levelname)-7s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(formatter)
    logger.addHandler(stream)
    path = Path(data_dir) / 'logs' / 'oficina-ia.log'
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        file = RotatingFileHandler(path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8')
        file.setFormatter(formatter)
        logger.addHandler(file)
        logger.info('Registro en vivo activado. Archivo: %s', path)
    except OSError as exc:
        logger.warning('Registro disponible solo en consola; no se pudo abrir el archivo: %s', redact(str(exc)))
    return path


def close():
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()


EVENTS = {
    'task.created': 'Tarea creada', 'task.started': 'Tarea iniciada',
    'task.completed': 'Tarea completada', 'task.error': 'Tarea finalizada con error',
    'task.cancelled': 'Tarea cancelada', 'task.waiting_approval': 'Esperando aprobación del usuario',
    'agent.delegated': 'Tarea delegada', 'agent.failed': 'Fallo del agente',
    'model.started': 'Consultando modelo IA', 'model.completed': 'Respuesta del modelo recibida',
    'model.error': 'Falló la consulta al modelo',
    'model.format_retry': 'Respuesta IA con formato inválido; solicitando una única corrección',
    'tool.started': 'Ejecutando herramienta', 'tool.completed': 'Herramienta completada',
    'tool.error': 'Falló la herramienta', 'tool.waiting_approval': 'Herramienta esperando aprobación',
    'tool.loop_blocked': 'Se detuvo una repetición de herramienta sin progreso',
    'research.blocked': 'Investigación bloqueada', 'research.preflight': 'Acceso a fuentes comprobado',
    'approval.approved': 'Acción autorizada por el usuario', 'approval.rejected': 'Acción rechazada por el usuario',
    'research.sources_configured': 'Fuentes de investigación configuradas',
}


def emit(session, action, details, task_id=None, agent_id=None):
    if action not in EVENTS or not logger.handlers:
        return
    task = session.get(Task, task_id) if task_id else None
    agent = session.get(Agent, agent_id) if agent_id else None
    # Task completion is audited without an agent_id; the task owner supplies context.
    if not agent and task:
        agent = session.get(Agent, task.agent_id)
    task_name = task.number if task else '-'
    agent_name = agent.name if agent else '-'
    parts = [EVENTS[action]]
    # Deliberate allowlist: no prompts, tool arguments, results, URLs or credentials.
    for key in ('name', 'provider', 'model', 'target_name', 'duration_ms', 'error_category'):
        value = details.get(key)
        if value is not None and value != '':
            parts.append(f'{key}={value}')
    reason = details.get('error') or details.get('reason')
    if reason:
        parts.append('Motivo: ' + str(reason))
    text = redact(' | '.join(parts)).replace('\r', ' ').replace('\n', ' ')[:1200]
    level = logging.ERROR if action.endswith('.error') or action == 'agent.failed' else (
        logging.WARNING if action in {'research.blocked', 'tool.loop_blocked', 'tool.waiting_approval',
                                      'task.waiting_approval', 'approval.rejected'} else logging.INFO)
    logger.log(level, '%s | %s | %s', task_name, redact(agent_name).replace('\r', ' ').replace('\n', ' ')[:160], text)
