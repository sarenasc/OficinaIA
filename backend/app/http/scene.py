import copy
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app import models as m
from app.agents.failures import failure_info, task_error
from app.core.audit import redact
from app.core.db import get_session
from app.http.common import get_or_404, router, serialize


class Point(BaseModel):
    x: float = Field(ge=100, le=1100, allow_inf_nan=False)
    y: float = Field(ge=130, le=3800, allow_inf_nan=False)


class Room(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=60)
    x: float = Field(ge=60, le=1140, allow_inf_nan=False)
    y: float = Field(ge=120, le=3800, allow_inf_nan=False)
    width: float = Field(ge=200, le=1080, allow_inf_nan=False)
    depth: float = Field(ge=200, le=3600, allow_inf_nan=False)
    door: Literal['top', 'bottom', 'left', 'right'] = 'bottom'

    @model_validator(mode='after')
    def bounds(self):
        if self.x + self.width > 1140 or self.y + self.depth > 3900:
            raise ValueError('La sala debe quedar dentro del plano')
        return self


class Partition(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    x: float = Field(ge=60, le=1140, allow_inf_nan=False)
    y: float = Field(ge=120, le=3800, allow_inf_nan=False)
    length: float = Field(ge=160, le=3600, allow_inf_nan=False)
    orientation: Literal['horizontal', 'vertical'] = 'horizontal'
    doorway: bool = True

    @model_validator(mode='after')
    def bounds(self):
        if (self.orientation == 'horizontal' and self.x + self.length > 1140
                or self.orientation == 'vertical' and self.y + self.length > 3900):
            raise ValueError('La división debe quedar dentro del plano')
        return self


class Layout(BaseModel):
    revision: int = Field(ge=0)
    desks: dict[str, Point] = Field(max_length=500)
    rooms: list[Room] | None = Field(default=None, max_length=40)
    partitions: list[Partition] | None = Field(default=None, max_length=80)

    @model_validator(mode='after')
    def unique_ids(self):
        items = [*(self.rooms or []), *(self.partitions or [])]
        if len({item.id for item in items}) != len(items):
            raise ValueError('Cada sala y división debe tener un identificador único')
        return self


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
                "error": task_error(session, task) if task.error else redact(execution.error or ""),
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
                "error": task_error(session, task),
                "updated_at": task.created_at.isoformat(),
            }
            activity_dates[task.agent_id] = task.created_at
        failure = failure_info(session, task)
        if failure and failure['agent_id'] != task.agent_id:
            failed_id = failure['agent_id']
            if failed_id not in latest or task.created_at > activity_dates[failed_id]:
                latest[failed_id] = {
                    'task_id': task.id, 'request': task.request, 'task_status': task.status,
                    'tool': '', 'error': failure['reason'], 'updated_at': task.created_at.isoformat(),
                }
                activity_dates[failed_id] = task.created_at
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
    previous = visual.get('floorplan', {})
    layout = {
        "revision": payload.revision + 1,
        "desks": {key: point.model_dump() for key, point in payload.desks.items()},
        "rooms": [room.model_dump() for room in payload.rooms] if payload.rooms is not None else previous.get('rooms', []),
        "partitions": [part.model_dump() for part in payload.partitions] if payload.partitions is not None else previous.get('partitions', []),
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
