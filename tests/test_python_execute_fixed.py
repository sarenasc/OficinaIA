import json
import os

from app.core.db import SessionLocal
from app.models import Setting
from test_execution_dual import native as native_worker_fixture
from test_stage3_tools import approve, run, setup

native = native_worker_fixture

def test_mean_comes_from_real_worker_and_is_audited(client, tmp_path, native):
    office, agent, _ = setup(client, tmp_path)
    client.put("/api/execution/preference", json={"mode": "native"})
    task = run(client, office, agent, "python.execute", {"operation": "statistics.mean",
               "parameters": {"values": [2, 1, 3, 0, 4]}})
    assert task["status"] == "completed", task
    result = json.loads(task["result"])
    assert result["mean"] == 2.0 and result["sum"] == 10 and result["count"] == 5
    assert result["backend"] == "native" and result["worker_pid"] != os.getpid() and result["duration_ms"] > 0
    details = client.get(f"/api/tasks/{task['id']}/details").json()
    assert any(e["tool_name"] == "python.execute" and e["output"]["mean"] == 2.0 for e in details["executions"])
    assert any(e["action"] == "tool.completed" for e in details["audit"])
    with SessionLocal() as session:
        job = session.get(Setting, "execution_job:" + result["job_id"]).value
        assert job["status"] == "completed" and job["duration_ms"] > 0 and job["fixed_operation"] == "statistics.mean"


def test_create_read_group_csv_through_single_tool(client, tmp_path, native):
    office, agent, resource = setup(client, tmp_path)
    params = {"resource_id": resource["id"], "path": "partidos.csv"}
    created = run(client, office, agent, "python.execute", {"operation": "csv.create", "parameters": {**params,
                "rows": [{"equipo": "A", "goles": 2}, {"equipo": "A", "goles": 4}, {"equipo": "B", "goles": 1}]}})
    assert created["status"] == "completed", created
    result = json.loads(created["result"])
    assert result["backend"] == "native" and result["artifact"]["verified"] and (tmp_path / "partidos.csv").exists()
    read = run(client, office, agent, "python.execute", {"operation": "csv.read", "parameters": params})
    assert read["status"] == "completed", read
    assert json.loads(read["result"])["rows"][1] == {"equipo": "A", "goles": "4"}
    grouped = run(client, office, agent, "python.execute", {"operation": "sports.group", "parameters": {
        **params, "group_column": "equipo", "value_column": "goles"}})
    assert grouped["status"] == "completed", grouped
    assert json.loads(grouped["result"])["summary"][0]["mean"] == 3.0


def test_paths_unassigned_resources_and_arbitrary_code_are_denied(client, tmp_path, native):
    office, agent, resource = setup(client, tmp_path)
    client.put("/api/execution/preference", json={"mode": "native"})
    for operation in ("csv.read", "csv.create"):
        params = {"resource_id": resource["id"], "path": "../escape.csv"}
        if operation == "csv.create":
            params["rows"] = [{"goals": 2}]
        denied = run(client, office, agent, "python.execute", {"operation": operation, "parameters": params})
        assert denied["status"] == "error" and "escap" in denied["error"]
    denied = run(client, office, agent, "python.execute", {"operation": "csv.read",
                 "parameters": {"resource_id": "not-assigned", "path": "secret.csv"}})
    assert denied["status"] == "error" and "asignado" in denied["error"]
    denied = run(client, office, agent, "python.execute", {"code": "print('must not run')", "resources": []})
    assert denied["status"] == "error" and "arbitrario" in denied["error"]


def test_mixed_code_unknown_operations_and_extra_fields_rejected(client, tmp_path, native):
    office, agent, _ = setup(client, tmp_path)
    for args in ({"operation": "statistics.mean", "parameters": {"values": [2]}, "code": "print(2)", "resources": []},
                 {"operation": "exec", "parameters": {"code": "print(2)"}},
                 {"operation": "statistics.mean", "parameters": {"values": [2], "code": "print(2)"}}):
        task = run(client, office, agent, "python.execute", args)
        assert task["status"] == "error" and "Argumentos inválidos" in task["error"]


def test_csv_modify_requires_approval_and_preserves_formula_safety(client, tmp_path, native):
    office, agent, resource = setup(client, tmp_path)
    client.patch(f"/api/agents/{agent['id']}", json={"mode": "safe"})
    file = tmp_path / "out.csv"
    file.write_text("old\noriginal\n", encoding="utf-8")
    task = run(client, office, agent, "python.execute", {"operation": "csv.create", "parameters": {
               "resource_id": resource["id"], "path": "out.csv", "rows": [{"text": "=1+1"}]}})
    assert task["status"] == "waiting_approval" and "original" in file.read_text(encoding="utf-8")
    task = approve(client, task)
    assert task["status"] == "completed", task
    assert "'=1+1" in file.read_text(encoding="utf-8")


STANDINGS = {"children": [{"standings": {"entries": [
    {"team": {"displayName": "Colo Colo"}, "stats": [{"name": "points", "value": 55}, {"name": "gamesPlayed", "value": 25}]},
    {"team": {"displayName": "=HYPERLINK(\"x\")"}, "stats": [{"name": "points", "value": 40}]},
]}}]}


def test_json_keys_and_table_extract_nested_data_without_code(client, tmp_path, native):
    office, agent, resource = setup(client, tmp_path)
    client.put("/api/execution/preference", json={"mode": "native"})
    (tmp_path / "standings.json").write_text(json.dumps(STANDINGS), encoding="utf-8")
    params = {"resource_id": resource["id"], "path": "standings.json"}
    keys = run(client, office, agent, "python.execute", {"operation": "json.keys", "parameters": {
               **params, "at": "children.0.standings.entries"}})
    assert keys["status"] == "completed", keys
    shape = json.loads(keys["result"])
    assert shape["type"] == "list" and shape["size"] == 2 and shape["keys"]["stats"] == {"type": "list", "size": 2}
    table = run(client, office, agent, "python.execute", {"operation": "json.table", "parameters": {
                **params, "rows": "children.0.standings.entries", "output_path": "posiciones.csv",
                "columns": {"equipo": "team.displayName", "puntos": "stats[name=points].value",
                            "pj": "stats[name=gamesPlayed].value"}}})
    assert table["status"] == "completed", table
    result = json.loads(table["result"])
    assert result["row_count"] == 2 and result["empty_cells"] == {"pj": 1} and "content" not in result
    assert result["artifact"]["verified"] and result["backend"] == "native"
    lines = (tmp_path / "posiciones.csv").read_text(encoding="utf-8").splitlines()
    assert lines[:2] == ["equipo,puntos,pj", "Colo Colo,55,25"]
    assert lines[2].startswith("\"'=HYPERLINK")


def test_json_operations_respect_resources_and_file_types(client, tmp_path, native):
    office, agent, resource = setup(client, tmp_path)
    client.put("/api/execution/preference", json={"mode": "native"})
    (tmp_path / "data.json").write_text(json.dumps(STANDINGS), encoding="utf-8")
    (tmp_path / "data.csv").write_text("a\n1\n", encoding="utf-8")
    table = {"rows": "children", "columns": {"a": "standings"}, "output_path": "out.csv"}
    for params, expected in (
        ({"resource_id": resource["id"], "path": "../data.json"}, "escap"),
        ({"resource_id": "not-assigned", "path": "data.json"}, "asignado"),
        ({"resource_id": resource["id"], "path": "data.csv"}, ".json"),
        ({"resource_id": resource["id"], "path": "data.json", "at": "missing.key"}, "no existe"),
    ):
        denied = run(client, office, agent, "python.execute", {"operation": "json.keys", "parameters": params})
        assert denied["status"] == "error" and expected in denied["error"], denied
    for change, expected in (({"output_path": "out.xlsx"}, ".csv"), ({"output_path": "../out.csv"}, "escap"),
                             ({"rows": "children.0"}, "lista")):
        denied = run(client, office, agent, "python.execute", {"operation": "json.table", "parameters": {
                     "resource_id": resource["id"], "path": "data.json", **table, **change}})
        assert denied["status"] == "error" and expected in denied["error"], denied
    assert not (tmp_path / "out.xlsx").exists()
