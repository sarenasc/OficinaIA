"""Local backups; no export of Windows Credential Manager secrets."""

import os
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.config import DATA_DIR
from app.core.db import engine, get_session
from app.http.common import router


def folder():
    root = DATA_DIR / "backups"
    root.mkdir(exist_ok=True)
    return root


@router.get("/backups")
def list_backups():
    return [
        {"name": path.name, "bytes": path.stat().st_size}
        for path in sorted(folder().iterdir(), reverse=True)
        if path.is_file() and path.suffix in {".db", ".dump"}
    ]


@router.post("/backups")
def create_backup(session: Session = Depends(get_session)):
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]
    if engine.dialect.name == "sqlite":
        path = folder() / (name + ".db")
        with sqlite3.connect(engine.url.database) as source, sqlite3.connect(path) as destination:
            source.backup(destination)
    elif engine.dialect.name == "postgresql":
        if not shutil.which("pg_dump"):
            raise ValueError("Instale las herramientas cliente PostgreSQL (pg_dump) para crear backups")
        path = folder() / (name + ".dump")
        url = engine.url
        env = dict(os.environ, PGPASSWORD=url.password or "")
        command = [
            "pg_dump",
            "--format=custom",
            "--no-password",
            "--host",
            url.host or "127.0.0.1",
            "--port",
            str(url.port or 5432),
            "--username",
            url.username or "office",
            "--file",
            str(path),
            url.database,
        ]
        result = subprocess.run(command, env=env, capture_output=True, timeout=120, check=False)
        if result.returncode:
            path.unlink(missing_ok=True)
            raise ValueError("pg_dump falló; revise servicio, permisos y versión cliente")
    else:
        raise ValueError("Backup no implementado para este motor de persistencia")
    audit(session, "backup.created", {"name": path.name, "bytes": path.stat().st_size})
    return {"name": path.name, "bytes": path.stat().st_size}


@router.get("/backups/{name}/download")
def backup_download(name: str):
    import re

    if not re.fullmatch(r"\d{8}T\d{6}Z-[a-f0-9]{8}\.(db|dump)", name):
        raise ValueError("Nombre de backup inválido")
    path = folder() / name
    if not path.is_file() or path.is_symlink():
        raise ValueError("Backup no encontrado")
    return FileResponse(path, filename=name)
