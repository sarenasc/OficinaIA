import asyncio
import shutil
import subprocess

import httpx
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import OLLAMA_URL
from app.core.db import engine, get_session
from app.http.common import router
from app.security.windows_runtime import windows_runtime


@router.get("/ollama/status")
async def ollama_status(session: Session = Depends(get_session)):
    from sqlalchemy import select

    from app.ai.providers import validate_provider
    from app.models import Agent, Provider

    configured = list(session.scalars(select(Provider).where(Provider.kind == "ollama")))
    agents = list(session.scalars(select(Agent)))
    results = []
    async with httpx.AsyncClient(timeout=3, trust_env=False, follow_redirects=False) as client:
        for provider in configured:
            models = []
            reachable = False
            try:
                validate_provider(provider)
                response = await client.get(provider.url.rstrip("/") + "/api/tags")
                response.raise_for_status()
                models = [item["name"] for item in response.json().get("models", [])]
                reachable = True
            except (httpx.HTTPError, ValueError, KeyError, TypeError):
                pass
            assigned = [agent for agent in agents if agent.provider_id == provider.id]

            def model_allowed(agent):
                try:
                    validate_provider(provider, agent.model or provider.default_model)
                    return True
                except ValueError:
                    return False

            ready = [
                agent.id
                for agent in assigned
                if reachable
                and provider.active
                and agent.status != "disabled"
                and (agent.model or provider.default_model) in models
                and model_allowed(agent)
            ]
            results.append(
                {
                    "id": provider.id,
                    "name": provider.name,
                    "reachable": reachable,
                    "models": models,
                    "assigned_agents": len(assigned),
                    "ready_agents": ready,
                }
            )
    return {
        "providers": results,
        "reachable": any(item["reachable"] for item in results),
        "ready_agents": sum(len(item["ready_agents"]) for item in results),
    }


@router.post("/artifacts/{id}/open")
def open_file(id: str, session: Session = Depends(get_session)):
    return windows_runtime.open(session, id)


@router.post("/artifacts/{id}/open-folder")
def open_folder(id: str, session: Session = Depends(get_session)):
    return windows_runtime.open(session, id, folder=True)


@router.post("/services/diagnostics")
async def diagnostics():
    def check_database():
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return engine.dialect.name

    def check_docker():
        if not shutil.which("docker"):
            return "No instalado/en PATH"
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, timeout=10, check=False
        )
        return result.stdout.decode(errors="replace").strip() if not result.returncode else "Docker Desktop no iniciado"

    async def check_ollama():
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            result = await client.get(OLLAMA_URL.rstrip("/") + "/api/tags")
            result.raise_for_status()
            return {"models": [m["name"] for m in result.json().get("models", [])]}

    async def check_redis():
        import os

        from redis.asyncio import Redis

        url = os.getenv("OFFICE_REDIS_URL")
        if not url:
            return "No configurado (cola local en memoria)"
        client = Redis.from_url(url, socket_connect_timeout=5, socket_timeout=5)
        try:
            return "Conectado" if await client.ping() else "Sin respuesta"
        finally:
            await client.aclose()

    results = await asyncio.gather(
        asyncio.to_thread(check_database),
        asyncio.to_thread(check_docker),
        check_ollama(),
        check_redis(),
        return_exceptions=True,
    )
    return {
        key: "No disponible; revise servicio/configuración" if isinstance(value, Exception) else value
        for key, value in zip(["database", "docker", "ollama", "redis"], results)
    }
