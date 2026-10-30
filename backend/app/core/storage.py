"""SQLite location and startup integrity.

OneDrive/Dropbox sync office.db, -wal and -shm as independent files. With two
computers (or one PC while the sync client replaces a file) this corrupts the
database ("database disk image is malformed"). The live database therefore lives
in a local folder; DATA_DIR (logs, backups, runtime) can stay where it is.
"""

import hashlib
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger("oficina")

SYNC_MARKERS = ("onedrive", "dropbox", "google drive", "googledrive", "icloud", "box sync", "mega")
AUTO_BACKUPS = 10


def synced_folder(path: Path) -> bool:
    path = Path(path).resolve()
    roots = [os.environ.get(name) for name in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer")]
    for root in filter(None, roots):
        try:
            path.relative_to(Path(root).resolve())
            return True
        except ValueError:
            pass
    return any(part.lower().startswith(SYNC_MARKERS) for part in path.parts)


def local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    return Path(base) / "OficinaIA"


def database_path(data_dir: Path) -> Path:
    """office.db next to the data, unless that folder is synchronized."""
    data_dir = Path(data_dir).resolve()
    if not synced_folder(data_dir):
        return data_dir / "office.db"
    # One local database per installation folder, so two checkouts never share it.
    key = hashlib.sha256(str(data_dir).lower().encode()).hexdigest()[:12]
    folder = local_root() / "bases" / key
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "origen.txt").write_text(str(data_dir) + "\n", encoding="utf-8")
    return folder / "office.db"


def healthy(path: Path) -> bool:
    try:
        db = sqlite3.connect(path)
        try:
            return db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        finally:
            db.close()
    except sqlite3.DatabaseError:
        return False


def copy_database(source: Path, destination: Path):
    src, dst = sqlite3.connect(source), sqlite3.connect(destination)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()


def _sidecars(path: Path):
    return [path, path.with_name(path.name + "-wal"), path.with_name(path.name + "-shm")]


def _quarantine(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = path.with_name(f"{path.name}.danada-{stamp}")
    for file in _sidecars(path):
        if file.exists():
            shutil.move(file, target.with_name(target.name + file.name[len(path.name):]))
    return target


def _latest_healthy_backup(data_dir: Path):
    folder = Path(data_dir) / "backups"
    candidates = [*folder.glob("*.db"), *(folder / "auto").glob("*.db")] if folder.exists() else []
    for candidate in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
        if healthy(candidate):
            return candidate
    return None


def auto_backup(path: Path, data_dir: Path):
    folder = Path(data_dir) / "backups" / "auto"
    folder.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8] + ".db"
    copy_database(path, folder / name)
    for old in sorted(folder.glob("*.db"), reverse=True)[AUTO_BACKUPS:]:
        old.unlink(missing_ok=True)


def prepare_sqlite(path: Path, data_dir: Path):
    """Run before the first connection: migrate, verify, restore and back up."""
    path, data_dir = Path(path), Path(data_dir)
    legacy = data_dir / "office.db"
    if not path.exists() and legacy != path and legacy.exists():
        source = legacy if healthy(legacy) else _latest_healthy_backup(data_dir)
        if source:
            copy_database(source, path)
            logger.warning("Base de datos movida fuera de la carpeta sincronizada: %s -> %s. "
                           "La copia anterior se conserva sin cambios.", source, path)
        else:
            logger.error("La base %s está dañada y no hay backups sanos; se crea una base nueva en %s. "
                         "El archivo dañado se conserva para recuperación manual.", legacy, path)
    elif path.exists() and not healthy(path):
        damaged = _quarantine(path)
        backup = _latest_healthy_backup(data_dir)
        if not backup:
            raise RuntimeError(
                f"La base de datos está dañada (database disk image is malformed). Se apartó como {damaged}. "
                f"No hay backups sanos en {data_dir / 'backups'}. Reinicie para comenzar con una base nueva "
                "o recupere el archivo con 'sqlite3 archivo .recover'."
            )
        copy_database(backup, path)
        logger.error("Base de datos dañada apartada como %s. Restaurado el backup %s; "
                     "los cambios posteriores a ese backup no están.", damaged, backup)
    if path.exists():
        auto_backup(path, data_dir)
