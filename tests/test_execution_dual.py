import json
import sys
import threading
import time
import venv

import pytest
from app.agents.engine import TaskCancelled
from app.core.db import SessionLocal
from app.execution import service
from app.execution.sports_worker import analyze
from app.models import Agent, Setting, Task
from app.tools.registry import execute_tool
from test_stage3_tools import run, setup


@pytest.fixture
def native(tmp_path, monkeypatch):
    if sys.platform != "win32":
        pytest.skip("Trabajador real requiere Windows")
    root = tmp_path / "runtime-data"
    venv.EnvBuilder(with_pip=False).create(root / "runtime" / "native-venv")
    monkeypatch.setattr(service, "DATA_DIR", root)
    return root


def sports_setup(client, tmp_path):
    office, agent, resource = setup(client, tmp_path)
    assert client.patch(f"/api/agents/{agent['id']}", json={"permissions": ["sports.analyze", "python.execute"]}).status_code == 200
    (tmp_path / "goles.csv").write_text("equipo,goles\nA,2\nA,4\nB,1\n", encoding="utf-8")
    args = {"resource_id": resource["id"], "path": "goles.csv", "group_column": "equipo", "value_column": "goles"}
    return office, agent, resource, args


def test_native_real_analysis_artifact_jobs_and_preference(client, tmp_path, native):
    office, agent, _, args = sports_setup(client, tmp_path)
    assert client.put("/api/execution/preference", json={"mode": "native"}).json()["mode"] == "native"
    args["output_path"] = "resumen.json"
    task = run(client, office, agent, "sports.analyze", args)
    assert task["status"] == "completed", task
    data = json.loads((tmp_path / "resumen.json").read_text(encoding="utf-8"))
    assert data["rows"] == 3 and data["summary"][0]["sum"] == 6
    state = client.get("/api/execution/status").json()
    assert state["native"]["available"], state
    assert state["native"]["packages"]["stdlib"]
    assert state["active_jobs"] == 0 and state["jobs"][0]["status"] == "completed"
    assert client.get(f"/api/tasks/{task['id']}/details").json()["artifacts"]
    with SessionLocal() as session:
        assert service.preference(session) == "native"
        assert session.get(Setting, "execution_job:" + state["jobs"][0]["id"]).value["status"] == "completed"


def test_native_rejects_arbitrary_code_before_process(client, tmp_path, native):
    office, agent, _, _ = sports_setup(client, tmp_path)
    client.put("/api/execution/preference", json={"mode": "native"})
    task = run(client, office, agent, "python.execute", {"code": "raise Exception('must not run')", "resources": []})
    assert task["status"] == "error" and "arbitrario" in task["error"]


def test_native_path_and_capability_denial(client, tmp_path, native):
    office, agent, _, args = sports_setup(client, tmp_path)
    args["path"] = "../secret.csv"
    assert run(client, office, agent, "sports.analyze", args)["status"] == "error"
    args["path"] = "goles.csv"
    client.patch(f"/api/agents/{agent['id']}", json={"permissions": []})
    denied = run(client, office, agent, "sports.analyze", args)
    assert denied["status"] == "error" and "Permisos" in denied["error"]


def test_worker_rejects_nonfinite_and_missing_columns(tmp_path):
    file = tmp_path / "bad.csv"
    file.write_text("team,goals\nA,nan\n", encoding="utf-8")
    with pytest.raises(ValueError, match="finito"):
        analyze(file, "team", "goals")
    with pytest.raises(ValueError, match="Columnas"):
        analyze(file, "team", "wrong")


def test_worker_environment_excludes_secrets(monkeypatch, tmp_path):
    monkeypatch.setenv("OFFICE_SESSION_TOKEN", "must-not-inherit")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "must-not-inherit")
    env = service.worker_environment(tmp_path)
    assert "must-not-inherit" not in str(env) and "PATH" not in env and "PYTHONPATH" not in env


def test_native_real_timeout_and_cancel_process_cleanup(client, tmp_path, native, monkeypatch):
    office, agent, _, args = sports_setup(client, tmp_path)
    client.put("/api/execution/preference", json={"mode": "native"})
    # TEST-ONLY trusted worker fixture, never selectable by agents in production.
    sleeper = tmp_path / "sleep_worker.py"
    sleeper.write_text("import time\ntime.sleep(15)\n", encoding="utf-8")
    monkeypatch.setattr(service, "WORKER", sleeper)
    with SessionLocal() as session:
        task = Task(number="TEST-TIMEOUT", office_id=office["id"], agent_id=agent["id"], request="Prueba directa", status="executing")
        session.add(task)
        session.commit()
        task_id = task.id
    # Direct tool execution verifies real process timeout without a model request.
    with SessionLocal() as session:
        current = session.get(Task, task_id)
        current.status = "executing"
        session.commit()
        person = session.get(Agent, agent["id"])
        with pytest.raises(TimeoutError):
            service.execute(session, current, person, "sports.analyze", args, 0.1)
    timer = threading.Timer(0.2, service.cancel, args=(task_id,))
    timer.start()
    try:
        with SessionLocal() as session:
            with pytest.raises(TaskCancelled):
                execute_tool(session, session.get(Task, task_id), session.get(Agent, agent["id"]), "sports.analyze", args)
    finally:
        timer.join()
    assert not service._active
    state = client.get("/api/execution/status").json()
    assert {job["status"] for job in state["jobs"]} == {"timeout", "cancelled"}


def test_auto_never_downgrades_arbitrary_python(client, tmp_path, monkeypatch):
    office, agent, _, _ = sports_setup(client, tmp_path)
    from app.tools import sandbox
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: None)
    task = run(client, office, agent, "python.execute", {"code": "print('unsafe')", "resources": []})
    assert task["status"] == "error" and "Docker" in task["error"]
    state = client.get("/api/execution/status").json()
    assert state["jobs"][0]["backend"] == "docker"


def test_preference_validation_and_missing_worker(client, tmp_path, monkeypatch):
    assert client.put("/api/execution/preference", json={"mode": "unsafe"}).status_code == 422
    monkeypatch.setattr(service, "DATA_DIR", tmp_path / "not-prepared")
    state = client.get("/api/execution/status").json()
    assert not state["native"]["available"]


def test_interrupted_job_is_not_reexecuted(client):
    with SessionLocal() as session:
        session.add(Setting(key="execution_job:old", value={"id": "old", "task_id": "old", "operation": "sports.analyze",
                    "status": "running", "started_at": "2000-01-01", "backend": "native"}))
        session.commit()
    state = client.get("/api/execution/status").json()
    assert state["jobs"][0]["status"] == "interrupted"


def test_auto_selects_real_native_and_packages(client, tmp_path, native):
    office, agent, _, args = sports_setup(client, tmp_path)
    task = run(client, office, agent, "sports.analyze", args)
    assert task["status"] == "completed", task
    assert json.loads(task["result"])["backend"] == "native"
    packages = run(client, office, agent, "python.packages", {})
    assert packages["status"] == "completed", packages
    assert json.loads(packages["result"])["packages"]["stdlib"]


def test_http_cancel_stops_real_worker_without_publication(client, tmp_path, native, monkeypatch):
    office, agent, _, args = sports_setup(client, tmp_path)
    sleeper = tmp_path / "sleep-http.py"
    sleeper.write_text("import time\ntime.sleep(20)\n", encoding="utf-8")
    monkeypatch.setattr(service, "WORKER", sleeper)
    args["output_path"] = "must-not-exist.json"
    from conftest import create, wait_task
    procedure = create(client, "procedures", name="Cancelación", office_id=office["id"],
                       steps=[{"agent_id": agent["id"], "tool": "sports.analyze", "arguments": args}])
    task = create(client, "tasks", office_id=office["id"], agent_id=agent["id"], request="Cancelación de prueba",
                  procedure_id=procedure["id"])
    for _ in range(100):
        if service._active:
            break
        time.sleep(0.02)
    assert service._active
    assert client.post(f"/api/tasks/{task['id']}/cancel").json()["status"] == "cancelled"
    for _ in range(100):
        if not service._active:
            break
        time.sleep(0.02)
    assert not service._active and not (tmp_path / "must-not-exist.json").exists()
    assert wait_task(client, task["id"])["status"] == "cancelled"
    with SessionLocal() as session:
        from sqlalchemy import select
        job = session.scalar(select(Setting).where(Setting.key.like("execution_job:%")))
        assert job.value["status"] == "cancelled"
