import sqlite3

import pytest
from app.core import storage


def make_db(path, value="ok"):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE t (v TEXT)")
        db.execute("INSERT INTO t VALUES (?)", (value,))
    return path


def corrupt(path):
    data = bytearray(path.read_bytes())
    data[100:4096] = b"\xff" * (4096 - 100)
    path.write_bytes(bytes(data))


def value(path):
    with sqlite3.connect(path) as db:
        return db.execute("SELECT v FROM t").fetchone()[0]


@pytest.fixture(autouse=True)
def computer(monkeypatch):
    monkeypatch.setenv("COMPUTERNAME", "PC-PRUEBA")


def test_synced_folder_detection(tmp_path, monkeypatch):
    monkeypatch.setenv("OneDrive", str(tmp_path / "cloud"))
    assert storage.synced_folder(tmp_path / "cloud" / "Oficina IA" / "data")
    assert storage.synced_folder(tmp_path / "OneDrive - Almahue" / "data")
    assert not storage.synced_folder(tmp_path / "local" / "data")


def test_database_moves_out_of_onedrive_once(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    data = tmp_path / "OneDrive" / "Oficina IA" / "data"
    data.mkdir(parents=True)
    path = storage.database_path(data)
    assert path.parent.parent.parent == tmp_path / "appdata" / "OficinaIA"
    assert storage.database_path(tmp_path / "local") == tmp_path / "local" / "office.db"
    make_db(data / "office.db", "antes")
    storage.prepare_sqlite(path, data)
    assert value(path) == "antes" and (data / "office.db").exists()
    path.unlink()
    storage.prepare_sqlite(path, data)  # the old synchronized copy is never imported again
    assert not path.exists()


def test_corrupt_database_restores_latest_healthy_backup(tmp_path):
    path = make_db(tmp_path / "office.db", "original")
    storage.backup_after_start(path, tmp_path)
    corrupt(path)
    assert not storage.healthy(path)
    storage.prepare_sqlite(path, tmp_path)
    assert value(path) == "original"
    assert list(tmp_path.glob("office.db.danada-*"))


def test_damaged_backups_are_skipped(tmp_path):
    path = make_db(tmp_path / "office.db", "sano")
    storage.backup_after_start(path, tmp_path)
    newest = storage.auto_backup(path, tmp_path)
    corrupt(newest)
    corrupt(path)
    storage.prepare_sqlite(path, tmp_path)
    assert value(path) == "sano"


def test_corrupt_database_without_backup_starts_empty(tmp_path):
    path = make_db(tmp_path / "office.db")
    corrupt(path)
    storage.prepare_sqlite(path, tmp_path)
    assert not path.exists() and list(tmp_path.glob("office.db.danada-*"))


def test_reset_keeps_previous_database(tmp_path):
    path = make_db(tmp_path / "office.db", "vieja")
    kept = storage.reset(path)
    assert not path.exists() and value(kept) == "vieja"


def test_auto_backups_are_bounded_per_computer(tmp_path):
    path = make_db(tmp_path / "office.db")
    for _ in range(storage.AUTO_BACKUPS + 3):
        storage.auto_backup(path, tmp_path)
    folder = tmp_path / "backups" / "auto" / "PC-PRUEBA"
    assert len(list(folder.glob("*.db"))) == storage.AUTO_BACKUPS
    assert not list(folder.glob("*.parcial"))


def test_startup_restores_backup_when_first_queries_fail(monkeypatch):
    from app import main
    from app.core.config import DATA_DIR
    from app.core.db import engine
    from fastapi.testclient import TestClient

    with TestClient(main.app):
        pass
    assert list(storage.auto_folder(DATA_DIR).glob("*.db"))  # every successful start saves a backup
    calls = []
    original = main.initialize_database

    def flaky():
        if not calls:
            calls.append(1)
            raise main.DatabaseError("SELECT", {}, sqlite3.DatabaseError("database disk image is malformed"))
        original()

    monkeypatch.setattr(main, "initialize_database", flaky)
    with TestClient(main.app, headers={"Authorization": "Bearer test-session-only"}) as client:
        assert client.get("/api/health").status_code == 200
    assert calls and storage.healthy(engine.url.database)
    engine.dispose()
