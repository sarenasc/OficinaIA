"""Downloadable Excel: what each agent worked on, its current state, tokens and estimated USD by date."""

from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from zoneinfo import ZoneInfo

from fastapi import Depends
from fastapi.responses import Response
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.http.common import router
from app.models import Agent, Execution, Office, Task

ZONE = ZoneInfo("America/Santiago")
STATES = {"working": "Trabajando", "waiting": "Esperando aprobación o delegación", "active": "Disponible",
          "disabled": "Desactivado"}
TASK_STATES = {"pending": "Pendiente", "planning": "Planificando", "executing": "En ejecución",
               "waiting_approval": "Esperando aprobación", "completed": "Completada", "error": "Error",
               "cancelled": "Cancelada"}
HEADER = PatternFill("solid", fgColor="1F4E5A")
USD = "0.0000"
INT = "#,##0"


def local(value: datetime | None) -> datetime | None:
    """Local wall time without tzinfo: Excel has no time zones."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(ZONE).replace(tzinfo=None)


def sheet(book: Workbook, title: str, headers: list[str], rows: list[list], formats: dict[int, str] | None = None):
    ws = book.create_sheet(title)
    ws.append(headers)
    for cell in ws[1]:
        cell.font, cell.fill = Font(bold=True, color="FFFFFF"), HEADER
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for row in rows:
        ws.append(row)
    for index, header in enumerate(headers, start=1):
        letter = get_column_letter(index)
        width = max([len(str(header))] + [len(str(r[index - 1])) for r in rows[:500] if r[index - 1] is not None])
        ws.column_dimensions[letter].width = min(60, max(10, width + 2))
        fmt = (formats or {}).get(index)
        for cell in ws[letter][1:]:
            if isinstance(cell.value, datetime):
                cell.number_format = "yyyy-mm-dd hh:mm"
            elif isinstance(cell.value, date):
                cell.number_format = "yyyy-mm-dd"
            elif fmt:
                cell.number_format = fmt
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = ws.dimensions
    return ws


def activity_workbook(session: Session, start: date, end: date) -> bytes:
    if end < start:
        raise ValueError("La fecha final debe ser igual o posterior a la inicial")
    offices = {o.id: o.name for o in session.scalars(select(Office))}
    agents = {a.id: a for a in session.scalars(select(Agent))}

    def in_range(value):
        moment = local(value)
        return moment is not None and start <= moment.date() <= end

    tasks = [t for t in session.scalars(select(Task).order_by(Task.created_at)) if in_range(t.created_at)]
    executions = [e for e in session.scalars(select(Execution).order_by(Execution.created_at)) if in_range(e.created_at)]
    calls = [e for e in executions if e.provider]
    tools = [e for e in executions if not e.provider]
    numbers = {t.id: t.number for t in session.scalars(select(Task))}

    per_task, per_agent, per_day = {}, {}, {}
    for e in calls:
        for bucket in (per_task.setdefault(e.task_id, {}), per_agent.setdefault(e.agent_id, {})):
            bucket["calls"] = bucket.get("calls", 0) + 1
            bucket["in"] = bucket.get("in", 0) + e.tokens_in
            bucket["out"] = bucket.get("out", 0) + e.tokens_out
            bucket["usd"] = bucket.get("usd", 0) + (e.cost or 0)
            bucket["unpriced"] = bucket.get("unpriced", 0) + int(e.cost is None)
        key = (local(e.created_at).date(), e.agent_id, e.provider, e.model)
        day = per_day.setdefault(key, [0, 0, 0, 0.0, 0])
        day[0] += 1
        day[1] += e.tokens_in
        day[2] += e.tokens_out
        day[3] += e.cost or 0
        day[4] += int(e.cost is None)
    participants = {}
    for e in executions:
        participants.setdefault(e.task_id, set()).add(e.agent_id)
    for t in tasks:
        participants.setdefault(t.id, set()).add(t.agent_id)

    agent_tasks, last_activity = {}, {}
    for t in tasks:
        for agent_id in participants[t.id]:
            agent_tasks.setdefault(agent_id, []).append(t)
    for e in executions:
        last_activity[e.agent_id] = max(filter(None, [last_activity.get(e.agent_id), local(e.created_at)]))

    def name(agent_id):
        agent = agents.get(agent_id)
        return agent.name if agent else agent_id

    book = Workbook()
    book.remove(book.active)

    total = {"in": sum(e.tokens_in for e in calls), "out": sum(e.tokens_out for e in calls),
             "usd": sum(e.cost or 0 for e in calls), "unpriced": sum(e.cost is None for e in calls)}
    working = [a for a in agents.values() if a.status in {"working", "waiting"}]
    summary = [
        ["Rango", f"{start.isoformat()} a {end.isoformat()} (America/Santiago)"],
        ["Generado", datetime.now(ZONE).replace(tzinfo=None)],
        ["Agentes trabajando ahora", len(working)],
        ["Agentes con actividad en el rango", len({a for a in agent_tasks})],
        ["Agentes sin actividad en el rango", len([a for a in agents.values() if a.id not in agent_tasks])],
        ["Tareas creadas", len(tasks)],
        ["Tareas completadas", sum(t.status == "completed" for t in tasks)],
        ["Tareas con error", sum(t.status == "error" for t in tasks)],
        ["Llamadas IA", len(calls)],
        ["Tokens de entrada", total["in"]],
        ["Tokens de salida", total["out"]],
        ["USD estimado", round(total["usd"], 6)],
        ["Llamadas sin tarifa configurada", total["unpriced"]],
        ["Nota", "USD estimado según las tarifas del proveedor configuradas en Oficina IA; las llamadas sin tarifa "
                 "no suman costo. Ollama local cuesta 0."],
    ]
    ws = sheet(book, "Resumen", ["Indicador", "Valor"], summary)
    ws.column_dimensions["B"].width = 60
    ws["B13"].number_format = USD

    agent_rows = []
    for agent in sorted(agents.values(), key=lambda a: (offices.get(a.office_id, ""), a.name)):
        done = agent_tasks.get(agent.id, [])
        usage = per_agent.get(agent.id, {})
        agent_rows.append([
            agent.name, offices.get(agent.office_id, ""), STATES.get(agent.status, agent.status),
            "Sí" if done else "No", len(done), sum(t.status == "completed" for t in done),
            sum(t.status == "error" for t in done), sum(t.status == "cancelled" for t in done),
            usage.get("calls", 0), usage.get("in", 0), usage.get("out", 0), round(usage.get("usd", 0), 6),
            usage.get("unpriced", 0), last_activity.get(agent.id),
            "; ".join(f"{t.number}: {t.request[:80]}" for t in done[-5:]),
        ])
    sheet(book, "Agentes", ["Agente", "Oficina", "Estado actual", "Trabajó en el rango", "Tareas", "Completadas",
                            "Con error", "Canceladas", "Llamadas IA", "Tokens entrada", "Tokens salida", "USD estimado",
                            "Llamadas sin tarifa", "Última actividad", "Últimas tareas (hasta 5)"],
          agent_rows, {5: INT, 9: INT, 10: INT, 11: INT, 12: USD})

    task_rows = []
    for t in tasks:
        usage = per_task.get(t.id, {})
        created, finished = local(t.created_at), local(t.finished_at)
        source = (t.context or {}).get("source") or {}
        task_rows.append([
            created, t.number, offices.get(t.office_id, ""), name(t.agent_id), t.request[:2000],
            TASK_STATES.get(t.status, t.status), finished,
            round((finished - created).total_seconds() / 60, 1) if finished else None,
            ", ".join(sorted(name(a) for a in participants[t.id])), usage.get("calls", 0), usage.get("in", 0),
            usage.get("out", 0), round(usage.get("usd", 0), 6),
            f"Programación: {source['schedule']}" if source.get("schedule") else "Manual", (t.error or "")[:1000],
        ])
    sheet(book, "Tareas", ["Creada", "Número", "Oficina", "Agente", "Solicitud", "Estado", "Finalizada",
                           "Duración (min)", "Agentes participantes", "Llamadas IA", "Tokens entrada", "Tokens salida",
                           "USD estimado", "Origen", "Error"],
          task_rows, {10: INT, 11: INT, 12: INT, 13: USD})

    day_rows = [[day, name(agent_id), provider, model, *values[:3], round(values[3], 6), values[4]]
                for (day, agent_id, provider, model), values in sorted(per_day.items(), key=lambda i: (i[0][0], name(i[0][1])))]
    sheet(book, "Consumo diario", ["Fecha", "Agente", "Proveedor", "Modelo", "Llamadas", "Tokens entrada",
                                   "Tokens salida", "USD estimado", "Llamadas sin tarifa"],
          day_rows, {5: INT, 6: INT, 7: INT, 8: USD})

    tool_rows = [[local(e.created_at), numbers.get(e.task_id, e.task_id), name(e.agent_id), e.tool_name, e.status,
                  e.duration_ms, (e.error or "")[:500]] for e in tools]
    sheet(book, "Herramientas", ["Fecha y hora", "Tarea", "Agente", "Herramienta", "Estado", "Duración (ms)", "Error"],
          tool_rows, {6: INT})

    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


@router.get("/reports/activity.xlsx")
def activity_report(desde: date | None = None, hasta: date | None = None, session: Session = Depends(get_session)):
    today = datetime.now(ZONE).date()
    end = hasta or today
    start = desde or end - timedelta(days=30)
    content = activity_workbook(session, start, end)
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="actividad_agentes_{start}_{end}.xlsx"'})
