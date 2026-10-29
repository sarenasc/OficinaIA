"""One dispatch service; permissions remain in the existing registry/resource layer."""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.core.audit import redact
from app.core.config import DATA_DIR, SANDBOX_IMAGE
from app.execution.catalog import validate_operation
from app.models import Setting
from app.security.permissions import ApprovalRequired, resource_path
from app.tools.files import publish_bytes

WORKER = Path(__file__).with_name("sports_worker.py")
_slots = threading.BoundedSemaphore(2)
_lock = threading.Lock()
_active = {}
_context = threading.local()


def preference(session):
    setting = session.get(Setting, "execution_backend")
    return setting.value.get("mode", "auto") if setting else "auto"


def native_python():
    if getattr(sys, "frozen", False) and os.environ.get("OFFICE_NATIVE_EXECUTABLE"):
        return Path(os.environ["OFFICE_NATIVE_EXECUTABLE"])
    return DATA_DIR / "runtime" / "native-venv" / "Scripts" / "python.exe"


def worker_environment(directory):
    # Deliberately exclude tokens, provider keys, DB URLs, user Python paths and proxies.
    result = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR") if key in os.environ}
    if getattr(sys, "frozen", False):
        # Reuse this executable's extracted runtime; never forward application secrets.
        result.update({key: value for key, value in os.environ.items() if key.startswith("_PYI_")})
    result.update(TEMP=str(directory), TMP=str(directory), PYTHONIOENCODING="utf-8")
    return result


def check_cancelled():
    event = getattr(_context, "event", None)
    if event and event.is_set():
        from app.agents.engine import TaskCancelled
        raise TaskCancelled()


def cancel(task_id):
    with _lock:
        for job in _active.values():
            if job["task_id"] == task_id:
                job["event"].set()


def fixed_parameters(session, agent, arguments, temp=None):
    name = arguments["operation"]
    parameters = dict(arguments["parameters"])
    validate_operation(name, parameters)
    resources = []
    if name in {"csv.read", "sports.group", "json.keys", "json.table"}:
        suffix = ".json" if name.startswith("json.") else ".csv"
        resource_id = parameters.pop("resource_id")
        if name == "json.table":
            output = parameters.pop("output_path")
            if not output.lower().endswith(".csv"):
                raise ValueError("output_path debe terminar en .csv")
            resource_path(session, agent, resource_id, output, "create")
        original = resource_path(session, agent, resource_id, parameters["path"], "read")
        if original.suffix.lower() != suffix or original.stat().st_size > 20 * 1024 * 1024:
            raise ValueError(f"La operación requiere un archivo {suffix} autorizado de hasta 20 MB")
        resources = [resource_id]
        if temp is None:
            parameters["path"] = "/workspace/" + resource_id + "/" + parameters["path"].replace("\\", "/")
        else:
            with original.open("rb") as source:
                content = source.read(20 * 1024 * 1024 + 1)
            if len(content) > 20 * 1024 * 1024:
                raise ValueError("El archivo excede 20 MB")
            staged = temp / ("input" + suffix)
            staged.write_bytes(content)
            parameters["path"] = str(staged)
    elif name == "csv.create":
        if not parameters["path"].lower().endswith(".csv"):
            raise ValueError("El archivo debe tener extensión .csv")
        resource_path(session, agent, parameters.pop("resource_id"), parameters.pop("path"), "create")
    return name, parameters, resources


class ExecutionBackend(ABC):
    @abstractmethod
    def execute(self, session, task, agent, operation, arguments, timeout):
        raise NotImplementedError


class DockerExecutionBackend(ExecutionBackend):
    def execute(self, session, task, agent, operation, arguments, timeout):
        from app.tools.sandbox import execute_python
        if operation == "python.execute" and "operation" in arguments:
            name, parameters, resources = fixed_parameters(session, agent, arguments)
            source = WORKER.read_text(encoding="utf-8").split('if __name__ == "__main__":')[0]
            code = source + "\nprint(json.dumps(run_operation(" + json.dumps(name) + ",json.loads(" + \
                   repr(json.dumps(parameters, allow_nan=False)) + ")),allow_nan=False))"
            return execute_python(session, task, agent, code, resources, timeout)["data"]
        if operation == "python.execute":
            if not shutil.which("docker"):
                raise PermissionError("Python arbitrario requiere aislamiento Docker; Docker no está instalado o no está en PATH. "
                                      "Sin Docker use python.execute con operation y parameters, por ejemplo statistics.mean")
            return execute_python(session, task, agent, arguments["code"], arguments["resources"], timeout)
        if operation == "python.packages":
            code = ('import importlib.metadata as m,json;print(json.dumps({p:m.version(p) for p in '
                    '["pandas","numpy","scipy","scikit-learn","statsmodels","matplotlib","openpyxl"]}))')
            return execute_python(session, task, agent, code, [], timeout)
        source = WORKER.read_text(encoding="utf-8").split('if __name__ == "__main__":')[0]
        path = "/workspace/" + arguments["resource_id"] + "/" + arguments["path"].replace("\\", "/")
        code = source + "\nprint(json.dumps(analyze(" + ",".join(json.dumps(v) for v in
               (path, arguments["group_column"], arguments["value_column"])) + ")))"
        return execute_python(session, task, agent, code, [arguments["resource_id"]], timeout)["data"]


class WindowsExecutionBackend(ExecutionBackend):
    def execute(self, session, task, agent, operation, arguments, timeout):
        parameterized = operation == "python.execute" and "operation" in arguments
        if operation not in {"sports.analyze", "python.packages"} and not parameterized:
            raise PermissionError("Windows nativo bloquea Python arbitrario. Seleccione Docker para python.execute")
        if sys.platform != "win32" or not native_python().is_file():
            raise ValueError("Trabajador Windows no preparado; ejecute scripts/setup_native_worker.py")
        # A locked leftover must never replace the timeout/cancel/result outcome.
        with TemporaryDirectory(prefix="office-native-", ignore_cleanup_errors=True) as directory:
            temp = Path(directory)
            if operation == "python.packages":
                argument = "--diagnostic"
            elif parameterized:
                name, parameters, _ = fixed_parameters(session, agent, arguments, temp)
                job = temp / "arguments.json"
                job.write_text(json.dumps({"operation": name, "parameters": parameters}, allow_nan=False), encoding="utf-8")
                argument = str(job)
            else:
                original = resource_path(session, agent, arguments["resource_id"], arguments["path"], "read")
                if original.suffix.lower() != ".csv" or original.stat().st_size > 20 * 1024 * 1024:
                    raise ValueError("Análisis deportivo requiere CSV de hasta 20 MB")
                source = temp / "input.csv"
                with original.open("rb") as handle:
                    content = handle.read(20 * 1024 * 1024 + 1)
                if len(content) > 20 * 1024 * 1024:
                    raise ValueError("CSV excede 20 MB")
                source.write_bytes(content)
                job = temp / "arguments.json"
                job.write_text(json.dumps({"path": str(source), "group_column": arguments["group_column"],
                                           "value_column": arguments["value_column"]}), encoding="utf-8")
                argument = str(job)
            from app.execution.windows_limits import WorkerLimits
            process = None
            limits = None
            try:
                with (temp / "out").open("w+b") as out, (temp / "err").open("w+b") as err:
                    command = ([str(native_python()), "--native-worker", argument]
                               if getattr(sys, "frozen", False) else
                               [str(native_python()), "-I", str(WORKER), argument])
                    process = subprocess.Popen(command,
                                               cwd=temp, env=worker_environment(temp), stdout=out, stderr=err,
                                               creationflags=0x08000000 | 0x4)  # hidden, suspended until Job Object attached
                    limits = WorkerLimits(process)
                    limits.resume(process)
                    start = time.monotonic()
                    while process.poll() is None:
                        check_cancelled()
                        if time.monotonic() - start >= timeout:
                            raise TimeoutError("Trabajador Windows excedió el timeout")
                        if (temp / "out").stat().st_size + (temp / "err").stat().st_size > 1024 * 1024:
                            raise ValueError("Trabajador excedió 1 MB de salida")
                        time.sleep(0.05)
                    check_cancelled()
                    out.seek(0)
                    err.seek(0)
                    if process.returncode:
                        raise ValueError("Operación deportiva falló: " + err.read(4000).decode("utf-8", errors="replace"))
                    result = json.loads(out.read(1024 * 1024))
                    result["worker_pid"] = process.pid
                    return result
            finally:
                if limits:
                    limits.close()
                if process and process.poll() is None:
                    process.kill()
                if process:
                    process.wait(timeout=5)
                release_outputs(temp)


def release_outputs(directory: Path):
    """Windows can release a killed worker's output handles shortly after its job empties."""
    deadline = time.monotonic() + 2
    for name in ("err", "out"):
        while True:
            try:
                (directory / name).unlink(missing_ok=True)
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    break
                time.sleep(0.05)


def execute(session, task, agent, operation, arguments, timeout):
    mode = preference(session)
    parameterized = operation == "python.execute" and "operation" in arguments
    arbitrary = operation == "python.execute" and not parameterized
    if parameterized:
        validate_operation(arguments["operation"], arguments["parameters"])
    if mode == "native" and arbitrary:
        raise PermissionError("Windows nativo bloquea Python arbitrario. Seleccione Docker")
    selected = "docker" if mode == "docker" or arbitrary else "native"
    if mode == "auto" and selected == "native" and (sys.platform != "win32" or not native_python().is_file()):
        selected = "docker"
    if operation == "sports.analyze":
        resource_path(session, agent, arguments["resource_id"], arguments["path"], "read")
        if "output_path" in arguments:
            if not arguments["output_path"].lower().endswith(".json"):
                raise ValueError("Salida de análisis debe ser .json")
            output = resource_path(session, agent, arguments["resource_id"], arguments["output_path"], "create")
            if output.exists():
                raise ValueError("Use un nombre nuevo para el resultado deportivo")
    if not _slots.acquire(timeout=1):
        raise ValueError("Hay dos trabajos activos; intente después")
    id = str(uuid4())
    start = time.monotonic()
    event = threading.Event()
    record = {"id": id, "task_id": task.id, "agent_id": agent.id, "backend": selected,
              "operation": operation, "status": "running", "started_at": datetime.now(timezone.utc).isoformat()}
    if parameterized:
        record["fixed_operation"] = arguments["operation"]
    row = Setting(key="execution_job:" + id, value=dict(record))
    session.add(row)
    with _lock:
        _active[id] = {"task_id": task.id, "event": event}
    try:
        session.commit()
    except Exception:
        with _lock:
            _active.pop(id, None)
        _slots.release()
        raise
    _context.event = event
    try:
        result = (DockerExecutionBackend() if selected == "docker" else WindowsExecutionBackend()).execute(
            session, task, agent, operation, arguments, timeout)
        check_cancelled()
        if parameterized and arguments["operation"] == "csv.create":
            parameters = arguments["parameters"]
            result["artifact"] = publish_bytes(session, task, agent, parameters["resource_id"], parameters["path"],
                                               result.pop("content").encode("utf-8"), "python.execute/csv.create")
        if parameterized and arguments["operation"] == "json.table":
            parameters = arguments["parameters"]
            result["artifact"] = publish_bytes(session, task, agent, parameters["resource_id"], parameters["output_path"],
                                               result.pop("content").encode("utf-8"), "python.execute/json.table")
        if operation == "sports.analyze" and "output_path" in arguments:
            result["artifact"] = publish_bytes(session, task, agent, arguments["resource_id"], arguments["output_path"],
                                               json.dumps(result, ensure_ascii=False).encode("utf-8"), operation)
        record["status"] = "completed"
        return {**result, "backend": selected, "job_id": id, "duration_ms": int((time.monotonic() - start) * 1000)}
    except BaseException as exc:
        record.update(status="cancelled" if event.is_set() else "waiting_approval" if isinstance(exc, ApprovalRequired)
                      else "timeout" if isinstance(exc, TimeoutError) else "error",
                      error="Cancelado" if event.is_set() else redact(str(exc) or type(exc).__name__))
        raise
    finally:
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        record["duration_ms"] = int((time.monotonic() - start) * 1000)
        try:
            row.value = dict(record)
            session.commit()
        finally:
            with _lock:
                _active.pop(id, None)
            _context.event = None
            _slots.release()


def diagnostics(session):
    docker = {"available": False, "error": "Docker no está en PATH", "tools": ["python.execute", "python.packages", "sports.analyze"]}
    if shutil.which("docker"):
        try:
            check = subprocess.run(["docker", "image", "inspect", SANDBOX_IMAGE], capture_output=True, timeout=5,
                                   creationflags=0x08000000 if sys.platform == "win32" else 0)
            docker.update(available=check.returncode == 0, error=None if check.returncode == 0 else "Daemon o imagen no disponible")
        except (OSError, subprocess.TimeoutExpired) as exc:
            docker["error"] = type(exc).__name__
    native = {"available": False, "error": "Trabajador Windows no preparado",
              "tools": ["python.execute (operation/parameters)", "sports.analyze", "python.packages"]}
    if sys.platform == "win32" and native_python().is_file():
        try:
            # This probes the actual worker + Windows limits, not just the executable's existence.
            native.update(WindowsExecutionBackend().execute(None, None, None, "python.packages", {}, 5))
            native.update(available=True, error=None)
        except Exception as exc:
            native["error"] = str(exc)
    from sqlalchemy import select
    jobs = [dict(row.value) for row in session.scalars(select(Setting).where(Setting.key.like("execution_job:%"))
            .order_by(Setting.value["started_at"].as_string().desc()).limit(100))]
    with _lock:
        active_ids = set(_active)
    for job in jobs:
        if job["status"] == "running" and job["id"] not in active_ids:
            job.update(status="interrupted", error="Backend reiniciado; trabajo no se reejecuta automáticamente")
    jobs.sort(key=lambda job: job["started_at"], reverse=True)
    return {"mode": preference(session), "docker": docker, "native": native, "jobs": jobs[:20],
            "active_jobs": len(active_ids), "last_error": next((job.get("error") for job in jobs if job.get("error")), None)}


def recover_jobs(session):
    from sqlalchemy import select
    for row in session.scalars(select(Setting).where(Setting.key.like("execution_job:%"))):
        if row.value.get("status") == "running":
            row.value = {**row.value, "status": "interrupted", "error": "Backend reiniciado; no se reejecuta automáticamente"}
    session.commit()
