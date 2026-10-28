from conftest import create, wait_task


def test_procedure_failure_does_not_leave_agent_working(client, tmp_path):
    demo = client.post("/api/demo/install", json={"output_path": str(tmp_path)}).json()
    task = create(
        client,
        "tasks",
        office_id=demo["office"]["id"],
        agent_id=demo["agent_id"],
        request="Archivo duplicado",
        procedure_id=demo["procedure"]["id"],
        inputs={"output_name": "../forbidden.xlsx"},
    )
    result = wait_task(client, task["id"])
    assert result["status"] == "error"
    agents = client.get("/api/agents").json()
    assert all(a["status"] != "working" for a in agents)
    assert not (tmp_path.parent / "forbidden.xlsx").exists()
