import copy

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app import schemas as s
from app.core.audit import audit
from app.core.db import get_session
from app.http.common import get_or_404, router, serialize


@router.post("/offices/{id}/duplicate")
def duplicate_office(id: str, session: Session = Depends(get_session)):
    original = get_or_404(session, m.Office, id)
    office = m.Office(
        name=original.name + " (copia)",
        description=original.description,
        icon=original.icon,
        visual=copy.deepcopy(original.visual),
    )
    session.add(office)
    session.flush()
    areas = {}
    for area in session.scalars(select(m.Area).where(m.Area.office_id == id)):
        clone = m.Area(name=area.name, description=area.description, office_id=office.id)
        session.add(clone)
        session.flush()
        areas[area.id] = clone.id
    agents = {}
    for agent in session.scalars(select(m.Agent).where(m.Agent.office_id == id)):
        data = {field: copy.deepcopy(getattr(agent, field)) for field in s.AgentInput.model_fields}
        data.update(office_id=office.id, area_id=areas.get(agent.area_id), status="active")
        clone = m.Agent(**data)
        session.add(clone)
        session.flush()
        agents[agent.id] = clone.id
        # Copy knowledge/tools, but resources and connections require fresh explicit authorization.
        for assignment in session.scalars(select(m.AgentTool).where(m.AgentTool.agent_id == agent.id)):
            session.add(m.AgentTool(agent_id=clone.id, tool_id=assignment.tool_id))
        for assignment in session.scalars(select(m.AgentSkill).where(m.AgentSkill.agent_id == agent.id)):
            session.add(m.AgentSkill(agent_id=clone.id, skill_id=assignment.skill_id))
    for relation in session.scalars(select(m.AgentRelation)):
        if relation.source_id in agents and relation.target_id in agents:
            session.add(m.AgentRelation(source_id=agents[relation.source_id], target_id=agents[relation.target_id]))
    if "floorplan" in (office.visual or {}):
        visual = copy.deepcopy(office.visual)
        visual["floorplan"] = {
            "revision": 0,
            "desks": {
                agents[key]: value for key, value in visual["floorplan"].get("desks", {}).items() if key in agents
            },
        }
        office.visual = visual
    office.coordinator_id = agents.get(original.coordinator_id)
    session.commit()
    audit(session, "office.duplicated", {"source": id, "target": office.id})
    return serialize(office)
