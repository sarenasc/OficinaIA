"""SQLite location, startup integrity and automatic backups.

OneDrive/Dropbox sync office.db, -wal and -shm as independent files. With two
computers (or one PC while the sync client replaces a file) this corrupts the
database ("database disk image is malformed"). The live database therefore lives
in a local folder; DATA_DIR (logs, backups, runtime) can stay where it is.

Every start verifies the database and saves a backup. A damaged database is moved
aside (never deleted) and replaced by the newest healthy backup, or by an empty
database when there is none, so the system always starts.
"""

import hashlib
import logging
import os
import platform
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger("oficina")

SYNC_MARKERS = ("onedrive", "dropbox", "google drive", "googledrive", "icloud", "box sync", "mega")
AUTO_BACKUPS = 10  # most recent starts
DAILY_BACKUPS = 14  # plus the newest backup of each of these days


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
    """Consistent copy (includes WAL content); written under a temporary name first."""
    partial = destination.with_name(destination.name + ".parcial")
    partial.unlink(missing_ok=True)
    src, dst = sqlite3.connect(source), sqlite3.connect(partial)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    os.replace(partial, destination)


def _sidecars(path: Path):
    return [path, path.with_name(path.name + "-wal"), path.with_name(path.name + "-shm")]


def set_aside(path: Path, reason: str = "danada") -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = path.with_name(f"{path.name}.{reason}-{stamp}")
    for file in _sidecars(path):
        if file.exists():
            shutil.move(file, target.with_name(target.name + file.name[len(path.name):]))
    return target


def auto_folder(data_dir: Path) -> Path:
    # Per computer: data/backups is often synchronized and each PC has its own database.
    computer = re.sub(r"[^A-Za-z0-9_-]", "_", os.environ.get("COMPUTERNAME") or platform.node() or "equipo")
    return Path(data_dir) / "backups" / "auto" / computer


def latest_healthy_backup(data_dir: Path):
    """Own automatic backups first (newest first), then manual backups."""
    groups = [sorted(auto_folder(data_dir).glob("*.db"), reverse=True),
              sorted((Path(data_dir) / "backups").glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)]
    for candidate in (path for group in groups for path in group):
        if healthy(candidate):
            return candidate
        logger.warning("Backup descartado por estar dañado: %s", candidate)
    return None


def auto_backup(path: Path, data_dir: Path) -> Path:
    folder = auto_folder(data_dir)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8] + ".db")
    copy_database(path, target)
    backups = sorted(folder.glob("*.db"), reverse=True)
    keep = set(backups[:AUTO_BACKUPS])
    days = {}
    for backup in backups:
        days.setdefault(backup.name[:8], backup)
    keep.update(list(days.values())[:DAILY_BACKUPS])
    for old in backups:
        if old not in keep:
            old.unlink(missing_ok=True)
    return target


def restore(path: Path, data_dir: Path, reason: str = "danada"):
    """Move the current database aside and put the newest healthy backup in place."""
    damaged = set_aside(path, reason) if path.exists() else None
    backup = latest_healthy_backup(data_dir)
    if backup:
        copy_database(backup, path)
        logger.error("Base de datos dañada%s. Restaurado el último backup sano %s; "
                     "los cambios posteriores a ese backup no están.",
                     f" apartada como {damaged}" if damaged else "", backup)
    else:
        logger.error("Base de datos dañada%s y sin backups sanos: se inicia una base nueva vacía. "
                     "El archivo dañado se conserva para recuperación manual.",
                     f" apartada como {damaged}" if damaged else "")
    return backup


def reset(path: Path) -> Path | None:
    """Start from zero without deleting anything: the current database is kept aside."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Do not import the old synchronized office.db on the next start either.
    (path.parent / "migrada.txt").write_text("base nueva solicitada\n", encoding="utf-8")
    return set_aside(path, "reinicio") if path.exists() else None


def prepare_sqlite(path: Path, data_dir: Path):
    """Run before the first connection: migrate, verify and restore."""
    path, data_dir = Path(path), Path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    legacy = data_dir / "office.db"
    if not path.exists() and legacy != path and legacy.exists() and not (path.parent / "migrada.txt").exists():
        if healthy(legacy):
            copy_database(legacy, path)
            logger.warning("Base de datos movida fuera de la carpeta sincronizada: %s -> %s. "
                           "La copia anterior se conserva sin cambios.", legacy, path)
        else:
            logger.error("La base %s está dañada; se conserva sin cambios.", legacy)
            restore(path, data_dir)
        # Only once: later starts never bring back the old synchronized copy.
        (path.parent / "migrada.txt").write_text(str(legacy) + "\n", encoding="utf-8")
    elif path.exists() and not healthy(path):
        restore(path, data_dir)


def backup_after_start(path: Path, data_dir: Path):
    """Only a database that already opened and served the startup queries is a good backup."""
    try:
        target = auto_backup(Path(path), Path(data_dir))
        logger.info("Backup automático guardado: %s", target)
    except (OSError, sqlite3.Error) as exc:
        # A failed backup must not stop the office; the previous backups remain.
        logger.warning("No se pudo guardar el backup automático: %s: %s", type(exc).__name__, exc)


def is_corruption(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "malformed" in text or "not a database" in text or "disk i/o error" in text
