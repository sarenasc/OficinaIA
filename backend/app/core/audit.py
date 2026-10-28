import re

from sqlalchemy.orm import Session

from app.models import AuditEvent

SENSITIVE = re.compile(r"(?i)(api[_-]?key|password|authorization|token|secret|credential)")


def redact(value):
    if isinstance(value, dict):
        return {k: "[REDACTED]" if SENSITIVE.search(k) else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"(?i)Bearer\s+\S+", "Bearer [REDACTED]", value)
        value = re.sub(r"\bsk-[A-Za-z0-9_-]{12,}", "[REDACTED]", value)
        value = re.sub(r"(?i)(password|api[_-]?key|secret|token)\s*[=:]\s*[^\s,;]+", r"\1=[REDACTED]", value)
    return value


def audit(session: Session, action: str, details: dict, task_id: str | None = None, agent_id: str | None = None):
    session.add(AuditEvent(action=action, details=redact(details), task_id=task_id, agent_id=agent_id))
    session.commit()
