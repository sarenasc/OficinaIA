from datetime import datetime, timezone
from io import BytesIO

from app.core.db import SessionLocal
from app.models import Execution, Task
from conftest import create
from openpyxl import load_workbook


def test_activity_report_by_date_range(client):
    office = create(client, "offices", name="Planta")
    martin = create(client, "agents", name="Martín", office_id=office["id"])
    jose = create(client, "agents", name="José", office_id=office["id"])
    with SessionLocal() as session:
        inside = Task(number="TASK-R-1", office_id=office["id"], agent_id=martin["id"], request="Pareto de detenciones",
                      status="completed", created_at=datetime(2026, 11, 3, 13, tzinfo=timezone.utc),
                      finished_at=datetime(2026, 11, 3, 13, 12, tzinfo=timezone.utc))
        outside = Task(number="TASK-R-2", office_id=office["id"], agent_id=jose["id"], request="Antigua",
                       status="completed", created_at=datetime(2026, 9, 1, 13, tzinfo=timezone.utc))
        session.add_all([inside, outside])
        session.flush()
        session.add_all([
            Execution(task_id=inside.id, agent_id=martin["id"], provider="anthropic", model="claude-sonnet-5-5",
                      status="completed", tokens_in=1000, tokens_out=200, cost=0.004,
                      created_at=datetime(2026, 11, 3, 13, 1, tzinfo=timezone.utc)),
            Execution(task_id=inside.id, agent_id=martin["id"], tool_name="sql.query", status="completed",
                      duration_ms=50, created_at=datetime(2026, 11, 3, 13, 2, tzinfo=timezone.utc)),
            Execution(task_id=outside.id, agent_id=jose["id"], provider="anthropic", model="claude-sonnet-5-5",
                      status="completed", tokens_in=5000, tokens_out=500, cost=None,
                      created_at=datetime(2026, 9, 1, 13, 1, tzinfo=timezone.utc)),
        ])
        session.commit()
    response = client.get("/api/reports/activity.xlsx?desde=2026-11-01&hasta=2026-11-04")
    assert response.status_code == 200
    assert "actividad_agentes_2026-11-01_2026-11-04.xlsx" in response.headers["content-disposition"]
    book = load_workbook(BytesIO(response.content))
    assert book.sheetnames == ["Resumen", "Agentes", "Tareas", "Consumo diario", "Herramientas"]
    agents = {row[0]: row for row in book["Agentes"].iter_rows(min_row=2, values_only=True)}
    assert agents["Martín"][3] == "Sí" and agents["Martín"][9] == 1000 and agents["Martín"][11] == 0.004
    assert agents["José"][3] == "No" and agents["José"][9] == 0  # its work is outside the range
    tasks = list(book["Tareas"].iter_rows(min_row=2, values_only=True))
    assert [t[1] for t in tasks] == ["TASK-R-1"] and tasks[0][7] == 12.0
    assert list(book["Herramientas"].iter_rows(min_row=2, values_only=True))[0][3] == "sql.query"
    bad = client.get("/api/reports/activity.xlsx?desde=2026-11-05&hasta=2026-11-01")
    assert bad.status_code == 422
