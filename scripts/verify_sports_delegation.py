"""Real model/engine probes; no provider mocks, synthetic responses or configuration changes."""
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.agents.engine import instructions, run_agents
from app.core.audit import audit, redact
from app.core.config import DATA_DIR
from app.core.db import SessionLocal
from app.models import Agent, AgentRelation, Execution, Message, Office, Task
from app.tools.registry import execute_tool
from sqlalchemy import select


def collect_proof(session, task, coordinator, child):
    messages = [{"source_id": m.source_id, "target_id": m.target_id, "status": m.status,
                 "content": m.content} for m in session.scalars(select(Message).where(Message.task_id == task.id))]
    executions = [{"agent_id": e.agent_id, "provider": e.provider, "model": e.model, "tool": e.tool_name,
                   "status": e.status, "error": e.error} for e in
                  session.scalars(select(Execution).where(Execution.task_id == task.id))]
    return {"task_id": task.id, "number": task.number, "specialist": child.name, "status": task.status,
            "error": task.error, "result": task.result, "messages": messages, "executions": executions,
            "dispatch_verified": any(m["source_id"] == coordinator.id and m["target_id"] == child.id for m in messages),
            "child_response_verified": any(m["source_id"] == child.id and m["target_id"] == coordinator.id for m in messages),
            "explicit_diagnostic_action": True, "models_simulated": False}


async def probe(name):
    with SessionLocal() as session:
        office = session.scalar(select(Office).where(Office.name.ilike("%deport%")))
        coordinator = session.get(Agent, office.coordinator_id)
        child = session.scalar(select(Agent).where(Agent.office_id == office.id, Agent.name == name))
        request = "Diagnóstico de delegación explícita al " + name + ". Al recibir su respuesta final, confirma recepción sin herramientas."
        previous = session.scalar(select(Task).where(Task.office_id == office.id, Task.request == request,
                                  Task.status == "completed").order_by(Task.created_at.desc()))
        if previous and previous.context.get("diagnostic_explicit_delegate"):
            proof = collect_proof(session, previous, coordinator, child)
            if proof["dispatch_verified"] and proof["child_response_verified"]:
                print(json.dumps({"reused_actual_history": previous.number, "specialist": name}), flush=True)
                audit(session, "delegation.probe", proof, previous.id, coordinator.id)
                return proof
        if session.scalar(select(Task.id).where(Task.office_id == office.id,
                          Task.status.in_(["pending", "executing", "waiting_approval"]))):
            raise ValueError("Espere tareas activas antes del diagnóstico")
        child_request = ("Prueba breve de conectividad. No uses herramientas, no delegues ni accedas a archivos o internet. "
                         "Devuelve exclusivamente una acción final JSON con content igual a '" + name + " recibió la delegación'.")
        action = {"type": "delegate", "agent_id": child.id, "request": child_request}
        # Use the actual persisted-action/resume path. The diagnostic supplies an authorized
        # delegate action explicitly; it does NOT claim the parent model selected it.
        context = {"diagnostic_explicit_delegate": True, "frames": [{"agent_id": coordinator.id,
                   "request": request, "messages": [{"role": "system", "content": instructions(session, coordinator)},
                       {"role": "user", "content": request}], "pending": action, "steps": 0}]}
        task = Task(number="VERIFY-DELEGATE-" + uuid4().hex[:8].upper(), office_id=office.id,
                    agent_id=coordinator.id, request=request, context=context, status="executing")
        session.add(task)
        session.commit()
        initial_statuses = {coordinator.id: coordinator.status, child.id: child.status}
        print(json.dumps({"started": task.number, "specialist": name}), flush=True)
        try:
            await asyncio.wait_for(run_agents(session, task), timeout=90)
            task.status = "completed"
        except asyncio.TimeoutError:
            task.status, task.error = "error", "Diagnóstico real excedió 90 s; no se cambió modelo ni proveedor"
        except Exception as exc:
            task.status, task.error = "error", redact(str(exc))
        finally:
            task.finished_at = datetime.now(timezone.utc)
            for execution in session.scalars(select(Execution).where(Execution.task_id == task.id, Execution.status == "running")):
                execution.status, execution.error = "error", "Interrumpida por timeout del diagnóstico"
            for id, state in initial_statuses.items():
                session.get(Agent, id).status = state
            session.commit()
        proof = collect_proof(session, task, coordinator, child)
        audit(session, "delegation.probe", proof, task.id, coordinator.id)
        print(json.dumps(proof, ensure_ascii=True), flush=True)
        return proof


async def main():
    evidence = DATA_DIR / "verification" / ("delegation-probes-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    evidence.mkdir(parents=True)
    proofs = []
    for name in ("Investigador Deportivo", "Analista Deportivo"):
        proofs.append(await probe(name))
        (evidence / "probes.json").write_text(json.dumps(proofs, ensure_ascii=False, indent=2), encoding="utf-8")
    # New session rereads persisted directed relations and executes agents.list again.
    with SessionLocal() as session:
        office = session.scalar(select(Office).where(Office.name.ilike("%deport%")))
        coordinator = session.get(Agent, office.coordinator_id)
        task = session.get(Task, proofs[-1]["task_id"])
        listed = execute_tool(session, task, coordinator, "agents.list", {})
        targets = list(session.scalars(select(AgentRelation.target_id).where(AgentRelation.source_id == coordinator.id)))
        assert len(targets) == 5
        assert all(person["delegatable"] for person in listed["agents"] if person["id"] != coordinator.id)
        (evidence / "persistence.json").write_text(json.dumps({"relations": targets, "agents_list": listed}, indent=2), encoding="utf-8")
    print(json.dumps({"evidence": str(evidence), "all_five_delegatable": True}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
