"""Attribute a task failure to the agent that was actually executing it."""
from sqlalchemy import select

from app.core.audit import redact
from app.models import Agent, AuditEvent


def failure_info(session, task):
    if task.status != 'error' or not task.error:
        return None
    stored = (task.context or {}).get('failure')
    if stored:
        return stored
    context = task.context or {}
    frames = context.get('frames', [])
    steps = context.get('procedure_steps', [])
    agent_id = frames[-1]['agent_id'] if frames else task.agent_id
    if not frames and steps:
        index = len(context.get('outputs', []))
        if index < len(steps):
            agent_id = steps[index]['agent_id']
    # Older failures already have a reliable audit record, even if their frames are absent.
    blocked = session.scalar(select(AuditEvent).where(
        AuditEvent.task_id == task.id, AuditEvent.action == 'research.blocked'
    ).order_by(AuditEvent.created_at.desc()).limit(1))
    if blocked and blocked.agent_id:
        agent_id = blocked.agent_id
    agent = session.get(Agent, agent_id)
    name = agent.name if agent else 'Especialista no disponible'
    reason = redact(task.error)
    delegated = bool(frames and len(frames) > 1) or (not steps and agent_id != task.agent_id)
    message = (f'La tarea delegada a {name} quedó bloqueada. Motivo: {reason}' if delegated
               else f'Falló la ejecución de {name}. Motivo: {reason}' if agent_id != task.agent_id else reason)
    return {'agent_id': agent_id, 'agent_name': name, 'delegated': delegated,
            'reason': reason, 'message': message}


def task_error(session, task):
    failure = failure_info(session, task)
    return failure['message'] if failure else redact(task.error or '')
