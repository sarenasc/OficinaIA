"""Apply sports office tools only; never grant folders or database connections."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.audit import audit
from app.core.db import SessionLocal
from app.models import Agent, AgentTool, Office, Task, Tool
from app.tools.builtins import register_builtins
from sqlalchemy import select

PROFILES = {
    "Investigador Deportivo": (["web.search", "web.fetch", "web.download", "api.request"], ["internet.access"]),
    "Analista Deportivo": (["python.execute", "python.packages", "filesystem.read"], ["python.execute"]),
    "Gestor de Datos Deportivos": (["filesystem.read", "filesystem.write", "sql.query"], []),
    "Creador de Archivos Deportivos": (["filesystem.read", "filesystem.write", "pdf.create", "pdf.read", "pdf.merge"], []),
    "Auditor Deportivo": (["filesystem.read", "sql.query"], []),
    "Coordinador": (["agents.list", "tasks.status"], []),
    "Coordinador Deportivo": (["agents.list", "tasks.status"], []),
}

with SessionLocal() as session:
    offices = list(session.scalars(select(Office).where(Office.name.ilike("%deport%"))))
    if len(offices) != 1:
        raise SystemExit("Se requiere una única oficina deportiva; configure las asignaciones manualmente")
    office = offices[0]
    if session.scalar(select(Task.id).where(Task.office_id == office.id,
                       Task.status.in_(["pending", "executing", "waiting_approval"]))):
        raise SystemExit("Espere que terminen las tareas de la oficina antes de aplicar perfiles")
    register_builtins(session)
    changes = []
    for agent in session.scalars(select(Agent).where(Agent.office_id == office.id)):
        profile = PROFILES.get(agent.name)
        if not profile:
            continue
        names, permissions = profile
        if agent.name == "Auditor Deportivo" and "python.execute" in agent.permissions:
            names = [*names, "python.execute", "python.packages"]
        for name in names:
            tool = session.scalar(select(Tool).where(Tool.name == name))
            if not session.get(AgentTool, (agent.id, tool.id)):
                session.add(AgentTool(agent_id=agent.id, tool_id=tool.id))
        agent.permissions = list(dict.fromkeys([*agent.permissions, *permissions]))
        changes.append({"agent_id": agent.id, "name": agent.name, "added_tools": names})
    session.commit()
    audit(session, "stage3.profiles", {"office_id": office.id, "changes": changes,
                                       "resources_granted": False, "connections_granted": False})
    print("Perfiles aplicados. Sin conexiones ni carpetas nuevas; SQL de escritura no concedido automáticamente.")
