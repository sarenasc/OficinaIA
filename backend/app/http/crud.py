from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.core.audit import audit, redact
from app.core.db import get_session
from app.http.common import ENTITIES, entity_type, get_or_404, router, serialize, validate_domain
from app.security.secrets import secrets


@router.get("/{entity}")
def list_entities(
    entity: str, office_id: str | None = None, task_id: str | None = None, session: Session = Depends(get_session)
):
    cls = entity_type(entity)
    query = select(cls)
    if office_id and hasattr(cls, "office_id"):
        query = query.where(cls.office_id == office_id)
    if task_id and hasattr(cls, "task_id"):
        query = query.where(cls.task_id == task_id)
    return [serialize(obj) for obj in session.scalars(query.order_by(cls.created_at.desc()).limit(1000))]


@router.get("/{entity}/{id}")
def get_entity(entity: str, id: str, session: Session = Depends(get_session)):
    return serialize(get_or_404(session, entity_type(entity), id))


def write_entity(entity, data, session, current=None):
    cls = entity_type(entity, writable=True)
    if current:
        original = {key: getattr(current, key) for key in ENTITIES[entity][1].model_fields}
        data = {**original, **data}
    parsed = ENTITIES[entity][1].model_validate(data).model_dump()
    validate_domain(session, entity, parsed, current)
    if current:
        for key, value in parsed.items():
            setattr(current, key, value)
        obj = current
    else:
        obj = cls(**parsed)
        session.add(obj)
    session.commit()
    audit(session, entity + (".updated" if current else ".created"), {"id": obj.id, "changes": redact(parsed)})
    return serialize(obj)


@router.post("/{entity}")
def create_entity(entity: str, data: dict, session: Session = Depends(get_session)):
    return write_entity(entity, data, session)


@router.patch("/{entity}/{id}")
def update_entity(entity: str, id: str, data: dict, session: Session = Depends(get_session)):
    current = get_or_404(session, entity_type(entity, writable=True), id)
    if (
        entity in {"agents", "tools", "resources", "providers", "connections", "relations", "offices", "procedures"}
        and session.scalar(select(m.Task.id).where(m.Task.status.in_(["pending", "executing", "waiting_approval"])))
        is not None
    ):
        raise HTTPException(409, "Espere a que terminen las tareas antes de modificar la configuración")
    return write_entity(entity, data, session, current)


@router.delete("/{entity}/{id}")
def delete_entity(entity: str, id: str, session: Session = Depends(get_session)):
    cls = entity_type(entity, writable=True)
    obj = get_or_404(session, cls, id)
    if isinstance(obj, m.Tool) and obj.builtin:
        raise HTTPException(409, "Desactive la herramienta integrada en lugar de eliminarla")
    if session.scalar(select(m.Task.id).where(m.Task.status.in_(["pending", "executing", "waiting_approval"]))):
        raise HTTPException(409, "Espere a que terminen las tareas antes de eliminar configuración")
    if entity in {"providers", "connections"}:
        secrets.delete(obj.credential_ref)
    session.delete(obj)
    session.commit()
    audit(session, entity + ".deleted", {"id": id})
    return {"deleted": True}
