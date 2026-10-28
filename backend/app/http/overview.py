import shutil

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models as m
from app.core.db import engine, get_session
from app.http.common import router


@router.get("/health")
def health():
    return {
        "status": "ok",
        "database": engine.dialect.name,
        "docker_installed": bool(shutil.which("docker")),
        "ollama_installed": bool(shutil.which("ollama")),
        "windows_secrets": __import__("sys").platform == "win32",
    }


@router.get("/dashboard")
def dashboard(session: Session = Depends(get_session)):
    counts = {
        key: session.scalar(select(func.count()).select_from(cls))
        for key, cls in {"offices": m.Office, "agents": m.Agent, "tasks": m.Task, "artifacts": m.Artifact}.items()
    }
    counts["task_states"] = dict(session.execute(select(m.Task.status, func.count()).group_by(m.Task.status)).all())
    executions = list(session.scalars(select(m.Execution).where(m.Execution.provider != "")))
    counts["consumption"] = {
        "local_calls": sum(e.provider == "ollama" for e in executions),
        "external_calls": sum(e.provider != "ollama" for e in executions),
        "tokens_in": sum(e.tokens_in for e in executions),
        "tokens_out": sum(e.tokens_out for e in executions),
        "estimated_usd": sum(e.cost or 0 for e in executions),
        "unpriced_calls": sum(e.cost is None for e in executions),
    }
    return counts
