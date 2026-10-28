"""Typed Windows operations; never accepts command text or arbitrary executable paths."""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.audit import audit
from app.models import Agent, Artifact, Resource
from app.security.permissions import resource_path


class WindowsRuntime:
    SAFE_EXTENSIONS = {".xlsx", ".csv", ".txt", ".pdf", ".png", ".jpg", ".jpeg", ".json"}

    def artifact_path(self, session: Session, artifact_id: str):
        artifact = session.get(Artifact, artifact_id)
        if not artifact:
            raise ValueError("Artefacto no encontrado")
        agent = session.get(Agent, artifact.agent_id)
        resource = session.get(Resource, artifact.resource_id)
        relative = str(Path(artifact.path).relative_to(Path(resource.path).resolve()))
        path = resource_path(session, agent, resource.id, relative, "read")
        if not path.is_file():
            raise ValueError("El archivo ya no existe")
        return artifact, path

    def open(self, session: Session, artifact_id: str, folder: bool = False):
        if sys.platform != "win32":
            raise ValueError("Esta acción requiere el backend nativo Windows")
        artifact, path = self.artifact_path(session, artifact_id)
        if folder:
            # Explorer receives one verified directory argument, never a shell command.
            command = [str(Path(os.environ.get("WINDIR", "C:/Windows")) / "explorer.exe"), str(path.parent)]
            subprocess.Popen(command, creationflags=0x08000000)
        else:
            if path.suffix.lower() not in self.SAFE_EXTENSIONS:
                raise PermissionError("No se permite abrir programas ni scripts como artefactos")
            os.startfile(str(path), "open")
        audit(
            session,
            "windows.open_folder" if folder else "windows.open_file",
            {"path": str(path)},
            artifact.task_id,
            artifact.agent_id,
        )
        return {"opened": True}


windows_runtime = WindowsRuntime()
