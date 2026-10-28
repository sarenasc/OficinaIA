"""Register the sales chart procedure; never execute or modify the user's workbook."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.db import SessionLocal
from app.models import Agent, AgentTool, Procedure, Tool
from app.tools.builtins import register_builtins
from sqlalchemy import select

with SessionLocal() as session:
    register_builtins(session)
    agent = session.get(Agent, "6165e889-bd6d-4ed9-aca1-bd4c1eaa3c86")
    if not agent:
        raise SystemExit("No se encontró el Analista configurado")
    for name in ("excel.chart", "filesystem.list"):
        tool = session.scalar(select(Tool).where(Tool.name == name))
        if not session.get(AgentTool, (agent.id, tool.id)):
            session.add(AgentTool(agent_id=agent.id, tool_id=tool.id))
    name = "Graficar ventas Excel con código"
    procedure = session.scalar(select(Procedure).where(Procedure.office_id == agent.office_id, Procedure.name == name))
    if not procedure:
        session.add(Procedure(office_id=agent.office_id, name=name,
            description="Suma ventas por producto y agrega GraficoVentas al mismo archivo. Requiere aprobación en modo seguro; no llama a la IA.",
            steps=[{"agent_id": agent.id, "tool": "excel.chart", "arguments": {
                "resource_id": "b9302c94-3656-4964-ab37-070e5a0346e5",
                "path": "$input.path", "sheet": "Datos", "category_column": "producto",
                "value_column": "total", "chart_sheet": "$input.chart_sheet"}}]))
    session.commit()
    print("Analista: excel.chart y filesystem.list asignadas. Procedimiento registrado; archivo original sin modificar.")
