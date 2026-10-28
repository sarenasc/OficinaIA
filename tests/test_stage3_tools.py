import hashlib
import json
import sqlite3

import pytest
from app.agents.engine import instructions
from app.core.db import SessionLocal
from app.models import Agent
from conftest import create, wait_task
from pypdf import PdfReader, PdfWriter


def setup(client, tmp_path):
    office = create(client, "offices", name="Etapa 3")
    agent = create(client, "agents", name="Especialista", office_id=office["id"], mode="trusted",
                   permissions=["internet.access", "sql.write", "python.execute"])
    resource = create(client, "resources", name="Pruebas", path=str(tmp_path))
    tools = client.get("/api/tools").json()
    response = client.put(f"/api/agents/{agent['id']}/assignments", json={"tools": [t["id"] for t in tools],
        "resources": [{"resource_id": resource["id"], "permissions": ["read", "create", "modify"]}]})
    assert response.status_code == 200
    return office, agent, resource


def run(client, office, agent, tool, args):
    procedure = create(client, "procedures", name="Prueba " + tool, office_id=office["id"],
                       steps=[{"agent_id": agent["id"], "tool": tool, "arguments": args}])
    task = create(client, "tasks", office_id=office["id"], agent_id=agent["id"], request="Prueba real de herramienta",
                  procedure_id=procedure["id"])
    return wait_task(client, task["id"])


def approve(client, task):
    approvals = client.get(f"/api/tasks/{task['id']}/details").json()["approvals"]
    approval = next(a for a in approvals if a["status"] == "pending")
    assert client.post(f"/api/approvals/{approval['id']}/decide", json={"approved": True}).status_code == 200
    return wait_task(client, task["id"])


def assign_connection(client, agent, connection, permissions):
    data = client.get(f"/api/agents/{agent['id']}/assignments").json()
    data["connections"] = [{"connection_id": connection["id"], "permissions": permissions}]
    assert client.put(f"/api/agents/{agent['id']}/assignments", json=data).status_code == 200


def test_pdf_create_read_merge_and_artifact_integrity(client, tmp_path):
    office, agent, resource = setup(client, tmp_path)
    args = {"resource_id": resource["id"], "path": "deporte.pdf", "title": "Informe deportivo",
            "paragraphs": ["Datos de prueba: dos equipos y tres partidos."],
            "tables": [{"headers": ["Equipo", "Goles"], "rows": [["Equipo A", 5], ["Equipo B", 3]]}],
            "charts": [{"title": "Goles", "labels": ["A", "B"], "values": [5, 3]}],
            "sources": ["Dataset local de prueba"], "footer": "Verificación Etapa 3"}
    task = run(client, office, agent, "pdf.create", args)
    assert task["status"] == "completed", task
    document = PdfReader(tmp_path / "deporte.pdf")
    assert "Informe deportivo" in document.pages[0].extract_text()
    read = run(client, office, agent, "pdf.read", {"resource_id": resource["id"], "path": "deporte.pdf"})
    assert read["status"] == "completed"
    assert '"ocr_performed": false' in read["result"]
    merged = run(client, office, agent, "pdf.merge", {"resource_id": resource["id"], "path": "combinado.pdf",
                 "sources": [{"resource_id": resource["id"], "path": "deporte.pdf"}] * 2})
    assert merged["status"] == "completed", merged
    assert len(PdfReader(tmp_path / "combinado.pdf").pages) == 2
    details = client.get(f"/api/tasks/{task['id']}/details").json()
    assert details["artifacts"] and any(a["action"] == "tool.completed" for a in details["audit"])
    result = json.loads(task["result"])
    assert result["sha256"] == hashlib.sha256((tmp_path / "deporte.pdf").read_bytes()).hexdigest()
    before = (tmp_path / "deporte.pdf").read_bytes()
    args["path"] = "../escape.pdf"
    assert run(client, office, agent, "pdf.create", args)["status"] == "error"
    assert (tmp_path / "deporte.pdf").read_bytes() == before


def test_scanned_pdf_reports_no_ocr_and_missing_source_denied(client, tmp_path):
    office, agent, resource = setup(client, tmp_path)
    writer = PdfWriter()
    writer.add_blank_page(612, 792)
    writer.write(tmp_path / "sin-texto.pdf")
    result = run(client, office, agent, "pdf.read", {"resource_id": resource["id"], "path": "sin-texto.pdf"})
    assert result["status"] == "completed"
    assert json.loads(result["result"])["possibly_scanned"]
    other = create(client, "resources", name="No autorizado", path=str(tmp_path))
    assert run(client, office, agent, "pdf.read", {"resource_id": other["id"], "path": "sin-texto.pdf"})["status"] == "error"


def test_sql_bound_parameters_approval_and_rollback(client, tmp_path):
    office, agent, _ = setup(client, tmp_path)
    path = tmp_path / "sports.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE scores (team TEXT, goals INTEGER)")
        db.executemany("INSERT INTO scores VALUES (?, ?)", [("A", 1), ("B", 2)])
    connection = create(client, "connections", name="SQLite", kind="sqlite", config={"path": str(path),
                        "writable_enabled": True, "write_tables": ["scores"], "max_write_rows": 1})
    assign_connection(client, agent, connection, ["connect", "select", "execute"])
    read = run(client, office, agent, "sql.query", {"connection_id": connection["id"],
               "query": "SELECT * FROM scores WHERE team=:team", "parameters": {"team": "A"}, "max_rows": 1})
    assert read["status"] == "completed", read
    assert json.loads(read["result"])["rows"] == [{"team": "A", "goals": 1}]
    args = {"connection_id": connection["id"], "query": "UPDATE scores SET goals=:goals WHERE team=:team",
            "parameters": {"goals": 4, "team": "A"}}
    task = run(client, office, agent, "sql.execute", args)
    assert task["status"] == "waiting_approval"
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT goals FROM scores WHERE team='A'").fetchone()[0] == 1
    assert approve(client, task)["status"] == "completed"
    args.update(query="UPDATE scores SET goals=:goals WHERE goals>0", parameters={"goals": 9})
    task = run(client, office, agent, "sql.execute", args)
    assert task["status"] == "waiting_approval"
    assert approve(client, task)["status"] == "error"
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT goals FROM scores ORDER BY team").fetchall() == [(4,), (2,)]
    for query in ["DROP TABLE scores", "DELETE FROM scores", "UPDATE scores SET goals=0", "DELETE FROM scores WHERE 1=1; DROP TABLE scores"]:
        args.update(query=query, parameters={})
        assert run(client, office, agent, "sql.execute", args)["status"] == "error"
    assign_connection(client, agent, connection, ["connect"])
    assert run(client, office, agent, "sql.query", {"connection_id": connection["id"], "query": "SELECT * FROM scores"})["status"] == "error"


def test_skill_missing_tool_blocks_before_model_call(client):
    office = create(client, "offices", name="Dependencias")
    agent = create(client, "agents", name="Analista", office_id=office["id"])
    tool = next(t for t in client.get("/api/tools").json() if t["name"] == "pdf.create")
    skill = create(client, "skills", name="PDF", instructions="Crear PDF real", required_tools=[tool["id"]])
    client.put(f"/api/agents/{agent['id']}/assignments", json={"skills": [skill["id"]]})
    with SessionLocal() as session:
        with pytest.raises(PermissionError, match="pdf.create"):
            instructions(session, session.get(Agent, agent["id"]))
