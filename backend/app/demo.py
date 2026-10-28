"""Optional, explicitly installed sample. Never runs on startup."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models as m
from app.api import authorize, serialize
from app.core.config import DATA_DIR
from app.core.db import get_session

router = APIRouter(prefix="/api/demo", dependencies=[Depends(authorize)])


class DemoInput(BaseModel):
    output_path: str


@router.post("/install")
def install_demo(data: DemoInput, session: Session = Depends(get_session)):
    if session.get(m.Setting, "demo"):
        raise HTTPException(409, "La demo ya existe; elimínela antes de reinstalar")
    output = Path(data.output_path)
    if (
        not output.is_absolute()
        or not output.is_dir()
        or output.is_symlink()
        or (hasattr(output, "is_junction") and output.is_junction())
    ):
        raise HTTPException(422, "Seleccione una carpeta existente para autorizar la salida demo")
    sample_dir = DATA_DIR / "demo"
    sample_dir.mkdir(exist_ok=True)
    (sample_dir / "datos.csv").write_text(
        "semana,kilos,recepciones\n1,1200,12\n2,1800,15\n3,1500,14\n4,2100,18\n", encoding="utf-8"
    )
    office = m.Office(
        name="Oficina Demo Analítica",
        description="Demo opcional CSV → resumen → Excel; no requiere API ni IA",
        demo=True,
    )
    session.add(office)
    session.flush()
    provider = session.scalar(select(m.Provider).where(m.Provider.kind == "ollama"))
    coordinator = m.Agent(
        name="Coordinador",
        office_id=office.id,
        goal="Coordinar análisis y generación de reportes",
        provider_id=provider.id,
        position={"x": 250, "y": 30},
    )
    analyst = m.Agent(
        name="Analista",
        office_id=office.id,
        goal="Leer y resumir datos",
        provider_id=provider.id,
        position={"x": 80, "y": 240},
    )
    creator = m.Agent(
        name="Generador Reportes",
        office_id=office.id,
        goal="Crear Excel y comprobar sus datos",
        provider_id=provider.id,
        position={"x": 420, "y": 240},
    )
    session.add_all([coordinator, analyst, creator])
    session.flush()
    office.coordinator_id = coordinator.id
    session.add_all(
        [
            m.AgentRelation(source_id=coordinator.id, target_id=analyst.id),
            m.AgentRelation(source_id=coordinator.id, target_id=creator.id),
        ]
    )
    source = m.Resource(name="CSV demo", path=str(sample_dir.resolve()))
    destination = m.Resource(name="Salida demo autorizada", path=str(output.resolve()))
    session.add_all([source, destination])
    session.flush()
    session.add_all(
        [
            m.AgentResource(agent_id=analyst.id, resource_id=source.id, permissions=["read"]),
            m.AgentResource(agent_id=creator.id, resource_id=destination.id, permissions=["read", "create"]),
        ]
    )
    for agent, names in [(analyst, ["csv.read", "data.summarize"]), (creator, ["excel.create", "excel.read"])]:
        for tool in session.scalars(select(m.Tool).where(m.Tool.name.in_(names))):
            session.add(m.AgentTool(agent_id=agent.id, tool_id=tool.id))
    procedure = m.Procedure(
        name="CSV demo → Excel",
        office_id=office.id,
        description="Procedimiento determinista real, sin llamadas IA",
        steps=[
            {"agent_id": analyst.id, "tool": "csv.read", "arguments": {"resource_id": source.id, "path": "datos.csv"}},
            {"agent_id": analyst.id, "tool": "data.summarize", "arguments": {"rows": "$steps.0.rows"}},
            {
                "agent_id": creator.id,
                "tool": "excel.create",
                "arguments": {
                    "resource_id": destination.id,
                    "path": "$input.output_name",
                    "rows": "$steps.0.rows",
                    "summary": "$steps.1.rows",
                },
            },
        ],
    )
    session.add(procedure)
    session.flush()
    session.add(
        m.Setting(
            key="demo",
            value={"office_id": office.id, "resource_ids": [source.id, destination.id], "procedure_id": procedure.id},
        )
    )
    session.commit()
    return {"office": serialize(office), "procedure": serialize(procedure), "agent_id": coordinator.id}


@router.delete("/remove")
def remove_demo(session: Session = Depends(get_session)):
    setting = session.get(m.Setting, "demo")
    if not setting:
        return {"removed": True}
    office_id = setting.value["office_id"]
    tasks = list(session.scalars(select(m.Task.id).where(m.Task.office_id == office_id)))
    if session.scalar(
        select(m.Task.id).where(m.Task.id.in_(tasks), m.Task.status.in_(["pending", "executing", "waiting_approval"]))
    ):
        raise HTTPException(409, "Termine o cancele las tareas demo antes de eliminar")
    for cls in [m.Approval, m.Artifact, m.AuditEvent, m.Message, m.Execution, m.Memory]:
        session.execute(delete(cls).where(cls.task_id.in_(tasks)))
    agents = list(session.scalars(select(m.Agent.id).where(m.Agent.office_id == office_id)))
    session.execute(delete(m.Memory).where(m.Memory.agent_id.in_(agents)))
    session.execute(delete(m.Task).where(m.Task.office_id == office_id))
    session.execute(delete(m.Office).where(m.Office.id == office_id))
    for id in setting.value["resource_ids"]:
        session.execute(delete(m.Resource).where(m.Resource.id == id))
    session.delete(setting)
    session.commit()
    sample = DATA_DIR / "demo" / "datos.csv"
    sample.unlink(missing_ok=True)
    # User outputs are preserved. Their removal is always the user's decision.
    return {"removed": True, "note": "Los Excel generados en su carpeta se conservan"}
