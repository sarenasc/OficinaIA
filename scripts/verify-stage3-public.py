"""Live public HTTP and file/PDF flow in an isolated DB. No production permissions changed."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.models import Agent, AgentResource, AgentTool, AuditEvent, Base, Office, Resource, Task, Tool
from app.tools.builtins import register_builtins
from app.tools.registry import execute_tool
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

root = Path("data/verification/stage3-public-flow").resolve()
if (root / "competitions-live.json").exists():
    from uuid import uuid4
    root = root / ("run-" + uuid4().hex[:8])
root.mkdir(parents=True, exist_ok=True)
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
with Session(engine, expire_on_commit=False) as session:
    register_builtins(session)
    office = Office(name="Verificación aislada")
    session.add(office)
    session.flush()
    agent = Agent(name="Investigador de prueba", office_id=office.id, permissions=["internet.access"], mode="safe")
    session.add(agent)
    session.flush()
    task = Task(number="VERIFY-STAGE3-PUBLIC", office_id=office.id, agent_id=agent.id, request="Verificación pública real")
    output = Resource(name="Salida de prueba", kind="directory", path=str(root))
    fifa = Resource(name="FIFA pública", kind="url", path="https://www.fifa.com/")
    dataset = Resource(name="StatsBomb open data", kind="url", path="https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json")
    csv_dataset = Resource(name="Football Data CSV", kind="url", path="https://football-data.co.uk/mmz4281/2526/E0.csv")
    session.add_all([task, output, fifa, dataset, csv_dataset])
    session.flush()
    for resource in [output, fifa, dataset, csv_dataset]:
        session.add(AgentResource(agent_id=agent.id, resource_id=resource.id,
                                  permissions=["read", "create"] if resource is output else ["read"]))
    for name in ["web.fetch", "web.download", "filesystem.read", "pdf.create"]:
        tool = session.scalar(select(Tool).where(Tool.name == name))
        session.add(AgentTool(agent_id=agent.id, tool_id=tool.id))
    session.commit()
    results = []
    for name, arguments in [
        ("web.fetch", {"url": fifa.path, "timeout": 20}),
        ("web.download", {"url": dataset.path, "destination": {"resource_id": output.id}, "filename": "competitions-live.json"}),
        ("web.download", {"url": csv_dataset.path, "destination": {"resource_id": output.id}, "filename": "partidos-live.csv"}),
        ("filesystem.read", {"resource_id": output.id, "path": "competitions-live.json"}),
        ("pdf.create", {"resource_id": output.id, "path": "reporte-verificacion.pdf", "title": "Verificación de acceso a datos deportivos públicos",
                        "paragraphs": ["El dataset original se descargó con la herramienta autorizada y se verificó su integridad. Este documento verifica la integración, sin predicciones deportivas."],
                        "sources": [fifa.path, dataset.path]}),
    ]:
        try:
            result = execute_tool(session, task, agent, name, arguments)
            results.append({"tool": name, "passed": True, **{k: result[k] for k in ["status", "path", "bytes", "sha256", "verified", "page_count"] if k in result}})
        except Exception as exc:
            results.append({"tool": name, "passed": False, "error": str(exc)})
    audit_count = len(list(session.scalars(select(AuditEvent))))
    report = {"isolated_database": True, "results": results, "audit_events": audit_count,
              "public_dataset_records": len(json.loads((root / "competitions-live.json").read_text())) if (root / "competitions-live.json").exists() else None}
    (root / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if not all(r["passed"] for r in results):
        raise SystemExit(1)
