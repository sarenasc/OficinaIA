from fastapi import Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models as m
from app import schemas as s
from app.core.audit import audit
from app.core.db import get_session
from app.http.common import get_or_404, router


@router.get("/agents/{id}/assignments")
def assignments(id: str, session: Session = Depends(get_session)):
    get_or_404(session, m.Agent, id)
    return {
        "tools": list(session.scalars(select(m.AgentTool.tool_id).where(m.AgentTool.agent_id == id))),
        "skills": list(session.scalars(select(m.AgentSkill.skill_id).where(m.AgentSkill.agent_id == id))),
        "resources": [
            {"resource_id": a.resource_id, "permissions": a.permissions}
            for a in session.scalars(select(m.AgentResource).where(m.AgentResource.agent_id == id))
        ],
        "connections": [
            {"connection_id": a.connection_id, "permissions": a.permissions}
            for a in session.scalars(select(m.AgentConnection).where(m.AgentConnection.agent_id == id))
        ],
    }


@router.put("/agents/{id}/assignments")
def set_assignments(id: str, data: s.AssignmentInput, session: Session = Depends(get_session)):
    agent = get_or_404(session, m.Agent, id)
    active = session.scalar(
        select(m.Task).where(
            m.Task.status.in_(["pending", "executing", "waiting_approval"]), m.Task.office_id == agent.office_id
        )
    )
    if active:
        raise HTTPException(409, "Espere a que terminen las tareas de la oficina antes de cambiar permisos")
    for tool_id in set(data.tools):
        get_or_404(session, m.Tool, tool_id)
    for skill_id in set(data.skills):
        get_or_404(session, m.Skill, skill_id)
    for item in data.resources:
        if set(item) != {"resource_id", "permissions"} or not set(item["permissions"]).issubset(
            {"read", "create", "modify", "copy", "move", "delete", "execute"}
        ):
            raise HTTPException(422, "Asignación de recurso inválida")
        get_or_404(session, m.Resource, item["resource_id"])
    for item in data.connections:
        if set(item) != {"connection_id", "permissions"} or not set(item["permissions"]).issubset(
            {"connect", "select", "execute"}
        ):
            raise HTTPException(422, "Permisos de conexión admitidos: connect/select/execute")
        get_or_404(session, m.Connection, item["connection_id"])
    for cls in (m.AgentTool, m.AgentSkill, m.AgentResource, m.AgentConnection):
        session.execute(delete(cls).where(cls.agent_id == id))
    session.add_all([m.AgentTool(agent_id=id, tool_id=tid) for tid in set(data.tools)])
    session.add_all([m.AgentSkill(agent_id=id, skill_id=sid) for sid in set(data.skills)])
    session.add_all([m.AgentResource(agent_id=id, **item) for item in data.resources])
    session.add_all([m.AgentConnection(agent_id=id, **item) for item in data.connections])
    session.commit()
    audit(session, "agent.assignments", data.model_dump(), agent_id=id)
    return assignments(id, session)
