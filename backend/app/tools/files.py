"""Validated file publication shared by download, text and PDF tools."""
import hashlib
import os
import tempfile
from pathlib import Path

from app.models import Artifact
from app.security.permissions import require_approval, resource_path


def publish_bytes(session, task, agent, resource_id, relative, content: bytes, tool: str):
    path = resource_path(session, agent, resource_id, relative, "create")
    previous = None
    if path.exists():
        resource_path(session, agent, resource_id, relative, "modify")
        previous = hashlib.sha256(path.read_bytes()).hexdigest()
        if agent.mode == "safe":
            require_approval(session, task, agent, "overwrite", {
                "tool": tool, "resource_id": resource_id, "path": relative,
                "previous_sha256": previous, "sha256": hashlib.sha256(content).hexdigest(),
            }, f"Sobrescribir {path.name} con contenido verificado")
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(content).hexdigest()
    fd, temporary = tempfile.mkstemp(prefix=".office-publish-", dir=path.parent)
    temp = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(content)
        if hashlib.sha256(temp.read_bytes()).hexdigest() != digest:
            raise ValueError("No coincide la integridad del archivo preparado")
        resource_path(session, agent, resource_id, relative, "modify" if previous else "create")
        if previous:
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != previous:
                raise ValueError("El archivo cambió; vuelva a revisar y aprobar")
            os.replace(temp, path)
        else:
            with path.open("xb") as output:
                output.write(content)
    finally:
        temp.unlink(missing_ok=True)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("El archivo publicado no coincide con la integridad esperada")
    session.add(Artifact(task_id=task.id, agent_id=agent.id, resource_id=resource_id, path=str(path), name=path.name))
    return {"path": str(path), "bytes": len(content), "sha256": digest, "verified": True}
