import copy

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app import models as m
from app.core.audit import redact
from app.core.db import get_session
from app.http.common import get_or_404, router, serialize


class Point(BaseModel):
    x: float = Field(ge=100, le=1100, allow_inf_nan=False)
    y: float = Field(ge=130, le=3800, allow_inf_nan=False)


class Layout(BaseModel):
    revision: int = Field(ge=0)
    desks: dict[str, Point] = Field(max_length=500)


@router.get("/offices/{id}/scene")
def scene(id: str, session: Session = Depends(get_session)):
    office = get_or_404(session, m.Office, id)
    agents = list(
        session.scalars(select(m.Agent).where(m.Agent.office_id == id).order_by(m.Agent.created_at, m.Agent.id))
    )
    latest = {}
    activity_dates = {}
    executions = session.scalars(
        select(m.Execution)
        .join(m.Task, m.Execution.task_id == m.Task.id)
        .where(m.Task.office_id == id)
        .order_by(m.Execution.created_at.desc())
        .limit(500)
    )
    for execution in executions:
        if execution.agent_id not in latest:
            task = session.get(m.Task, execution.task_id)
            inputs = execution.input or {}
            outputs = execution.output or {}
            resource = session.get(m.Resource, inputs.get("resource_id")) if inputs.get("resource_id") else None
            activity_dates[execution.agent_id] = execution.created_at
            latest[execution.agent_id] = {
                "task_id": task.id,
                "request": task.request,
                "task_status": task.status,
                "tool": execution.tool_name,
                "execution_status": execution.status,
                "path": redact(outputs.get("path") or inputs.get("path") or ""),
                "resource": resource.name if resource else "",
                "error": redact(execution.error or task.error or ""),
                "updated_at": execution.created_at.isoformat(),
            }
    for task in session.scalars(
        select(m.Task).where(m.Task.office_id == id).order_by(m.Task.created_at.desc()).limit(100)
    ):
        if task.agent_id not in latest or task.created_at > activity_dates[task.agent_id]:
            latest[task.agent_id] = {
                "task_id": task.id,
                "request": task.request,
                "task_status": task.status,
                "tool": "",
                "error": redact(task.error or ""),
                "updated_at": task.created_at.isoformat(),
            }
            activity_dates[task.agent_id] = task.created_at
    return {
        "office": {"id": office.id, "name": office.name},
        "layout": (office.visual or {}).get("floorplan", {"revision": 0, "desks": {}}),
        "agents": [{**serialize(agent), "activity": latest.get(agent.id)} for agent in agents],
        "messages": [
            {
                "id": message.id,
                "source_id": message.source_id,
                "target_id": message.target_id,
                "task_id": message.task_id,
            }
            for message in session.scalars(
                select(m.Message)
                .join(m.Task, m.Message.task_id == m.Task.id)
                .where(m.Task.office_id == id)
                .order_by(m.Message.created_at.desc())
                .limit(30)
            )
        ],
    }


@router.put("/offices/{id}/layout")
def save_layout(id: str, payload: Layout, session: Session = Depends(get_session)):
    office = get_or_404(session, m.Office, id)
    allowed = set(session.scalars(select(m.Agent.id).where(m.Agent.office_id == id)))
    if not set(payload.desks).issubset(allowed):
        raise HTTPException(422, "El plano contiene agentes de otra oficina o eliminados")
    visual = copy.deepcopy(office.visual or {})
    layout = {
        "revision": payload.revision + 1,
        "desks": {key: point.model_dump() for key, point in payload.desks.items()},
    }
    visual["floorplan"] = layout
    revision = func.coalesce(m.Office.visual["floorplan"]["revision"].as_integer(), 0)
    result = session.execute(
        update(m.Office).where(m.Office.id == id, revision == payload.revision).values(visual=visual),
        execution_options={"synchronize_session": False},
    )
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(409, "El plano cambió; recargue antes de guardar")
    session.commit()
    return layout
