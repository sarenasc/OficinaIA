import hashlib
import json
import logging
import shutil
import subprocess
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.config import SANDBOX_IMAGE
from app.models import Agent, Artifact, Task
from app.security.permissions import require_approval, resource_path

MAX_BYTES = 50 * 1024 * 1024
_slots = threading.BoundedSemaphore(2)


def snapshot(root: Path) -> dict[str, str]:
    files, total = {}, 0
    for path in root.rglob("*"):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise PermissionError("Sandbox no acepta enlaces ni junctions")
        if path.is_file():
            total += path.stat().st_size
            if total > MAX_BYTES or len(files) >= 1000:
                raise ValueError("Sandbox excede 50 MB o 1000 archivos por recurso")
            files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def execute_python(session: Session, task: Task, agent: Agent, code: str, resources: list[str], timeout: int):
    if not _slots.acquire(timeout=1):
        raise ValueError("Hay dos ejecuciones Python simultáneas; espere y vuelva a intentar")
    try:
        return _execute_python(session, task, agent, code, resources, timeout)
    finally:
        _slots.release()


def _execute_python(session: Session, task: Task, agent: Agent, code: str, resources: list[str], timeout: int):
    if not shutil.which("docker"):
        raise ValueError("Docker no está instalado o no está en PATH. Python nunca se ejecuta sin aislamiento")
    from app.models import AgentResource

    name = "office-" + task.id + "-" + agent.id[:8]
    with TemporaryDirectory(prefix="office-script-") as temp:
        mounts, staged = [], []
        for resource_id in resources:
            root = resource_path(session, agent, resource_id, "", "read")
            if not root.is_dir() or "," in str(root):
                raise PermissionError("Montaje requiere carpeta sin comas")
            assignment = session.get(AgentResource, (agent.id, resource_id))
            permissions = set(assignment.permissions)
            writable = bool(permissions & {"create", "modify", "delete"})
            if agent.mode == "safe" and permissions & {"modify", "delete"}:
                require_approval(
                    session,
                    task,
                    agent,
                    "python-write",
                    {"resource_id": resource_id, "code": code, "permissions": sorted(permissions)},
                    "Python podrá publicar modificaciones o eliminaciones en esta carpeta autorizada",
                )
            before = snapshot(root)
            stage = Path(temp) / resource_id
            stage.mkdir()
            for relative in before:
                source = resource_path(session, agent, resource_id, relative, "read")
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            staged.append((resource_id, root, stage, before))
            mounts += [
                "--mount",
                f"type=bind,source={stage},target=/workspace/{resource_id}" + ("" if writable else ",readonly"),
            ]
        script = Path(temp) / "main.py"
        script.write_text(code, encoding="utf-8")
        command = [
            "docker",
            "run",
            "--rm",
            "--pull",
            "never",
            "--name",
            name,
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--pids-limit",
            "64",
            "--user",
            "10001:10001",
            "--tmpfs",
            "/tmp:rw,nosuid,size=64m",
            "--env", "MPLCONFIGDIR=/tmp/matplotlib",
            "--env", "OMP_NUM_THREADS=1",
            "--env", "OPENBLAS_NUM_THREADS=1",
            "--mount",
            f"type=bind,source={script},target=/app/main.py,readonly",
            *mounts,
            SANDBOX_IMAGE,
            "python",
            "-I",
            "/app/main.py",
        ]
        process = None
        try:
            # Files cap captured output rather than allowing unbounded PIPE memory.
            with (Path(temp) / "stdout").open("w+b") as out, (Path(temp) / "stderr").open("w+b") as err:
                process = subprocess.Popen(command, stdout=out, stderr=err)
                start = time.monotonic()
                while process.poll() is None:
                    from app.execution.service import check_cancelled
                    check_cancelled()
                    if time.monotonic() - start > timeout:
                        raise TimeoutError("Python excedió el timeout")
                    if (Path(temp) / "stdout").stat().st_size + (
                        Path(temp) / "stderr"
                    ).stat().st_size > 2 * 1024 * 1024:
                        raise ValueError("Python excedió 2 MB de salida")
                    for _, _, stage, _ in staged:
                        if (
                            sum(p.stat().st_size for p in stage.rglob("*") if p.is_file() and not p.is_symlink())
                            > MAX_BYTES
                        ):
                            raise ValueError("Python excedió el espacio de trabajo")
                    time.sleep(0.2)
                out.seek(0)
                err.seek(0)
                stdout = out.read(100000).decode("utf-8", errors="replace")
                stderr = err.read(100000).decode("utf-8", errors="replace")
            if process.returncode:
                raise ValueError("Python falló: " + stderr[:4000])
            from app.execution.service import check_cancelled
            check_cancelled()
            changes = []
            for resource_id, root, stage, before in staged:
                after = snapshot(stage)
                if snapshot(root) != before:
                    raise ValueError("Carpeta cambió durante ejecución; no se publicaron cambios Python")
                for relative in set(before) | set(after):
                    action = (
                        "delete"
                        if relative not in after
                        else "create"
                        if relative not in before
                        else "modify"
                        if before[relative] != after[relative]
                        else None
                    )
                    if action:
                        destination = resource_path(session, agent, resource_id, relative, action)
                        changes.append((resource_id, stage / relative, destination, action))
            # Validate every permission before changing Windows files.
            for resource_id, source, destination, action in changes:
                if action == "delete":
                    destination.unlink()
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with (
                        source.open("rb") as input_file,
                        destination.open("xb" if action == "create" else "wb") as output_file,
                    ):
                        shutil.copyfileobj(input_file, output_file)
                    session.add(
                        Artifact(
                            task_id=task.id,
                            agent_id=agent.id,
                            resource_id=resource_id,
                            path=str(destination),
                            name=destination.name,
                        )
                    )
                audit(session, "python.file." + action, {"path": str(destination)}, task.id, agent.id)
            result = {
                "stdout": stdout,
                "stderr": stderr,
                "mounts": {r: f"/workspace/{r}" for r in resources},
                "files": [{"path": str(dest), "action": action} for _, _, dest, action in changes],
            }
            try:
                result["data"] = json.loads(stdout)
            except json.JSONDecodeError:
                pass
            return result
        finally:
            try:
                cleanup = subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15, check=False)
                if cleanup.returncode:
                    logging.getLogger(__name__).warning("No se pudo confirmar limpieza del contenedor %s", name)
            except (OSError, subprocess.TimeoutExpired):
                # A cleanup failure must not mask user cancellation or prevent closing the client.
                logging.getLogger(__name__).warning("Falló limpieza Docker del contenedor %s", name)
            finally:
                if process and process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
