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


def test_synced_folder_detection(tmp_path, monkeypatch):
    monkeypatch.setenv("OneDrive", str(tmp_path / "cloud"))
    assert storage.synced_folder(tmp_path / "cloud" / "Oficina IA" / "data")
    assert storage.synced_folder(tmp_path / "OneDrive - Almahue" / "data")
    assert not storage.synced_folder(tmp_path / "local" / "data")


def test_database_moves_out_of_onedrive(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    data = tmp_path / "OneDrive" / "Oficina IA" / "data"
    data.mkdir(parents=True)
    path = storage.database_path(data)
    assert path.parent.parent.parent == tmp_path / "appdata" / "OficinaIA"
    assert storage.database_path(tmp_path / "local") == tmp_path / "local" / "office.db"
    make_db(data / "office.db", "antes")
    storage.prepare_sqlite(path, data)
    assert value(path) == "antes"
    assert (data / "office.db").exists()
    assert len(list((data / "backups" / "auto").glob("*.db"))) == 1


def test_corrupt_database_restores_latest_healthy_backup(tmp_path):
    path = make_db(tmp_path / "office.db", "original")
    storage.prepare_sqlite(path, tmp_path)
    corrupt(path)
    assert not storage.healthy(path)
    storage.prepare_sqlite(path, tmp_path)
    assert value(path) == "original"
    assert list(tmp_path.glob("office.db.danada-*"))


def test_corrupt_database_without_backup_is_kept_aside(tmp_path):
    path = make_db(tmp_path / "office.db")
    corrupt(path)
    with pytest.raises(RuntimeError, match="dañada"):
        storage.prepare_sqlite(path, tmp_path)
    assert not path.exists() and list(tmp_path.glob("office.db.danada-*"))
    storage.prepare_sqlite(path, tmp_path)  # next start: new empty database


def test_auto_backups_are_bounded(tmp_path):
    path = make_db(tmp_path / "office.db")
    for _ in range(storage.AUTO_BACKUPS + 3):
        storage.auto_backup(path, tmp_path)
    assert len(list((tmp_path / "backups" / "auto").glob("*.db"))) == storage.AUTO_BACKUPS
