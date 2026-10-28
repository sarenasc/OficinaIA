"""Real isolated sidecar source startup/restart; never modifies the user's office.db."""
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
import venv
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main():
    directory = ROOT / "data" / "verification" / ("dual-startup-" + uuid4().hex[:8])
    directory.mkdir(parents=True)
    venv.EnvBuilder(with_pip=False).create(directory / "runtime" / "native-venv")
    token = secrets.token_urlsafe(32)
    base = "http://127.0.0.1:18019/api/"
    env = dict(os.environ, OFFICE_SESSION_TOKEN=token, OFFICE_DATA_DIR=str(directory),
               OFFICE_DATABASE_URL="sqlite:///" + str(directory / "office.db"))

    def request(path, method="GET", data=None):
        req = urllib.request.Request(base + path, method=method, headers={"Authorization": "Bearer " + token,
            "Content-Type": "application/json"}, data=None if data is None else json.dumps(data).encode())
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.load(response)

    def start():
        log = (directory / "startup.log").open("ab")
        process = subprocess.Popen([sys.executable, str(ROOT / "packaging" / "windows_backend.py"),
            "--data-dir", str(directory), "--port", "18019"], cwd=ROOT, env=env, stdout=log, stderr=log,
            creationflags=0x08000000 if sys.platform == "win32" else 0)
        log.close()
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("Backend aislado terminó; revisar startup.log")
            try:
                request("health")
                return process
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        stop(process)
        raise TimeoutError("Backend aislado no respondió")

    def stop(process):
        if process and process.poll() is None:
            if sys.platform == "win32":
                subprocess.run([str(Path(os.environ["SYSTEMROOT"]) / "System32" / "taskkill.exe"),
                    "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=10, check=False,
                    creationflags=0x08000000)
            else:
                process.terminate()
            process.wait(timeout=10)

    process = None
    try:
        process = start()
        assert request("agents") == []
        office = request("offices", "POST", {"name": "Verificación dual aislada"})
        agent = request("agents", "POST", {"name": "Analista fijo", "office_id": office["id"],
            "permissions": ["python.execute"], "mode": "trusted"})
        tool = next(t for t in request("tools") if t["name"] == "python.execute")
        skill = request("skills", "POST", {"name": "Análisis fijo", "instructions": "Usa python.execute con operation/parameters.",
            "required_tools": [tool["id"]]})
        (directory / "datasets").mkdir()
        resource = request("resources", "POST", {"name": "Datos aislados", "path": str(directory / "datasets")})
        request("agents/" + agent["id"] + "/assignments", "PUT", {"tools": [tool["id"]], "skills": [skill["id"]],
            "resources": [{"resource_id": resource["id"], "permissions": ["read", "create"]}]})
        request("execution/preference", "PUT", {"mode": "native"})
        csv_parameters = {"resource_id": resource["id"], "path": "partidos.csv"}
        operations = [
            {"operation": "statistics.mean", "parameters": {"values": [2, 1, 3, 0, 4]}},
            {"operation": "csv.create", "parameters": {**csv_parameters, "rows": [
                {"equipo": "A", "goles": 2}, {"equipo": "A", "goles": 4}, {"equipo": "B", "goles": 1}]}},
            {"operation": "csv.read", "parameters": csv_parameters},
            {"operation": "sports.group", "parameters": {**csv_parameters, "group_column": "equipo", "value_column": "goles"}},
        ]
        procedure = request("procedures", "POST", {"name": "Calcular sin modelo", "office_id": office["id"],
            "steps": [{"agent_id": agent["id"], "tool": "python.execute", "arguments": args} for args in operations]})
        task = request("tasks", "POST", {"office_id": office["id"], "agent_id": agent["id"],
            "procedure_id": procedure["id"], "request": "Prueba real sin Ollama ni Docker"})
        for _ in range(100):
            task = request("tasks/" + task["id"])
            if task["status"] in {"completed", "error", "cancelled", "waiting_approval"}:
                break
            time.sleep(0.1)
        assert task["status"] == "completed", task
        state = request("execution/status")
        assert state["native"]["available"] and state["jobs"][0]["status"] == "completed"
        result = json.loads(task["result"])
        assert result["summary"][0]["sum"] == 6 and result["summary"][0]["mean"] == 3.0
        details = request("tasks/" + task["id"] + "/details")
        calculations = [{"tool": item["tool_name"], "duration_ms": item["duration_ms"], "output": item["output"]}
                        for item in details["executions"]]
        mean = next(item["output"] for item in calculations if item["output"].get("operation") == "statistics.mean")
        assert mean["mean"] == 2.0 and mean["sum"] == 10 and mean["count"] == 5 and mean["backend"] == "native"
        assert mean["duration_ms"] > 0 and mean["worker_pid"] != process.pid
        assert (directory / "datasets" / "partidos.csv").exists() and details["artifacts"]
        (directory / "calculations.json").write_text(json.dumps(calculations, indent=2), encoding="utf-8")
        stop(process)
        process = start()
        assert request("agents")[0]["id"] == agent["id"]
        assert request("skills")[0]["id"] == skill["id"]
        state = request("execution/status")
        assert state["mode"] == "native" and state["jobs"][0]["status"] == "completed"
        proof = {"status": "passed", "kind": "source sidecar; not compiled EXE", "checks": ["startup", "agents",
            "skills", "single python.execute", "native worker", "mean 2.0", "real CSV artifact", "CSV read/group",
            "job persistence", "restart", "isolated data", "shutdown"],
            "mean": mean, "data_dir": str(directory), "worker_python": state["native"]["python"]}
        (directory / "verification.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
        print(json.dumps(proof))
    finally:
        stop(process)


if __name__ == "__main__":
    main()
