"""Repair directed sports relations, preserving all other agent configuration."""
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.audit import audit
from app.core.config import DATA_DIR
from app.core.db import SessionLocal, engine
from app.http.common import validate_domain
from app.models import Agent, AgentRelation, Office, Task
from app.tools.registry import execute_tool
from sqlalchemy import select

EXPECTED = ["Investigador Deportivo", "Analista Deportivo", "Gestor de Datos Deportivos",
            "Creador de Archivos Deportivos", "Auditor Deportivo"]
PROTECTED = ["offices", "agents", "tools", "skills", "resources", "connections", "providers",
             "agent_tools", "agent_skills", "agent_resources", "agent_connections"]


def fingerprints(connection):
    result = {}
    for table in PROTECTED:
        rows = connection.exec_driver_sql('SELECT * FROM "' + table + '"').fetchall()
        encoded = json.dumps(sorted([list(row) for row in rows], key=str), default=str, sort_keys=True).encode()
        result[table] = hashlib.sha256(encoded).hexdigest()
    return result


def main():
    if engine.dialect.name != "sqlite":
        raise RuntimeError("Esta corrección verificable está preparada para la base SQLite local")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = DATA_DIR / "verification" / ("delegation-" + timestamp)
    evidence.mkdir(parents=True)
    with SessionLocal() as session:
        offices = list(session.scalars(select(Office).where(Office.name.ilike("%deport%"))))
        if len(offices) != 1:
            raise ValueError("No se encontró una única oficina deportiva")
        office = offices[0]
        coordinator = session.get(Agent, office.coordinator_id)
        if not office.active or not coordinator or coordinator.office_id != office.id or coordinator.status != "active":
            raise ValueError("Coordinador real no disponible")
        people = list(session.scalars(select(Agent).where(Agent.office_id == office.id)))
        specialists = []
        for name in EXPECTED:
            found = [person for person in people if person.name == name]
            if len(found) != 1 or found[0].status != "active":
                raise ValueError("Especialista ausente, duplicado o no activo: " + name)
            specialists.append(found[0])
        if session.scalar(select(Task.id).where(Task.office_id == office.id,
                          Task.status.in_(["pending", "executing", "waiting_approval"]))):
            raise ValueError("Hay tareas activas; espere antes de cambiar relaciones")
        task = Task(number="VERIFY-DELEGATION-" + uuid4().hex[:8].upper(), office_id=office.id,
                    agent_id=coordinator.id, request="Diagnóstico real agents.list antes/después de corregir relaciones",
                    status="completed")
        session.add(task)
        session.commit()
        before = execute_tool(session, task, coordinator, "agents.list", {})
        with sqlite3.connect(engine.url.database) as source, sqlite3.connect(evidence / "before.db") as destination:
            source.backup(destination)
        session.close()
        # SQLite write lock prevents another task/configuration from changing during correction.
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        if session.scalar(select(Task.id).where(Task.office_id == office.id,
                          Task.status.in_(["pending", "executing", "waiting_approval"]))):
            raise ValueError("Una tarea comenzó; no se cambiaron relaciones")
        protected_before = fingerprints(session.connection())
        changes = []
        for specialist in specialists:
            forward = session.scalar(select(AgentRelation).where(AgentRelation.source_id == coordinator.id,
                                                               AgentRelation.target_id == specialist.id))
            if forward:
                continue
            reverse = session.scalar(select(AgentRelation).where(AgentRelation.source_id == specialist.id,
                                                               AgentRelation.target_id == coordinator.id))
            if not reverse:
                raise ValueError("Relación invertida esperada no existe; revisar manualmente")
            values = {"source_id": coordinator.id, "target_id": specialist.id}
            validate_domain(session, "relations", values, reverse)
            changes.append({"id": reverse.id, "specialist": specialist.name,
                            "before": {"source_id": reverse.source_id, "target_id": reverse.target_id}, "after": values})
            reverse.source_id, reverse.target_id = coordinator.id, specialist.id
        session.flush()
        if fingerprints(session.connection()) != protected_before:
            raise ValueError("Cambió configuración protegida; transacción revertida")
        session.commit()
        task = session.get(Task, task.id)
        coordinator = session.get(Agent, coordinator.id)
        after = execute_tool(session, task, coordinator, "agents.list", {})
        assert all(next(person for person in after["agents"] if person["id"] == child.id)["delegatable"] for child in specialists)
        task.result = json.dumps(after, ensure_ascii=False)
        task.finished_at = datetime.now(timezone.utc)
        session.commit()
        audit(session, "delegation.corrected", {"office_id": office.id, "coordinator_id": coordinator.id,
              "changes": changes, "protected_configuration_unchanged": True}, task.id, coordinator.id)
        proof = {"office_id": office.id, "coordinator_id": coordinator.id, "diagnostic_task_id": task.id,
                 "diagnostic_task_number": task.number, "before": before, "after": after, "changes": changes,
                 "protected_configuration_unchanged": True, "fingerprints": protected_before}
        (evidence / "correction.json").write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"evidence": str(evidence), "coordinator_id": coordinator.id,
              "changes": len(changes), "specialists": [p for p in after["agents"] if p["id"] != coordinator.id],
              "diagnostic_task": task.number, "protected_configuration_unchanged": True}, ensure_ascii=True))


if __name__ == "__main__":
    main()
