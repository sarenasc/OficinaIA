import json
import math

import pytest
from app.agents.calculations import terminal_values, verified_final
from app.agents.engine import instructions, model_tool_result, run_agents
from app.ai.providers import AIResponse, canonical_action, providers
from app.core.db import SessionLocal
from app.execution.sports_worker import run_operation
from app.models import Agent, AuditEvent, Execution, Task
from conftest import create
from sqlalchemy import select
from test_execution_dual import native as native_worker_fixture
from test_stage3_tools import run, setup

native = native_worker_fixture
REQUEST = "Ejecuta mediante python.execute un cálculo con los goles [2,1,3,0,4] y calcula su promedio."
ACTION = {"type": "tool", "name": "python.execute", "arguments": {
    "operation": "statistics.mean", "parameters": {"values": [2, 1, 3, 0, 4]}}}


@pytest.mark.parametrize("values,total,mean,median,deviation", [
    ([2, 1, 3, 0, 4], 10, 2, 2, math.sqrt(2)),
    ([1, 2, 3, 4], 10, 2.5, 2.5, math.sqrt(1.25)),
    ([7], 7, 7, 7, 0),
    ([-2, -1, 0, 1, 2], 0, 0, 0, math.sqrt(2)),
    ([0.1, 0.2, 0.3], 0.6, 0.2, 0.2, math.sqrt(0.02 / 3)),
])
def test_real_process_regression(client, tmp_path, native, values, total, mean, median, deviation):
    office, agent, _ = setup(client, tmp_path)
    client.put("/api/execution/preference", json={"mode": "native"})
    task = run(client, office, agent, "python.execute", {"operation": "statistics.mean", "parameters": {"values": values}})
    assert task["status"] == "completed", task
    output = json.loads(task["result"])
    assert output["worker_pid"] > 0 and output["backend"] == "native"
    for key, expected in {"sum": total, "mean": mean, "median": median, "population_stddev": deviation}.items():
        assert output[key] == pytest.approx(expected), (key, output)
    details = client.get(f"/api/tasks/{task['id']}/details").json()
    execution = next(e for e in details["executions"] if e["tool_name"] == "python.execute")
    event = next(e for e in details["audit"] if e["action"] == "tool.completed")
    assert execution["output"] == event["details"]["output"] == output
    assert model_tool_result(output) == output


@pytest.mark.parametrize("values", [[], [True], [float("nan")], [float("inf")], [1e13]])
def test_invalid_statistics_rejected(values):
    with pytest.raises(ValueError):
        run_operation("statistics.mean", {"values": values})


def test_untrusted_fields_removed_and_complex_workflow_not_shortcut():
    dirty = {**ACTION, "result": {"sum_total": 14}, "execution_time": "inventado"}
    assert canonical_action(dirty) == ACTION
    assert terminal_values(REQUEST) == [2, 1, 3, 0, 4]
    assert terminal_values(REQUEST + " Guarda un Excel y delega al auditor.") is None
    assert verified_final("Lee un CSV, calcula y guarda un informe", ACTION, {}) is None
    assert terminal_values("Calcula promedio de [true].") is None


@pytest.mark.parametrize("denied", [False, True])
@pytest.mark.parametrize("routed", [False, True])
async def test_dirty_model_real_worker_no_second_call_and_permissions(client, tmp_path, native, monkeypatch, denied, routed):
    office, person, _ = setup(client, tmp_path)
    provider = create(client, "providers", name="Prueba", kind="ollama", url="http://127.0.0.1:11434", default_model="test")
    calls = []

    async def complete(*args):
        calls.append(args)
        assert len(calls) == 1, "No debe reescribir los cálculos en una segunda llamada"
        return AIResponse({**ACTION, "result": {"sum_total": 14}}, 100, 30, {"load_ms": 1})

    monkeypatch.setattr(providers["ollama"], "complete", complete)
    with SessionLocal() as session:
        agent = session.get(Agent, person["id"])
        agent.provider_id = provider["id"]
        if denied:
            agent.permissions = []
        task = Task(number="VERIFY-CALC", office_id=office["id"], agent_id=agent.id, request=REQUEST, status="executing")
        if not routed:
            task.context = {"frames": [{"agent_id": agent.id, "request": REQUEST, "steps": 0,
                "messages": [{"role": "system", "content": instructions(session, agent)}, {"role": "user", "content": REQUEST}],
                "pending": None}]}
        session.add(task)
        session.commit()
        if denied:
            with pytest.raises(PermissionError):
                await run_agents(session, task)
            assert not task.result
        else:
            await run_agents(session, task)
            output = json.loads(task.result)
            assert output["sum"] == 10 and output["median"] == 2 and output["population_stddev"] == pytest.approx(math.sqrt(2))
            assert output["worker_pid"] > 0
            tool = session.scalar(select(Execution).where(Execution.task_id == task.id, Execution.tool_name == "python.execute"))
            assert output == {"tool": "python.execute", **tool.output}
            assert session.scalar(select(AuditEvent).where(AuditEvent.task_id == task.id, AuditEvent.action == "calculation.verified"))
        event = session.scalar(select(AuditEvent).where(AuditEvent.task_id == task.id, AuditEvent.action == "model.action_sanitized"))
        assert bool(event) is not routed
        if event:
            assert event.details["ignored_fields"] == ["result"]
        event = session.scalar(select(AuditEvent).where(AuditEvent.task_id == task.id, AuditEvent.action == "model.completed"))
        if event:
            assert event.details["metrics"]["load_ms"] == 1
        assert len(calls) == (0 if routed else 1)


def test_changed_values_cannot_finish_as_requested():
    changed = {**ACTION, "arguments": {"operation": "statistics.mean", "parameters": {"values": [14]}}}
    with pytest.raises(ValueError, match="cambió"):
        verified_final(REQUEST, changed, {})


async def test_premature_model_final_is_not_accepted(client, tmp_path, monkeypatch):
    office, person, _ = setup(client, tmp_path)
    provider = create(client, "providers", name="Prueba", kind="ollama", url="http://127.0.0.1:11434", default_model="test")

    async def complete(*args):
        return AIResponse({"type": "final", "content": {"sum_total": 14}})

    monkeypatch.setattr(providers["ollama"], "complete", complete)
    with SessionLocal() as session:
        agent = session.get(Agent, person["id"])
        agent.provider_id = provider["id"]
        task = Task(number="VERIFY-INVENTED", office_id=office["id"], agent_id=agent.id, request=REQUEST, status="executing")
        task.context = {"frames": [{"agent_id": agent.id, "request": REQUEST, "steps": 0,
            "messages": [{"role": "system", "content": instructions(session, agent)}, {"role": "user", "content": REQUEST}],
            "pending": None}]}
        session.add(task)
        session.commit()
        with pytest.raises(ValueError, match="sin resultado verificado"):
            await run_agents(session, task)
        assert not task.result
