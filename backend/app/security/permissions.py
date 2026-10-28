import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, AgentResource, Approval, Resource, Task


class ApprovalRequired(Exception):
    def __init__(self, reason: str, key: str, payload: dict, agent_id: str):
        self.reason, self.key, self.payload, self.agent_id = reason, key, payload, agent_id
        super().__init__(reason)


def approval_key(kind: str, payload: dict) -> str:
    return kind + ":" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def require_approval(session: Session, task: Task, agent: Agent, kind: str, payload: dict, reason: str) -> None:
    key = approval_key(kind, {"agent": agent.id, **payload})
    approved = session.scalar(
        select(Approval).where(Approval.task_id == task.id, Approval.key == key, Approval.status == "approved")
    )
    if not approved:
        raise ApprovalRequired(reason, key, payload, agent.id)


def resource_path(session: Session, agent: Agent, resource_id: str, relative: str, permission: str) -> Path:
    assignment = session.get(AgentResource, (agent.id, resource_id))
    resource = session.get(Resource, resource_id)
    if not resource or not resource.active or not assignment or permission not in assignment.permissions:
        raise PermissionError(f"Recurso no asignado o permiso '{permission}' ausente")
    if resource.kind not in {"directory", "network_directory", "file"}:
        raise PermissionError("Este recurso no representa un archivo o carpeta")
    rel = Path(relative)
    if rel.is_absolute() or rel.drive or ".." in rel.parts or ":" in relative:
        raise PermissionError("Utilice una ruta relativa sin escapes ni flujos alternativos")
    original_root = Path(resource.path)
    unresolved_target = original_root if resource.kind == "file" else original_root / rel
    for part in [unresolved_target, *unresolved_target.parents]:
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise PermissionError("Enlaces y junctions no están permitidos")
    root = original_root.resolve(strict=True)
    if resource.kind == "file":
        if relative not in {"", "."}:
            raise PermissionError("Recurso de archivo no permite rutas hijas")
        return root
    target = (root / rel).resolve()
    if not target.is_relative_to(root):
        raise PermissionError("La ruta resuelta escapa del recurso autorizado")
    # Deny junctions/symlinks at every component, including resource root.
    for part in [root, *target.parents, target]:
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise PermissionError("Enlaces y junctions no están permitidos")
    return target
