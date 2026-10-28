from conftest import create


def test_multiple_sql_drafts_are_saved_without_connecting(client, monkeypatch):
    from app.tools import connections

    def no_network(*args, **kwargs):
        raise AssertionError("Saving or testing an inactive draft must not create an engine")

    monkeypatch.setattr(connections, "create_engine", no_network)
    first = create(client, "connections", name="SQL Ventas pendiente", kind="sqlserver", active=False, config={})
    second = create(
        client,
        "connections",
        name="SQL Inventario pendiente",
        kind="sqlserver",
        active=False,
        config={"auth": "windows", "driver": "ODBC Driver 18 for SQL Server"},
    )
    assert first["id"] != second["id"]
    assert len(client.get("/api/connections").json()) == 2
    response = client.post(f"/api/connections/{first['id']}/test")
    assert response.status_code == 422
    assert "inactiva" in response.json()["detail"]


def test_sql_activation_requires_configuration_and_preserves_other_drafts(client):
    first = create(client, "connections", name="SQL A", active=False, config={})
    second = create(client, "connections", name="SQL B", active=False, config={})
    endpoint = f"/api/connections/{first['id']}"
    assert client.patch(endpoint, json={"active": True}).status_code == 422
    assert client.patch(endpoint, json={"active": True, "config": {"host": "server"}}).status_code == 422
    config = {"host": "server\\instance", "database": "Ventas", "auth": "password"}
    assert client.patch(endpoint, json={"active": True, "config": config}).status_code == 422
    config.update(username="reader", port=70000)
    assert client.patch(endpoint, json={"active": True, "config": config}).status_code == 422
    config["port"] = 1433
    activated = client.patch(endpoint, json={"active": True, "config": config})
    assert activated.status_code == 200
    assert activated.json()["config"]["database"] == "Ventas"
    assert client.get(f"/api/connections/{second['id']}").json()["active"] is False
    assert client.patch(endpoint, json={"config": {**config, "password": "never-store"}}).status_code == 422
