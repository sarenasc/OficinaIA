import json

from conftest import create, wait_task


def test_reversed_relations_control_agents_list_and_cycles(client):
    office = create(client, "offices", name="Delegación deportiva de prueba")
    parent = create(client, "agents", office_id=office["id"], name="Coordinador")
    children = [create(client, "agents", office_id=office["id"], name=name) for name in
                ["Investigador", "Analista", "Gestor", "Creador", "Auditor"]]
    tool = next(tool for tool in client.get("/api/tools").json() if tool["name"] == "agents.list")
    assert client.put(f"/api/agents/{parent['id']}/assignments", json={"tools": [tool["id"]]}).status_code == 200
    relations = [create(client, "relations", source_id=child["id"] if index < 3 else parent["id"],
                        target_id=parent["id"] if index < 3 else child["id"]) for index, child in enumerate(children)]
    procedure = create(client, "procedures", office_id=office["id"], name="Listado real",
                       steps=[{"agent_id": parent["id"], "tool": "agents.list", "arguments": {}}])

    def listed():
        task = create(client, "tasks", office_id=office["id"], agent_id=parent["id"],
                      procedure_id=procedure["id"], request="Diagnóstico")
        done = wait_task(client, task["id"])
        assert done["status"] == "completed", done
        return {person["id"]: person["delegatable"] for person in json.loads(done["result"])["agents"]}

    before = listed()
    assert sum(before.values()) == 2
    # Adding the opposite arrow before replacing the reverse must remain forbidden.
    assert client.post("/api/relations", json={"source_id": parent["id"], "target_id": children[0]["id"]}).status_code == 422
    for relation, child in zip(relations[:3], children[:3]):
        assert client.patch(f"/api/relations/{relation['id']}", json={"source_id": parent["id"],
                           "target_id": child["id"]}).status_code == 200
    after = listed()
    assert all(after[child["id"]] for child in children)
    assert not after[parent["id"]]
    assert client.patch(f"/api/agents/{children[0]['id']}", json={"status": "disabled"}).status_code == 200
    assert not listed()[children[0]["id"]]
    other = create(client, "offices", name="Otra oficina")
    foreign = create(client, "agents", office_id=other["id"], name="Externo")
    assert client.post("/api/relations", json={"source_id": parent["id"], "target_id": foreign["id"]}).status_code == 422
    assert foreign["id"] not in listed()
