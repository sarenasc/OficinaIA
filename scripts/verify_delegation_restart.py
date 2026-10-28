"""Restart a real backend on a SQLite clone; do not interrupt the user's running app."""
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main():
    directory = ROOT / "data" / "verification" / ("delegation-restart-" + uuid4().hex[:8])
    directory.mkdir(parents=True)
    with sqlite3.connect('file:' + str(ROOT / 'data/office.db') + '?mode=ro', uri=True) as source:
        if source.execute("SELECT count(*) FROM tasks WHERE status IN ('pending','executing','waiting_approval')").fetchone()[0]:
            raise RuntimeError("Espere a terminar las pruebas/tareas antes de clonar")
        with sqlite3.connect(directory / "office.db") as target:
            source.backup(target)
    token = secrets.token_urlsafe(32)
    env = dict(os.environ, OFFICE_DATA_DIR=str(directory), OFFICE_SESSION_TOKEN=token,
               OFFICE_DATABASE_URL="sqlite:///" + str(directory / "office.db"))

    def request(path, method="GET", data=None):
        req = urllib.request.Request("http://127.0.0.1:18021/api/" + path, method=method,
              headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
              data=None if data is None else json.dumps(data).encode())
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.load(response)

    def stop(process):
        if process and process.poll() is None:
            subprocess.run([str(Path(os.environ["SYSTEMROOT"]) / "System32/taskkill.exe"), "/PID", str(process.pid),
                           "/T", "/F"], capture_output=True, timeout=10, check=False, creationflags=0x08000000)
            process.wait(timeout=10)

    process = None
    proof = {"production_restart": False, "cloned_database": True, "runs": []}
    try:
        for iteration in range(2):
            with (directory / "startup.log").open("ab") as log:
                process = subprocess.Popen([sys.executable, str(ROOT / "packaging/windows_backend.py"),
                    "--data-dir", str(directory), "--port", "18021"], env=env, cwd=ROOT, stdout=log, stderr=log,
                    creationflags=0x08000000)
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Backend clonado no arrancó")
                try:
                    request("health")
                    break
                except urllib.error.URLError:
                    time.sleep(0.1)
            office = next(office for office in request("offices") if office["id"] == "65b73f64-36d5-44af-8f57-8ec1c22ec697")
            coordinator = office["coordinator_id"]
            relations = [relation for relation in request("relations") if relation["source_id"] == coordinator]
            assert len(relations) == 5
            procedure = request("procedures", "POST", {"name": "Diagnóstico reinicio " + str(iteration),
                "office_id": office["id"], "steps": [{"agent_id": coordinator, "tool": "agents.list", "arguments": {}}]})
            task = request("tasks", "POST", {"office_id": office["id"], "agent_id": coordinator,
                "procedure_id": procedure["id"], "request": "agents.list real sin llamar al modelo"})
            for _ in range(100):
                task = request("tasks/" + task["id"])
                if task["status"] in {"completed", "error"}:
                    break
                time.sleep(0.05)
            assert task["status"] == "completed", task
            listed = json.loads(task["result"])
            children = [agent for agent in listed["agents"] if agent["id"] != coordinator]
            assert len(children) == 5 and all(agent["delegatable"] for agent in children)
            proof["runs"].append({"iteration": iteration, "relations": relations, "agents_list": listed,
                                  "task_id": task["id"], "status": task["status"]})
            stop(process)
        proof["status"] = "passed"
        (directory / "verification.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
        print(json.dumps({"status": "passed", "evidence": str(directory), "restarts": 1,
                          "specialists_delegatable": 5, "production_process_untouched": True}))
    finally:
        stop(process)


if __name__ == "__main__":
    main()
