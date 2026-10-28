"""Docker command/staging contract tests; real Docker integration needs Docker Desktop."""

import subprocess

import pytest
from app.core.db import SessionLocal
from app.models import Agent, Task
from app.tools import sandbox
from conftest import create


def setup_agent(client, tmp_path, permissions):
    office = create(client, "offices", name="O")
    agent = create(client, "agents", name="A", office_id=office["id"], mode="trusted", permissions=["python.execute"])
    resource = create(client, "resources", name="R", path=str(tmp_path))
    assert (
        client.put(
            f"/api/agents/{agent['id']}/assignments",
            json={"resources": [{"resource_id": resource["id"], "permissions": permissions}]},
        ).status_code
        == 200
    )
    return office, agent, resource


def test_missing_docker_never_runs_host_python(client, tmp_path, monkeypatch):
    office, agent, resource = setup_agent(client, tmp_path, ["read", "create"])
    monkeypatch.setattr(sandbox.shutil, "which", lambda program: None)
    with SessionLocal() as session:
        with pytest.raises(ValueError, match="aislamiento"):
            sandbox.execute_python(
                session, Task(id="test-task"), session.get(Agent, agent["id"]), "print('x')", [resource["id"]], 10
            )


@pytest.mark.parametrize("cleanup_timeout", [False, True])
def test_staged_modification_denied_without_modify(client, tmp_path, monkeypatch, cleanup_timeout):
    office, agent, resource = setup_agent(client, tmp_path, ["read", "create"])
    (tmp_path / "original.txt").write_text("before")
    monkeypatch.setattr(sandbox.shutil, "which", lambda program: "test-docker")
    def cleanup(command, **kwargs):
        if cleanup_timeout:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(sandbox.subprocess, "run", cleanup)

    class TestProcess:
        returncode = 0

        def __init__(self, command, stdout, stderr):
            from pathlib import Path

            mount = next(item for item in command if "target=/workspace/" in item)
            stage = Path(mount.split("source=", 1)[1].split(",target=", 1)[0])
            assert stage != tmp_path
            (stage / "original.txt").write_text("after")
            stdout.write(b"{}")

        def poll(self):
            return 0

    monkeypatch.setattr(sandbox.subprocess, "Popen", TestProcess)
    with SessionLocal() as session:
        with pytest.raises(PermissionError, match="modify"):
            sandbox.execute_python(
                session, Task(id="test-task"), session.get(Agent, agent["id"]), "test-only-code", [resource["id"]], 10
            )
    assert (tmp_path / "original.txt").read_text() == "before"
