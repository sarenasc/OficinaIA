"""Schedule clock: while the application is open, starts each agent's task on its day and time.

Times are America/Santiago, like the consumption figures. A schedule fires at most once per day.
If the application was closed at that time and opens later the same day, the run still happens
that day; days that passed with the application closed are not replayed.
"""

import asyncio
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.db import SessionLocal
from app.core.runtime_log import logger
from app.models import Schedule, Task

ZONE = ZoneInfo("America/Santiago")
TICK_SECONDS = 30
RUNNING = {"pending", "planning", "executing", "waiting_approval"}


def placeholders(now: datetime) -> dict:
    today = now.date()
    return {"{hoy}": today.isoformat(), "{ayer}": (today - timedelta(days=1)).isoformat(),
            "{fecha_hora}": now.strftime("%Y-%m-%d %H:%M")}


def fill(value, values: dict):
    """{hoy}, {ayer} and {fecha_hora} in the request and in procedure inputs."""
    if isinstance(value, str):
        for key, replacement in values.items():
            value = value.replace(key, replacement)
        return value
    if isinstance(value, dict):
        return {key: fill(item, values) for key, item in value.items()}
    if isinstance(value, list):
        return [fill(item, values) for item in value]
    return value


def is_due(schedule: Schedule, now: datetime) -> bool:
    if not schedule.active or schedule.last_run_date == now.date().isoformat():
        return False
    if schedule.weekdays and now.isoweekday() not in schedule.weekdays:
        return False
    return now.strftime("%H:%M") >= schedule.time


def run_due(session: Session, now: datetime | None = None) -> list[str]:
    """Create the tasks that are due; returns their ids. Errors stay on the schedule, never stop the clock."""
    from app import schemas as s
    from app.http.tasks import new_task

    now = now or datetime.now(ZONE)
    started = []
    for schedule in session.scalars(select(Schedule).where(Schedule.active.is_(True))):
        if not is_due(schedule, now):
            continue
        previous = session.get(Task, schedule.last_task_id) if schedule.last_task_id else None
        # Mark the day first: a failure must not retry every 30 seconds.
        schedule.last_run_date = now.date().isoformat()
        session.commit()
        if previous and previous.status in RUNNING:
            audit(session, "schedule.skipped", {"schedule": schedule.name, "reason": "previous_task_running",
                                                "task": previous.number}, previous.id, schedule.agent_id)
            continue
        values = placeholders(now)
        try:
            task = new_task(session, s.TaskInput(
                office_id=schedule.office_id, agent_id=schedule.agent_id,
                request=fill(schedule.request, values), priority=schedule.priority,
                procedure_id=schedule.procedure_id, inputs=fill(schedule.inputs or {}, values),
            ), source={"schedule_id": schedule.id, "schedule": schedule.name})
        except Exception as exc:  # agent disabled, procedure deleted, invalid inputs...
            session.rollback()
            detail = getattr(exc, "detail", None) or str(exc)
            audit(session, "schedule.error", {"schedule": schedule.name, "error": str(detail)[:500]},
                  None, schedule.agent_id)
            continue
        schedule.last_task_id = task.id
        session.commit()
        audit(session, "schedule.fired", {"schedule": schedule.name, "task": task.number,
                                          "inputs": json.dumps(schedule.inputs or {}, ensure_ascii=False)[:500]},
              task.id, schedule.agent_id)
        started.append(task.id)
    return started


class ScheduleClock:
    def __init__(self):
        self.running: asyncio.Task | None = None

    async def start(self):
        self.running = asyncio.create_task(self.loop())

    async def stop(self):
        if self.running:
            self.running.cancel()
            try:
                await self.running
            except asyncio.CancelledError:
                pass

    async def loop(self):
        while True:
            try:
                with SessionLocal() as session:
                    run_due(session)
            except Exception as exc:
                logger.error("Reloj de programaciones: %s: %s", type(exc).__name__, exc)
            await asyncio.sleep(TICK_SECONDS)


clock = ScheduleClock()
