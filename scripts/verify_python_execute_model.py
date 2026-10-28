"""Original natural-language prompt, real configured Ollama, isolated SQLite clone."""
import asyncio
import json
import math
import os
import sqlite3
import subprocess
import sys
import time
import venv
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


async def child(directory, calculations=False):
    sys.path.insert(0, str(ROOT / "backend"))
    from app.agents.engine import run_agents
    from app.core.audit import redact
    from app.core.db import SessionLocal
    from app.models import Agent, AuditEvent, Execution, Task
    from app.tools.builtins import register_builtins
    from sqlalchemy import select

    with SessionLocal() as session:
        register_builtins(session)
        agent = session.scalar(select(Agent).where(Agent.name == "Analista Deportivo"))
        previous_status = agent.status
        source_task = session.scalar(select(Task).where(Task.number == "TASK-2026-FC8801FB")) if calculations else None
        request = source_task.request if source_task else "Ejecuta mediante python.execute un cálculo con los goles [2,1,3,0,4] y calcula su promedio."
        if calculations:
            historical = {"number": source_task.number, "id": source_task.id, "request": source_task.request,
                          "result": source_task.result,
                          "executions": [{"id": e.id, "duration_ms": e.duration_ms, "provider": e.provider,
                            "model": e.model, "tokens_in": e.tokens_in, "tokens_out": e.tokens_out,
                            "tool": e.tool_name, "input": e.input, "output": e.output}
                            for e in session.scalars(select(Execution).where(Execution.task_id == source_task.id))],
                          "audit": [{"id": e.id, "action": e.action, "details": e.details}
                            for e in session.scalars(select(AuditEvent).where(AuditEvent.task_id == source_task.id))]}
            (directory / "historical-audit.json").write_text(json.dumps(redact(historical), ensure_ascii=False, indent=2), encoding="utf-8")
        task = Task(number="VERIFY-PYTHON-MODEL-" + uuid4().hex[:8].upper(), office_id=agent.office_id,
                    agent_id=agent.id, request=request,
                    status="executing")
        session.add(task)
        session.commit()
        start = time.monotonic()
        try:
            await asyncio.wait_for(run_agents(session, task), timeout=120)
            task.status = "completed"
        except asyncio.TimeoutError:
            task.status, task.error = "error", "Diagnóstico del modelo excedió 120 s"
        except Exception as exc:
            task.status, task.error = "error", redact(str(exc))
        finally:
            agent.status = previous_status
            task.finished_at = datetime.now(timezone.utc)
            for item in session.scalars(select(Execution).where(Execution.task_id == task.id, Execution.status == "running")):
                item.status, item.error = "error", "Interrumpido por el diagnóstico"
            session.commit()
        executions = [{"tool": item.tool_name, "provider": item.provider, "model": item.model,
                       "status": item.status, "duration_ms": item.duration_ms, "input": item.input,
                       "output": item.output, "error": item.error}
                      for item in session.scalars(select(Execution).where(Execution.task_id == task.id))]
        computed = [item["output"] for item in executions if item["tool"] == "python.execute" and
                    item["status"] == "completed" and item["output"].get("mean") == 2.0 and item["output"].get("backend") == "native"]
        if calculations:
            computed = [value for value in computed if value.get("sum") == 10 and value.get("median") == 2
                        and math.isclose(value.get("population_stddev", -1), math.sqrt(2))]
            final = json.loads(task.result) if task.status == "completed" else {}
            if not computed or final != {"tool": "python.execute", **computed[0]}:
                computed = []
        proof = {"status": "passed" if computed and task.status == "completed" else "failed", "task_status": task.status,
                 "task_id": task.id, "error": task.error, "result": task.result, "computations": computed,
                 "executions": executions, "models_simulated": False, "production_database_modified": False,
                 "elapsed_ms": int((time.monotonic() - start) * 1000),
                 "model_calls": sum(bool(item["provider"]) for item in executions),
                 "audit": [{"action": item.action, "details": item.details} for item in session.scalars(
                     select(AuditEvent).where(AuditEvent.task_id == task.id))]}
        (directory / "verification.json").write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": proof["status"], "task_status": task.status, "error": task.error,
                          "elapsed_ms": proof["elapsed_ms"], "model_calls": proof["model_calls"],
                          "computations": computed, "evidence": str(directory)}, ensure_ascii=True))


def main():
    calculations = "--calculations" in sys.argv
    if len(sys.argv) > 1 and sys.argv[1] != "--calculations":
        asyncio.run(child(Path(sys.argv[1]), calculations))
        return
    directory = ROOT / "data/verification" / ("python-model-" + uuid4().hex[:8])
    directory.mkdir(parents=True)
    with sqlite3.connect('file:' + str(ROOT / 'data/office.db') + '?mode=ro', uri=True) as source:
        if source.execute("SELECT count(*) FROM tasks WHERE status IN ('pending','executing','waiting_approval')").fetchone()[0]:
            raise RuntimeError("Espere tareas activas antes de clonar el diagnóstico")
        with sqlite3.connect(directory / "office.db") as target:
            source.backup(target)
    venv.EnvBuilder(with_pip=False).create(directory / "runtime/native-venv")
    env = dict(os.environ, OFFICE_DATA_DIR=str(directory), OFFICE_DATABASE_URL="sqlite:///" + str(directory / "office.db"))
    subprocess.run([sys.executable, str(Path(__file__).resolve()), str(directory),
                    *(["--calculations"] if calculations else [])], env=env, check=True)


if __name__ == "__main__":
    main()
