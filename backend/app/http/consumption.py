from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.http.common import router
from app.models import Agent, Execution, Task


@router.get("/consumption")
def consumption(session: Session = Depends(get_session)):
    zone = ZoneInfo("America/Santiago")
    today = datetime.now(zone).date()
    result = {"total": {}, "day": {}, "month": {}, "by_agent": {}, "by_office": {}, "by_task": {}}

    def add(bucket, execution):
        bucket.setdefault("local_calls", 0)
        bucket.setdefault("external_calls", 0)
        bucket.setdefault("tokens_in", 0)
        bucket.setdefault("tokens_out", 0)
        bucket.setdefault("estimated_usd", 0)
        bucket.setdefault("unpriced_calls", 0)
        bucket["local_calls" if execution.provider == "ollama" else "external_calls"] += 1
        bucket["tokens_in"] += execution.tokens_in
        bucket["tokens_out"] += execution.tokens_out
        bucket["estimated_usd"] += execution.cost or 0
        bucket["unpriced_calls"] += int(execution.cost is None)

    for execution, task, agent in session.execute(
        select(Execution, Task, Agent)
        .join(Task, Execution.task_id == Task.id)
        .join(Agent, Execution.agent_id == Agent.id)
        .where(Execution.provider != "")
    ):
        date = execution.created_at
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        local_date = date.astimezone(zone).date()
        add(result["total"], execution)
        if local_date == today:
            add(result["day"], execution)
        if (local_date.year, local_date.month) == (today.year, today.month):
            add(result["month"], execution)
        for key, id in [("by_agent", agent.id), ("by_office", task.office_id), ("by_task", task.id)]:
            add(result[key].setdefault(id, {}), execution)
    return result
