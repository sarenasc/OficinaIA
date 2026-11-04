from datetime import datetime

from app.agents.scheduler import ZONE, run_due
from app.core.db import SessionLocal
from app.models import Schedule, Task
from conftest import create


def setup(client, **schedule):
    office = create(client, "offices", name="Planta")
    agent = create(client, "agents", name="Martín", office_id=office["id"])
    row = create(client, "schedules", **{"name": "Detenciones diarias", "office_id": office["id"],
                                          "agent_id": agent["id"], "request": "Analiza las detenciones del {ayer}",
                                          "time": "07:00", "weekdays": [1, 2, 3, 4, 5], **schedule})
    return office, agent, row


def at(text):  # 2026-11-04 is a Wednesday
    return datetime.fromisoformat(text).replace(tzinfo=ZONE)


def test_schedule_fires_once_per_day_at_its_time(client):
    _, agent, row = setup(client)
    with SessionLocal() as session:
        assert run_due(session, at("2026-11-04T06:59")) == []
        started = run_due(session, at("2026-11-04T07:00"))
        assert len(started) == 1
        task = session.get(Task, started[0])
        assert task.agent_id == agent["id"] and task.request == "Analiza las detenciones del 2026-11-03"
        assert task.context["source"]["schedule_id"] == row["id"]
        assert run_due(session, at("2026-11-04T07:30")) == []  # already ran today
        session.get(Task, started[0]).status = "completed"
        session.commit()
        assert len(run_due(session, at("2026-11-05T09:15"))) == 1  # opened late: still runs that day


def test_schedule_respects_weekdays_pause_and_running_task(client):
    _, _, row = setup(client)
    with SessionLocal() as session:
        assert run_due(session, at("2026-11-07T08:00")) == []  # Saturday
        started = run_due(session, at("2026-11-04T08:00"))
        session.get(Task, started[0]).status = "executing"
        session.commit()
        assert run_due(session, at("2026-11-05T08:00")) == []  # previous task still running
        session.get(Schedule, row["id"]).active = False
        session.commit()
        assert run_due(session, at("2026-11-06T08:00")) == []


def test_schedule_validation_and_manual_run(client):
    office, agent, row = setup(client)
    base = {"name": "X", "office_id": office["id"], "agent_id": agent["id"], "request": "r"}
    assert client.post("/api/schedules", json={**base, "time": "25:00"}).status_code == 422
    assert client.post("/api/schedules", json={**base, "weekdays": [0]}).status_code == 422
    other = create(client, "offices", name="Otra")
    assert client.post("/api/schedules", json={**base, "office_id": other["id"]}).status_code == 422
    response = client.post(f"/api/schedules/{row['id']}/run")
    assert response.status_code == 200 and response.json()["number"].startswith("TASK-")
    assert "{ayer}" not in response.json()["request"]
