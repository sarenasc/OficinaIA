from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app import models as m
from app import schemas as s
from app.ai.providers import discover
from app.core.audit import audit
from app.core.db import get_session
from app.http.common import get_or_404, router
from app.security.secrets import secrets
from app.tools.connections import connection_engine


@router.post("/providers/{id}/credential")
@router.post("/connections/{id}/credential")
def put_credential(id: str, data: s.SecretInput, request: Request, session: Session = Depends(get_session)):
    cls = m.Provider if "/providers/" in request.url.path else m.Connection
    entity = get_or_404(session, cls, id)
    entity.credential_ref = secrets.put(data.value, entity.credential_ref)
    session.commit()
    audit(session, "credential.updated", {"entity_id": id})
    return {"stored": True}


@router.post("/providers/{id}/test")
async def test_provider(id: str, session: Session = Depends(get_session)):
    return {"models": await discover(get_or_404(session, m.Provider, id))}


@router.post("/connections/{id}/test")
def test_connection(id: str, session: Session = Depends(get_session)):
    connection = get_or_404(session, m.Connection, id)
    if connection.kind in {"http_api", "web_search"}:
        from app.tools.connections import validate_connection_config
        validate_connection_config(connection.kind, connection.config, True)
        if not connection.active:
            raise ValueError("Active la conexión antes de probarla")
        return {"configured": True, "network_test": False, "notice": "Configuración válida. Pruebe una llamada mediante un agente autorizado; guardar/probar configuración no consume API ni conecta redes privadas."}
    db_engine = connection_engine(connection)
    try:
        with db_engine.connect() as db:
            from sqlalchemy import text

            db.execute(text("SELECT 1"))
        return {"connected": True}
    finally:
        db_engine.dispose()
