import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jsonschema.exceptions import SchemaError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.agents.engine import worker
from app.api import router, ws_router
from app.core.audit import redact
from app.core.config import DATA_DIR, DATABASE_URL, OLLAMA_URL, TOKEN
from app.core.db import SessionLocal, engine
from app.core.runtime_log import close as close_log
from app.core.runtime_log import configure as configure_log
from app.core.runtime_log import logger
from app.core.storage import prepare_sqlite, synced_folder
from app.demo import router as demo_router
from app.models import Base, Provider
from app.tools.builtins import register_builtins


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_log(DATA_DIR)
    started = False
    try:
        logger.info('Iniciando Oficina IA. Preparando base de datos y herramientas.')
        if not TOKEN:
            raise RuntimeError("OFFICE_SESSION_TOKEN requerido. Utilice scripts/launch.py")
        if DATABASE_URL.startswith("sqlite"):
            prepare_sqlite(Path(engine.url.database), DATA_DIR)
            engine.dispose()
            logger.info('Base de datos: %s', engine.url.database)
            if synced_folder(Path(engine.url.database).parent):
                logger.warning('La base SQLite está en una carpeta sincronizada (OneDrive/Dropbox); '
                               'esto puede dañarla. Quite OFFICE_DATABASE_URL para usar la ubicación local.')
            Base.metadata.create_all(engine)
        with SessionLocal() as session:
            if not session.scalar(select(Provider).where(Provider.kind == "ollama")):
                session.add(Provider(name="Ollama local", kind="ollama", url=OLLAMA_URL))
                session.commit()
            register_builtins(session)
            from app.execution.service import recover_jobs
            recover_jobs(session)
        await worker.start()
        started = True
        logger.info('Sistema listo. Esperando tareas; las consultas periódicas no se imprimen.')
        yield
    except Exception as exc:
        logger.error('Falló el ciclo del sistema: %s: %s', type(exc).__name__, redact(str(exc)))
        raise
    finally:
        if started:
            logger.info('Cerrando motor de tareas.')
            await worker.stop()
        logger.info('Oficina IA detenida.')
        close_log()


app = FastAPI(title="Oficina IA Local", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:38080",
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    ],
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(demo_router)
app.include_router(router)
app.include_router(ws_router)


@app.middleware('http')
async def diagnostic_requests(request: Request, call_next):
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error('HTTP %s %s | %s: %s', request.method, redact(request.url.path),
                     type(exc).__name__, redact(str(exc)))
        raise
    if response.status_code >= 400 or request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        route = request.scope.get('route')
        path = getattr(route, 'path', request.url.path)
        level = logger.error if response.status_code >= 500 else logger.warning if response.status_code >= 400 else logger.info
        level('HTTP %s %s -> %s | %s ms', request.method, redact(path), response.status_code,
              int((time.monotonic() - start) * 1000))
    return response


@app.exception_handler(ValueError)
async def value_error(request: Request, exc: ValueError):
    # ValidationError can include raw invalid inputs; return only messages.
    detail = "; ".join(e["msg"] for e in exc.errors()) if isinstance(exc, ValidationError) else redact(str(exc))
    logger.warning('Operación rechazada: %s', detail)
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(PermissionError)
async def permission_error(request: Request, exc: PermissionError):
    logger.warning('Acceso rechazado: %s', redact(str(exc)))
    return JSONResponse(status_code=403, content={"detail": redact(str(exc))})


@app.exception_handler(SchemaError)
async def schema_error(request: Request, exc: SchemaError):
    return JSONResponse(status_code=422, content={"detail": "JSON Schema de herramienta inválido"})


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={
            "detail": "Nombre duplicado o elemento relacionado con historial. Conserve el historial y desactive el elemento"
        },
    )


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500, content={"detail": "Falló la operación local. Revise configuración, servicios y permisos"}
    )
