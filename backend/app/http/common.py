import hmac
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app import schemas as s
from app.ai.providers import validate_provider
from app.core.audit import SENSITIVE
from app.core.config import TOKEN


def authorize(request: Request):
    if not TOKEN or not hmac.compare_digest(request.headers.get("Authorization", ""), "Bearer " + TOKEN):
        raise HTTPException(401, "Token local requerido; inicie la aplicación con el lanzador")
    origin = request.headers.get("origin")
    if origin and origin not in {
        "http://127.0.0.1:38080",
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    }:
        raise HTTPException(403, "Origen no permitido")


router = APIRouter(prefix="/api", dependencies=[Depends(authorize)])
ws_router = APIRouter()
ENTITIES = {
    "offices": (m.Office, s.OfficeInput),
    "areas": (m.Area, s.AreaInput),
    "agents": (m.Agent, s.AgentInput),
    "providers": (m.Provider, s.ProviderInput),
    "tools": (m.Tool, s.ToolInput),
    "resources": (m.Resource, s.ResourceInput),
    "connections": (m.Connection, s.ConnectionInput),
    "skills": (m.Skill, s.SkillInput),
    "procedures": (m.Procedure, s.ProcedureInput),
    "relations": (m.AgentRelation, s.RelationInput),
}
READONLY = {
    "tasks": m.Task,
    "executions": m.Execution,
    "messages": m.Message,
    "audit": m.AuditEvent,
    "artifacts": m.Artifact,
    "approvals": m.Approval,
    "memories": m.Memory,
}


def serialize(entity) -> dict:
    result = {}
    for column in entity.__table__.columns:
        value = getattr(entity, column.name)
        if column.name == "credential_ref":
            result["has_credential"] = bool(value)
        else:
            result[column.name] = value.isoformat() if isinstance(value, datetime) else value
    # Task internal state contains model messages; only execution/event endpoints expose redacted content.
    if isinstance(entity, m.Task):
        result.pop("context", None)
    return result


def entity_type(entity: str, writable=False):
    if entity in ENTITIES:
        return ENTITIES[entity][0]
    if not writable and entity in READONLY:
        return READONLY[entity]
    raise HTTPException(404, "Módulo no encontrado")


def get_or_404(session: Session, cls, id: str):
    obj = session.get(cls, id)
    if not obj:
        raise HTTPException(404, "Elemento no encontrado")
    return obj


def reject_secrets(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if SENSITIVE.search(key):
                raise ValueError("Secretos solo se configuran en el almacén seguro")
            reject_secrets(item)
    elif isinstance(value, list):
        for item in value:
            reject_secrets(item)


def validate_domain(session: Session, entity: str, data: dict, current=None):
    if entity in {"providers", "connections", "tools"}:
        reject_secrets(data.get("config", {}))
    if "office_id" in data:
        get_or_404(session, m.Office, data["office_id"])
    if entity == "offices" and data.get("coordinator_id"):
        agent = get_or_404(session, m.Agent, data["coordinator_id"])
        if not current or agent.office_id != current.id:
            raise ValueError("Coordinador debe pertenecer a esta oficina")
    if entity == "agents":
        if current and current.office_id != data["office_id"]:
            raise ValueError("No se permite mover agentes entre oficinas con historial")
        if data.get("area_id") and get_or_404(session, m.Area, data["area_id"]).office_id != data["office_id"]:
            raise ValueError("Área pertenece a otra oficina")
        if data.get("provider_id"):
            get_or_404(session, m.Provider, data["provider_id"])
        if data["status"] in {"working", "waiting"}:
            if not current or current.status != data["status"]:
                raise ValueError("Estado de ejecución reservado al motor")
        if set(data["position"]) != {"x", "y"}:
            raise ValueError("Posición debe contener x e y")
        for item in data["fallbacks"]:
            if set(item) != {"provider_id", "model"}:
                raise ValueError("Fallback requiere provider_id y model")
            get_or_404(session, m.Provider, item["provider_id"])
    if entity == "providers":
        validate_provider(m.Provider(**data), data.get("default_model", ""))
    if entity == "resources" and data["kind"] in {"directory", "network_directory", "file"}:
        path = Path(data["path"])
        if not path.is_absolute() or not path.exists():
            raise ValueError("Seleccione un recurso existente con ruta absoluta")
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("No se aceptan enlaces/junctions")
        if data["kind"] == "file" and not path.is_file():
            raise ValueError("El recurso debe ser archivo")
        if data["kind"] != "file" and not path.is_dir():
            raise ValueError("El recurso debe ser carpeta")
    if entity == "resources" and data["kind"] == "url":
        from app.tools.network import origin
        origin(data["path"])
    if entity == "connections":
        from app.tools.connections import validate_connection_config

        validate_connection_config(data["kind"], data["config"], data["active"])
    if entity == "skills":
        for tid in data["required_tools"]:
            get_or_404(session, m.Tool, tid)
    if entity == "tools":
        from jsonschema import Draft202012Validator

        Draft202012Validator.check_schema(data["parameters"])
        if current and current.builtin:
            if any(
                data[k] != getattr(current, k) for k in ("name", "kind", "parameters", "config", "required_permissions")
            ):
                raise ValueError("No se permite cambiar el contrato de una herramienta integrada")
        elif data["kind"] not in {"custom.sql", "custom.python"}:
            raise ValueError("Herramientas personalizadas admitidas: SQL de lectura o Python Docker")
        if data["kind"] == "custom.python" and "python.execute" not in data["required_permissions"]:
            data["required_permissions"].append("python.execute")
        if data["kind"] == "custom.sql":
            if set(data["config"]) != {"connection_id", "query"} or not isinstance(data["config"].get("query"), str):
                raise ValueError("SQL personalizado requiere connection_id y query")
            get_or_404(session, m.Connection, data["config"]["connection_id"])
        if data["kind"] == "custom.python":
            config = data["config"]
            if not isinstance(config.get("code"), str) or not isinstance(config.get("resources", []), list):
                raise ValueError("Python personalizado requiere code y resources como lista de UUIDs")
    if entity == "procedures":
        for step in data["steps"]:
            if set(step) != {"agent_id", "tool", "arguments"}:
                raise ValueError("Paso requiere agent_id, tool y arguments")
            if get_or_404(session, m.Agent, step["agent_id"]).office_id != data["office_id"]:
                raise ValueError("Todos los agentes deben pertenecer a la oficina")
    if entity == "relations":
        source, target = (
            get_or_404(session, m.Agent, data["source_id"]),
            get_or_404(session, m.Agent, data["target_id"]),
        )
        if source.office_id != target.office_id or source.id == target.id:
            raise ValueError("Relación inválida")
        adjacency = {}
        for relation in session.scalars(select(m.AgentRelation)):
            if not current or relation.id != current.id:
                adjacency.setdefault(relation.source_id, []).append(relation.target_id)
        adjacency.setdefault(source.id, []).append(target.id)

        def visit(node, path):
            if node in path:
                raise ValueError("La relación produce un ciclo")
            for child in adjacency.get(node, []):
                visit(child, path | {node})

        visit(source.id, set())
