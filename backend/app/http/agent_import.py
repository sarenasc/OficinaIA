"""Atomic, validated agent batches. Import never runs agents or grants resources."""
from fastapi import Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app import schemas as s
from app.core.audit import audit
from app.core.db import get_session
from app.http.common import get_or_404, router, validate_domain


class ImportedAgent(s.AgentInput):
    office_id: str = ""
    key: str = Field(min_length=1, max_length=100)
    delegates: list[str] = Field(default_factory=list, max_length=100)
    tools: list[str] = Field(default_factory=list, max_length=100)


class AgentBatch(s.Input):
    version: int = Field(default=1, ge=1, le=1)
    agents: list[ImportedAgent] = Field(min_length=1, max_length=100)
    coordinator: str | None = None


def validate_batch(session: Session, office: m.Office, batch: AgentBatch):
    keys, names, parsed, tool_ids = set(), set(), {}, {}
    existing = {name.casefold() for name in session.scalars(select(m.Agent.name).where(m.Agent.office_id == office.id))}
    occupied = [a.position for a in session.scalars(select(m.Agent).where(m.Agent.office_id == office.id))]
    for entry in batch.agents:
        if entry.key in keys or entry.name.strip().casefold() in names | existing:
            raise ValueError(f"Clave o nombre duplicado: {entry.key} / {entry.name}")
        if not entry.name.strip():
            raise ValueError("El nombre no puede estar vacío")
        keys.add(entry.key)
        names.add(entry.name.strip().casefold())
        if entry.office_id and entry.office_id != office.id:
            raise ValueError("Todos los agentes deben pertenecer a la oficina seleccionada")
        data = entry.model_dump(exclude={"key", "delegates", "tools"})
        data["office_id"] = office.id
        data["name"] = entry.name.strip()
        if "position" not in entry.model_fields_set:
            index = 0
            while True:
                position = {"x": 100 + (index % 3) * 300, "y": 100 + (index // 3) * 240}
                if all(abs(p.get("x", 0) - position["x"]) >= 260 or
                       abs(p.get("y", 0) - position["y"]) >= 220 for p in occupied):
                    data["position"] = position
                    break
                index += 1
        occupied.append(data["position"])
        validate_domain(session, "agents", data)
        parsed[entry.key] = data
        tool_ids[entry.key] = []
        for name in set(entry.tools):
            tool = session.scalar(select(m.Tool).where(m.Tool.name == name, m.Tool.active.is_(True)))
            if not tool:
                raise ValueError(f"Herramienta inexistente o inactiva: {name}")
            tool_ids[entry.key].append(tool.id)
    if batch.coordinator and batch.coordinator not in keys:
        raise ValueError("El coordinador debe ser una clave del archivo")
    if batch.coordinator and office.coordinator_id:
        raise ValueError("La oficina ya tiene coordinador. Omita coordinator para conservarlo")
    edges = {entry.key: set(entry.delegates) for entry in batch.agents}

    visited = set()

    def visit(key, path):
        if key not in keys:
            raise ValueError(f"Agente delegado no definido: {key}")
        if key in path:
            raise ValueError("Las delegaciones no pueden formar ciclos")
        if key in visited:
            return
        for target in edges[key]:
            visit(target, path | {key})
        visited.add(key)

    for key in keys:
        visit(key, set())
    return parsed, tool_ids, edges


@router.post("/offices/{id}/agents/import")
def import_agents(id: str, batch: AgentBatch, preview: bool = True, session: Session = Depends(get_session)):
    office = get_or_404(session, m.Office, id)
    if session.scalar(select(m.Task.id).where(m.Task.office_id == id,
                         m.Task.status.in_(["pending", "executing", "waiting_approval"]))) is not None:
        raise HTTPException(409, "Espere a que terminen las tareas de la oficina antes de importar")
    parsed, tools, edges = validate_batch(session, office, batch)
    result = {"count": len(parsed), "coordinator": batch.coordinator,
              "agents": [{"key": entry.key, "name": entry.name, "role": entry.role,
                          "model": entry.model, "tools": entry.tools, "delegates": entry.delegates,
                          "mode": entry.mode, "external_policy": entry.external_policy,
                          "permissions": entry.permissions} for entry in batch.agents]}
    if preview:
        return {**result, "created": False}
    try:
        created = {key: m.Agent(**data) for key, data in parsed.items()}
        session.add_all(created.values())
        session.flush()
        for key, agent in created.items():
            session.add_all(m.AgentTool(agent_id=agent.id, tool_id=tid) for tid in tools[key])
            session.add_all(m.AgentRelation(source_id=agent.id, target_id=created[target].id) for target in edges[key])
        if batch.coordinator:
            office.coordinator_id = created[batch.coordinator].id
        session.commit()
    except Exception:
        session.rollback()
        raise
    audit(session, "agents.imported", {"office_id": id, "count": len(created), "ids": [a.id for a in created.values()]})
    return {**result, "created": True, "ids": {key: a.id for key, a in created.items()}}
