"""Read-only SQL plus explicit credential references."""

import time

import sqlglot
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session
from sqlglot import exp

from app.models import Agent, AgentConnection, Connection
from app.security.permissions import require_approval
from app.security.secrets import secrets


def validate_connection_config(kind: str, config: dict, active: bool):
    if not active:
        return
    if kind in {"http_api", "web_search"}:
        from app.tools.network import origin
        if kind == "http_api":
            origin(config.get("base_url", ""))
            if config.get("auth", "bearer") not in {"bearer", "header", "none"}:
                raise ValueError("Autenticación API admitida: bearer/header/none")
            header = config.get("auth_header", "X-API-Key")
            import re
            if not isinstance(header, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,80}", header) or header.lower() in {"host", "content-length", "connection", "cookie", "transfer-encoding"}:
                raise ValueError("Nombre de cabecera de autenticación inválido")
            if "allow_private" in config and not isinstance(config["allow_private"], bool):
                raise ValueError("allow_private debe ser booleano")
        elif config.get("provider", "brave") != "brave":
            raise ValueError("Proveedor de búsqueda implementado: brave")
        rate = config.get("requests_per_minute", 30)
        if isinstance(rate, bool) or not isinstance(rate, int) or not 1 <= rate <= 60:
            raise ValueError("requests_per_minute debe ser entero entre 1 y 60")
        return
    if config.get("writable_enabled"):
        if not isinstance(config.get("write_tables"), list) or not config["write_tables"] or not all(isinstance(t, str) and t for t in config["write_tables"]):
            raise ValueError("Declare write_tables como lista de tablas permitidas")
        limit = config.get("max_write_rows", 1000)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10000:
            raise ValueError("max_write_rows debe ser entero entre 1 y 10000")
        if not set(config.get("write_operations", ["insert", "update", "delete"])).issubset({"insert", "update", "delete"}):
            raise ValueError("write_operations solo admite insert/update/delete")
    if kind != "sqlserver":
        return
    if not isinstance(config.get("host"), str) or not config["host"].strip():
        raise ValueError("Complete el servidor SQL antes de activar la conexión")
    if not isinstance(config.get("database"), str) or not config["database"].strip():
        raise ValueError("Complete la base de datos antes de activar la conexión")
    if config.get("auth", "windows") not in {"windows", "password"}:
        raise ValueError("Autenticación SQL inválida")
    if config.get("auth") == "password" and not str(config.get("username") or "").strip():
        raise ValueError("Complete el usuario SQL antes de activar la conexión")
    port = config.get("port")
    if port is not None and (isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535):
        raise ValueError("Puerto SQL inválido; use un entero entre 1 y 65535")


def connection_engine(connection: Connection, writable: bool = False):
    if not connection.active:
        raise ValueError(
            "La conexión está guardada como inactiva; complete y active su configuración antes de probarla"
        )
    validate_connection_config(connection.kind, connection.config, connection.active)
    c = connection.config
    if connection.kind == "sqlite":
        from pathlib import Path

        path = Path(c["path"]).resolve(strict=True)
        return create_engine(f"sqlite:///file:{path.as_posix()}?mode={'rw' if writable else 'ro'}&uri=true")
    drivers = {"postgresql": "postgresql+psycopg", "mysql": "mysql+pymysql", "sqlserver": "mssql+pyodbc"}
    if connection.kind not in drivers:
        raise ValueError("Motor no soportado")
    query = {}
    if connection.kind == "sqlserver":
        query = {
            "driver": c.get("driver", "ODBC Driver 18 for SQL Server"),
            "Encrypt": "yes",
            "TrustServerCertificate": "yes" if c.get("trust_certificate") else "no",
        }
        if c.get("auth", "windows") == "windows":
            query["Trusted_Connection"] = "yes"
    url = URL.create(
        drivers[connection.kind],
        username=c.get("username") or None,
        password=secrets.get(connection.credential_ref) or None,
        host=c.get("host"),
        port=c.get("port"),
        database=c.get("database"),
        query=query,
    )
    return create_engine(url, pool_pre_ping=True, hide_parameters=True)


def validate_select(query: str, kind: str):
    dialect = {"sqlserver": "tsql", "postgresql": "postgres", "mysql": "mysql", "sqlite": "sqlite"}[kind]
    statements = sqlglot.parse(query, read=dialect)
    if len(statements) != 1 or not isinstance(statements[0], exp.Query):
        raise PermissionError("Solo una consulta SELECT de lectura está permitida")
    tree = statements[0]
    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Command, exp.Into, exp.Merge, exp.Copy)
    if any(isinstance(node, forbidden) for node in tree.walk()):
        raise PermissionError("Consulta contiene operaciones no autorizadas")
    # Functions can execute arbitrary server code; use a conservative allowlist.
    allowed = {
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX",
        "COALESCE",
        "UPPER",
        "LOWER",
        "ROUND",
        "ABS",
        "LENGTH",
        "DATE",
        "CAST",
        "EXTRACT",
        "YEAR",
        "MONTH",
        "DAY",
        "DATE_TRUNC",
    }
    for node in tree.find_all(exp.Func):
        name = node.name.upper() if isinstance(node, exp.Anonymous) else node.sql_name().upper()
        if name not in allowed:
            raise PermissionError(f"Función SQL no autorizada: {name}")
    return query


def query_readonly(session: Session, agent: Agent, connection_id: str, query: str, parameters=None, max_rows=10000):
    connection = session.get(Connection, connection_id)
    assignment = session.get(AgentConnection, (agent.id, connection_id))
    if (
        not connection
        or not connection.active
        or not assignment
        or not {"connect", "select"}.issubset(assignment.permissions)
    ):
        raise PermissionError("Conexión no asignada con permisos connect/select")
    validate_select(query, connection.kind)
    engine = connection_engine(connection)
    try:
        with engine.connect() as db:
            with db.begin():
                if connection.kind == "postgresql":
                    db.execute(text("SET TRANSACTION READ ONLY"))
                    db.execute(text("SET LOCAL statement_timeout = 30000"))
                elif connection.kind == "mysql":
                    db.execute(text("SET TRANSACTION READ ONLY"))
                elif connection.kind == "sqlserver":
                    db.connection.driver_connection.timeout = 30
                elif connection.kind == "sqlite":
                    deadline = time.monotonic() + 30
                    db.connection.driver_connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
                records = db.execute(text(query), parameters or {}).mappings().fetchmany(max_rows + 1)
                if len(records) > max_rows:
                    raise ValueError(f"La consulta excede {max_rows} filas; agregue un límite")
                rows = [
                    {
                        key: value if isinstance(value, (str, int, float, bool, type(None))) else str(value)
                        for key, value in row.items()
                    }
                    for row in records
                ]
        return {"rows": rows, "count": len(rows)}
    finally:
        engine.dispose()


def execute_write(session, task, agent, args):
    connection = session.get(Connection, args["connection_id"])
    assignment = session.get(AgentConnection, (agent.id, args["connection_id"]))
    if not connection or not connection.active or not assignment or not {"connect", "execute"}.issubset(assignment.permissions):
        raise PermissionError("SQL de escritura requiere conexión asignada con connect/execute")
    config = connection.config
    if not config.get("writable_enabled") or not config.get("write_tables"):
        raise PermissionError("Active writable_enabled y declare write_tables en la conexión antes de escribir")
    dialect = {"sqlserver": "tsql", "postgresql": "postgres", "sqlite": "sqlite", "mysql": "mysql"}.get(connection.kind)
    if not dialect:
        raise PermissionError("La conexión no es SQL")
    statements = sqlglot.parse(args["query"], read=dialect)
    if len(statements) != 1 or not isinstance(statements[0], (exp.Insert, exp.Update, exp.Delete)):
        raise PermissionError("sql.execute admite una única operación INSERT, UPDATE o DELETE; DDL prohibido")
    tree = statements[0]
    operation = tree.key
    if operation not in config.get("write_operations", ["insert", "update", "delete"]):
        raise PermissionError("Operación no autorizada en la conexión")
    if isinstance(tree, (exp.Update, exp.Delete)) and tree.args.get("where") is None:
        raise PermissionError("UPDATE/DELETE requieren WHERE")
    if any(isinstance(node, (exp.Func, exp.Query, exp.Command, exp.Into, exp.Returning)) for node in tree.walk()):
        raise PermissionError("Escrituras con funciones, subconsultas, comandos o RETURNING no están habilitadas")
    tables = {".".join(part for part in (node.catalog, node.db, node.name) if part) for node in tree.find_all(exp.Table)}
    if not tables or not tables.issubset(set(config["write_tables"])):
        raise PermissionError("Tabla de escritura no autorizada")
    require_approval(session, task, agent, "sql-write", {"args": args, "config": config},
                     f"Autorizar {operation.upper()} en {connection.name}: {', '.join(sorted(tables))}")
    engine = connection_engine(connection, writable=True)
    try:
        with engine.begin() as db:
            if connection.kind == "sqlserver":
                db.connection.driver_connection.timeout = 30
            elif connection.kind == "postgresql":
                db.execute(text("SET LOCAL statement_timeout = 30000"))
            elif connection.kind == "sqlite":
                deadline = time.monotonic() + 30
                db.connection.driver_connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            result = db.execute(text(args["query"]), args.get("parameters", {}))
            affected = result.rowcount
            if affected < 0 or affected > config.get("max_write_rows", 1000):
                raise ValueError("Cantidad de filas afectadas desconocida o superior al límite; transacción revertida")
        return {"operation": operation, "tables": sorted(tables), "affected_rows": affected, "committed": True}
    finally:
        engine.dispose()


def describe_connection(
    session: Session, agent: Agent, connection_id: str, table: str | None = None, schema: str | None = None
):
    connection = session.get(Connection, connection_id)
    assignment = session.get(AgentConnection, (agent.id, connection_id))
    if (
        not connection
        or not connection.active
        or not assignment
        or not {"connect", "select"}.issubset(assignment.permissions)
    ):
        raise PermissionError("Conexión no asignada con permisos connect/select")
    engine = connection_engine(connection)
    try:
        metadata = inspect(engine)
        names = metadata.get_table_names(schema=schema)
        if table is None:
            return {"tables": names[:100], "truncated": len(names) > 100, "schema": schema}
        if table not in names:
            raise ValueError("La tabla no existe en el esquema solicitado")
        columns = metadata.get_columns(table, schema=schema)
        return {
            "table": table,
            "schema": schema,
            "columns": [
                {"name": c["name"], "type": str(c["type"]), "nullable": c.get("nullable", True)} for c in columns[:100]
            ],
            "truncated": len(columns) > 100,
        }
    finally:
        engine.dispose()
