"""Real sandbox tests. Explicitly skipped when Docker or its built image is unavailable."""
import json
import shutil
import subprocess
import time

import pytest
from conftest import create, wait_task
from test_stage3_tools import run, setup


@pytest.fixture
def docker_ready():
    if not shutil.which("docker"):
        pytest.skip("Docker no está instalado; no se ejecuta Python en el host")
    result = subprocess.run(["docker", "image", "inspect", "oficina-python-sandbox:local"], capture_output=True, timeout=15)
    if result.returncode:
        pytest.skip("Docker daemon o imagen oficina-python-sandbox:local no disponible")


def test_real_csv_statistics_poisson_chart_and_package_versions(client, tmp_path, docker_ready):
    office, agent, resource = setup(client, tmp_path)
    client.put("/api/execution/preference", json={"mode": "docker"})
    (tmp_path / "partidos.csv").write_text("team,goals\nA,2\nA,1\nB,0\nB,3\n", encoding="utf-8")
    code = '''import json
from pathlib import Path
import pandas as pd
from scipy.stats import poisson
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root = Path('/workspace/RESOURCE')
data = pd.read_csv(root/'partidos.csv')
grouped = data.groupby('team')['goals'].agg(['count','sum','mean'])
grouped.to_csv(root/'estadisticas.csv')
grouped['sum'].plot.bar()
plt.savefig(root/'goles.png')
print(json.dumps({'games':len(data),'mean':float(data.goals.mean()), 'poisson_2':float(poisson.pmf(2,data.goals.mean()))}))
'''.replace("RESOURCE", resource["id"])
    result = run(client, office, agent, "python.execute", {"code": code, "resources": [resource["id"]]})
    assert result["status"] == "completed", result
    output = json.loads(result["result"])
    assert output["data"]["games"] == 4
    assert output["data"]["mean"] == 1.5
    assert 0.24 < output["data"]["poisson_2"] < 0.26
    assert (tmp_path / "goles.png").stat().st_size > 1000
    assert (tmp_path / "estadisticas.csv").exists()
    versions = run(client, office, agent, "python.packages", {})
    assert versions["status"] == "completed", versions
    assert all(json.loads(versions["result"])["data"].values())


def test_real_python_timeout_publishes_no_artifacts(client, tmp_path, docker_ready):
    office, agent, resource = setup(client, tmp_path)
    tool = next(t for t in client.get("/api/tools").json() if t["name"] == "python.execute")
    assert client.patch(f"/api/tools/{tool['id']}", json={"timeout": 1}).status_code == 200
    result = run(client, office, agent, "python.execute", {"code": "import time; time.sleep(5)", "resources": [resource["id"]]})
    assert result["status"] == "error"
    assert "timeout" in result["error"]
    assert list(tmp_path.iterdir()) == []


def test_real_fixed_mean_uses_docker(client, tmp_path, docker_ready):
    office, agent, _ = setup(client, tmp_path)
    client.put("/api/execution/preference", json={"mode": "docker"})
    result = run(client, office, agent, "python.execute", {"operation": "statistics.mean",
                 "parameters": {"values": [2, 1, 3, 0, 4]}})
    assert result["status"] == "completed", result
    assert json.loads(result["result"])["mean"] == 2.0
    assert json.loads(result["result"])["backend"] == "docker"


def test_real_docker_cgroup_cpu_and_memory_limits(client, tmp_path, docker_ready):
    office, agent, _ = setup(client, tmp_path)
    client.put("/api/execution/preference", json={"mode": "docker"})
    code = '''import json
from pathlib import Path
root = Path('/sys/fs/cgroup')
if (root/'cpu.max').exists():
    quota, period = (root/'cpu.max').read_text().split()
    memory = int((root/'memory.max').read_text())
else:
    quota = (root/'cpu/cpu.cfs_quota_us').read_text()
    period = (root/'cpu/cpu.cfs_period_us').read_text()
    memory = int((root/'memory/memory.limit_in_bytes').read_text())
print(json.dumps({'cpus':int(quota)/int(period), 'memory':memory}))'''
    result = run(client, office, agent, "python.execute", {"code": code, "resources": []})
    assert result["status"] == "completed", result
    limits = json.loads(result["result"])["data"]
    assert limits["cpus"] == 1 and limits["memory"] == 512 * 1024 * 1024


def test_real_docker_cancel_does_not_publish_staged_artifact(client, tmp_path, docker_ready):
    office, agent, resource = setup(client, tmp_path)
    client.put("/api/execution/preference", json={"mode": "docker"})
    code = f"from pathlib import Path\nimport time\nPath('/workspace/{resource['id']}/unpublished.txt').write_text('staged')\ntime.sleep(30)"
    procedure = create(client, "procedures", name="Cancelar Docker", office_id=office["id"], steps=[{
        "agent_id": agent["id"], "tool": "python.execute", "arguments": {"code": code, "resources": [resource["id"]]}}])
    task = create(client, "tasks", office_id=office["id"], agent_id=agent["id"], procedure_id=procedure["id"], request="Cancelar prueba")
    name = "office-" + task["id"] + "-" + agent["id"][:8]
    for _ in range(100):
        running = subprocess.run(["docker", "ps", "--filter", "name=" + name, "--format", "{{.Names}}"], capture_output=True, timeout=5)
        if name.encode() in running.stdout:
            break
        time.sleep(0.1)
    assert name.encode() in running.stdout
    client.post(f"/api/tasks/{task['id']}/cancel")
    assert wait_task(client, task["id"])["status"] == "cancelled"
    for _ in range(100):
        remaining = subprocess.run(["docker", "ps", "-a", "--filter", "name=" + name, "--format", "{{.Names}}"], capture_output=True, timeout=5)
        if name.encode() not in remaining.stdout:
            break
        time.sleep(0.1)
    assert name.encode() not in remaining.stdout and not (tmp_path / "unpublished.txt").exists()
