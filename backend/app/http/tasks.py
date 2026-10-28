import copy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app import schemas as s
from app.agents.engine import worker
from app.agents.failures import failure_info, task_error
from app.core.audit import audit
from app.core.db import get_session
from app.http.common import get_or_404, router, serialize
from app.security.permissions import resource_path


@router.post("/tasks")
async def create_task(data: s.TaskInput, session: Session = Depends(get_session)):
    office = get_or_404(session, m.Office, data.office_id)
    agent = get_or_404(session, m.Agent, data.agent_id)
    if not office.active or agent.office_id != office.id or agent.status == "disabled":
        raise HTTPException(422, "Oficina/agente no disponible")
    context = {}
    if data.procedure_id:
        procedure = get_or_404(session, m.Procedure, data.procedure_id)
        if procedure.office_id != office.id:
            raise HTTPException(422, "Procedimiento pertenece a otra oficina")
        context = {"procedure_steps": copy.deepcopy(procedure.steps), "inputs": data.inputs, "outputs": []}
    id = str(uuid4())
    task = m.Task(
        id=id,
        number=f"TASK-{datetime.now().year}-{id[:8].upper()}",
        office_id=office.id,
        agent_id=agent.id,
        request=data.request,
        priority=data.priority,
        context=context,
    )
    session.add(task)
    session.commit()
    audit(session, "task.created", {"request": data.request}, task.id, agent.id)
    worker.submit(task.id)
    return serialize(task)


@router.post("/tasks/{id}/cancel")
def cancel_task(id: str, session: Session = Depends(get_session)):
    task = get_or_404(session, m.Task, id)
    if task.status not in {"completed", "error", "cancelled"}:
        task.status = "cancelled"
        task.finished_at = datetime.now(timezone.utc)
        for approval in session.scalars(
            select(m.Approval).where(m.Approval.task_id == id, m.Approval.status == "pending")
        ):
            approval.status = "rejected"
            waiting = session.get(m.Agent, approval.agent_id)
            if waiting and waiting.status == "waiting":
                waiting.status = "active"
        session.commit()
        from app.execution.service import cancel
        cancel(id)
    return serialize(task)


@router.post("/approvals/{id}/decide")
async def decide_approval(id: str, data: s.ApprovalInput, session: Session = Depends(get_session)):
    approval = get_or_404(session, m.Approval, id)
    task = get_or_404(session, m.Task, approval.task_id)
    if approval.status != "pending" or task.status != "waiting_approval":
        raise HTTPException(409, "Aprobación ya resuelta o tarea no esperando")
    approval.status = "approved" if data.approved else "rejected"
    task.status = "pending" if data.approved else "cancelled"
    if not data.approved:
        ids = {approval.agent_id, task.agent_id}
        ids.update(frame["agent_id"] for frame in task.context.get("frames", []))
        for agent_id in ids:
            waiting = session.get(m.Agent, agent_id)
            if waiting and waiting.status == "waiting":
                waiting.status = "active"
    session.commit()
    audit(session, "approval." + approval.status, {"approval_id": id}, task.id, approval.agent_id)
    if data.approved:
        worker.submit(task.id)
    return serialize(approval)


@router.get("/tasks/{id}/details")
def task_details(id: str, session: Session = Depends(get_session)):
    task = get_or_404(session, m.Task, id)
    result = {"task": {**serialize(task), 'error': task_error(session, task)},
              'failure': failure_info(session, task)}
    for key, cls in {
        "executions": m.Execution,
        "messages": m.Message,
        "audit": m.AuditEvent,
        "artifacts": m.Artifact,
        "approvals": m.Approval,
    }.items():
        result[key] = [
            serialize(obj) for obj in session.scalars(select(cls).where(cls.task_id == id).order_by(cls.created_at))
        ]
    return result


@router.get("/artifacts/{id}/download")
def download_artifact(id: str, session: Session = Depends(get_session)):
    artifact = get_or_404(session, m.Artifact, id)
    agent = get_or_404(session, m.Agent, artifact.agent_id)
    resource = get_or_404(session, m.Resource, artifact.resource_id)
    relative = str(Path(artifact.path).relative_to(Path(resource.path).resolve()))
    path = resource_path(session, agent, artifact.resource_id, relative, "read")
    return FileResponse(path, filename=artifact.name)
