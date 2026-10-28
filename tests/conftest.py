import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient

_temp = TemporaryDirectory(prefix="office-tests-")
os.environ["OFFICE_DATA_DIR"] = _temp.name
os.environ["OFFICE_DATABASE_URL"] = f"sqlite:///{Path(_temp.name) / 'test.db'}"
os.environ["OFFICE_SESSION_TOKEN"] = "test-session-only"

from app.core.db import engine
from app.main import app
from app.models import Base


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app, headers={"Authorization": "Bearer test-session-only"}) as client:
        yield client
    engine.dispose()


def create(client, entity, **kwargs):
    response = client.post("/api/" + entity, json=kwargs)
    assert response.status_code == 200, response.text
    return response.json()


def wait_task(client, id):
    import time

    for _ in range(100):
        task = client.get("/api/tasks/" + id).json()
        if task["status"] in {"completed", "error", "cancelled", "waiting_approval"}:
            return task
        time.sleep(0.03)
    raise AssertionError("Task did not finish")
