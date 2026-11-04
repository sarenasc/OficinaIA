"""Read-only SQL plus explicit credential references."""

import re
import time

import sqlglot
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError
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


# sqlglot models much syntax as functions with its own canonical names: CASE, IIF -> IF,
# DATEPART -> EXTRACT, LEN -> LENGTH, CHARINDEX -> STR_POSITION, GETDATE -> CURRENT_TIMESTAMP,
# DATENAME/FORMAT -> TIME_TO_STR... tests/test_sql_functions.py keeps a corpus per dialect.
# Everything here is deterministic, read-only and local to the query. Never add procedures,
# OPENQUERY/OPENROWSET/OPENDATASOURCE, file, network, sleep or set-generating functions.
SAFE_SQL_FUNCTIONS = frozenset({
    # Conditional and nulls
    "CASE", "IF", "COALESCE", "NULLIF", "GREATEST", "LEAST", "CHOOSE", "EXISTS", "COLLATE",
    # Aggregates and statistics
    "COUNT", "SUM", "AVG", "MIN", "MAX", "STDDEV", "STDDEV_POP", "STDDEV_SAMP", "VARIANCE", "VARIANCE_POP",
    "STDEV", "STDEVP", "VAR", "VARP", "TOTAL", "APPROX_DISTINCT", "GROUPING", "GROUP_CONCAT", "STRING_AGG",
    "ARRAY_AGG", "LOGICAL_OR", "LOGICAL_AND", "PERCENTILE_CONT", "PERCENTILE_DISC", "MEDIAN",
    # Window functions
    "ROW_NUMBER", "RANK", "DENSE_RANK", "NTILE", "LAG", "LEAD", "FIRST_VALUE", "LAST_VALUE", "NTH_VALUE",
    "CUME_DIST", "PERCENT_RANK",
    # Numbers
    "ROUND", "ABS", "CEIL", "FLOOR", "POWER", "SQRT", "SIGN", "MOD", "LN", "LOG", "LOG10", "EXP", "PI",
    "SQUARE", "TRUNC", "NUMBER_TO_STR", "STR",
    # Types
    "CAST", "TRY_CAST", "CONVERT", "TRY_CONVERT", "PARSE", "TRY_PARSE", "ISNUMERIC", "ISDATE", "TYPEOF",
    # Text
    "LENGTH", "UPPER", "LOWER", "TRIM", "SUBSTRING", "LEFT", "RIGHT", "REPLACE", "CONCAT", "CONCAT_WS",
    "STR_POSITION", "PATINDEX", "SPLIT_PART", "REVERSE", "REPEAT", "SPACE", "STUFF", "TRANSLATE", "ASCII",
    "UNICODE", "CHR", "NCHAR", "QUOTENAME", "PRINTF", "FORMAT",
    # Dates
    "DATE", "DATETIME", "YEAR", "MONTH", "DAY", "QUARTER", "WEEK", "WEEK_OF_YEAR", "DAY_OF_WEEK",
    "DAY_OF_MONTH", "DAY_OF_YEAR", "EXTRACT", "DATE_TRUNC", "TIMESTAMP_TRUNC", "DATETRUNC", "DATE_ADD",
    "DATE_SUB", "DATEDIFF", "DATE_DIFF", "TIMESTAMPDIFF", "TIMESTAMP_DIFF", "LAST_DAY", "DATE_FROM_PARTS",
    "TIMESTAMP_FROM_PARTS", "MAKE_DATE", "TIME_TO_STR", "STR_TO_DATE", "STR_TO_TIME", "TIME_STR_TO_TIME",
    "TS_OR_DS_TO_DATE", "TS_OR_DS_TO_TIMESTAMP", "JULIANDAY", "AGE", "CURRENT_TIMESTAMP",
    "CURRENT_TIMESTAMP_L_T_Z", "CURRENT_DATE", "CURRENT_TIME", "NOW", "GETUTCDATE",
    # Metadata of the active database and login (names only)
    "DB_NAME", "CURRENT_DATABASE", "CURRENT_SCHEMA", "CURRENT_USER", "USER_NAME", "SUSER_SNAME",
    "OBJECT_ID", "OBJECT_NAME", "OBJECT_SCHEMA_NAME", "COL_NAME", "TYPE_NAME", "HAS_PERMS_BY_NAME",
})


class QueryRejected(PermissionError):
    """The query text itself was refused before reaching the server; the agent may rewrite it."""


def validate_select(query: str, kind: str):
    dialect = {"sqlserver": "tsql", "postgresql": "postgres", "mysql": "mysql", "sqlite": "sqlite"}[kind]
    try:
        statements = sqlglot.parse(query, read=dialect)
    except sqlglot.errors.ParseError as exc:
        raise QueryRejected(f"No se pudo interpretar la consulta SQL: {str(exc).splitlines()[0][:300]}") from None
    if len(statements) != 1 or not isinstance(statements[0], exp.Query):
        raise QueryRejected("Solo una consulta SELECT de lectura está permitida")
    tree = statements[0]
    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Command, exp.Into, exp.Merge, exp.Copy)
    if any(isinstance(node, forbidden) for node in tree.walk()):
        raise QueryRejected("Consulta contiene operaciones no autorizadas")
    # Functions can execute arbitrary server code; only the read-only allowlist below.
    for node in tree.find_all(exp.Func):
        if isinstance(node, exp.Connector):
            continue  # AND/OR/XOR are logical operators, modeled as Func by sqlglot>=29
        name = node.name.upper() if isinstance(node, exp.Anonymous) else node.sql_name().upper()
        if name not in SAFE_SQL_FUNCTIONS:
            raise QueryRejected(f"Función SQL no autorizada: {name}")
    return query


def server_version(engine) -> str:
    info = getattr(engine.dialect, "server_version_info", None) or ()
    version = ".".join(str(part) for part in info[:2])
    names = {"13": "2016", "14": "2017", "15": "2019", "16": "2022", "17": "2025"}
    if engine.dialect.name == "mssql" and info:
        return f"SQL Server {names.get(str(info[0]), version)} ({version})"
    return version


def server_error(exc, engine) -> str:
    """The server's own message without the echoed SQL or driver noise."""
    text_ = str(getattr(exc, "orig", exc))
    message = text_.split("[SQL:")[0]
    if "[SQL Server]" in message:
        message = re.split(r"\s*\(\d+\)\s*\(SQL\w+\)", message.split("[SQL Server]", 1)[1])[0]
    message = message.strip().rstrip(".")[:400]
    version = server_version(engine)
    suffix = f" Servidor: {version}." if version else ""
    return (f"El servidor rechazó la consulta: {message}.{suffix} Corrija la consulta; funciones como STRING_AGG, "
            "TRIM o CONCAT_WS no existen en versiones antiguas")


def query_readonly(session: Session, agent: Agent, connection_id: str, query: str, parameters=None, max_rows=10000,
                   truncate=False):
    """truncate: return the first max_rows rows with truncated=True (exploration) instead of failing (exports)."""
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
                try:
                    records = db.execute(text(query), parameters or {}).mappings().fetchmany(max_rows + 1)
                except (ProgrammingError, OperationalError) as exc:
                    # Read-only query refused by the server (syntax, missing column, function not in this
                    # version): the agent can rewrite it. Connection failures happen before this point.
                    raise QueryRejected(server_error(exc, engine)) from None
                truncated = len(records) > max_rows
                if truncated and not truncate:
                    raise ValueError(f"La consulta excede {max_rows} filas; agregue un límite")
                records = records[:max_rows]
                rows = [
                    {
                        key: value if isinstance(value, (str, int, float, bool, type(None))) else str(value)
                        for key, value in row.items()
                    }
                    for row in records
                ]
        if truncated:
            return {"rows": rows, "count": len(rows), "truncated": True,
                    "notice": f"Hay más de {max_rows} filas; se muestran las primeras {max_rows}. "
                              "Use filtros, GROUP BY o COUNT(*) si necesita el total"}
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


MAX_DESCRIBED_OBJECTS = 60


def _columns(metadata, table, schema, compact=False):
    columns = metadata.get_columns(table, schema=schema)
    if compact:  # "fecha DATE", "kilos DECIMAL(18, 2) NULL": several tables fit in the agent context
        listed = [f"{c['name']} {c['type']}" + (" NULL" if c.get("nullable", True) else "") for c in columns[:100]]
    else:
        listed = [{"name": c["name"], "type": str(c["type"]), "nullable": c.get("nullable", True)} for c in columns[:100]]
    return listed, len(columns) > 100


def _row_counts(engine, kind: str, schema: str | None, default_schema: str | None, names: list[str]) -> dict:
    """Table row counts from metadata, without scanning data; {} when the login cannot read it."""
    try:
        with engine.connect() as db:
            if kind == "sqlserver":
                rows = db.execute(text(
                    "SELECT s.name AS sch, t.name AS tbl, SUM(p.rows) AS total FROM sys.tables t "
                    "JOIN sys.schemas s ON s.schema_id = t.schema_id "
                    "JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0, 1) "
                    "GROUP BY s.name, t.name"
                )).mappings()
                wanted = schema or default_schema
                return {r["tbl"]: int(r["total"]) for r in rows if r["sch"] == wanted and r["tbl"] in names}
            if kind == "sqlite":
                quote = engine.dialect.identifier_preparer.quote
                return {name: db.execute(text(f"SELECT COUNT(*) FROM {quote(name)}")).scalar() for name in names}
    except SQLAlchemyError:
        return {}
    return {}


def describe_connection(
    session: Session, agent: Agent, connection_id: str, table: str | None = None, schema: str | None = None,
    columns: bool = False,
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
        views = metadata.get_view_names(schema=schema)
        database = connection.config.get("database") or connection.config.get("path")
        if table is None:
            result = {"database": database, "server": server_version(engine),
                      "schema": schema or metadata.default_schema_name,
                      "tables": names[:100], "views": views[:100],
                      "truncated": len(names) > 100 or len(views) > 100}
            if columns:
                # One call instead of one describe and one COUNT per object: saves agent steps.
                counts = _row_counts(engine, connection.kind, schema, metadata.default_schema_name,
                                     names[:MAX_DESCRIBED_OBJECTS])
                objects = []
                for kind, items in (("table", names), ("view", views)):
                    for name in items:
                        if len(objects) >= MAX_DESCRIBED_OBJECTS:
                            break
                        cols, cut = _columns(metadata, name, schema, compact=True)
                        objects.append({"name": name, "kind": kind, "rows": counts.get(name), "columns": cols,
                                        "columns_truncated": cut})
                result["objects"] = objects
                result["objects_truncated"] = len(names) + len(views) > len(objects)
                result["rows_note"] = ("rows es el total de filas según los metadatos del servidor; null en vistas "
                                       "o sin permiso: use sql.query con SELECT COUNT(*) si lo necesita")
            return result
        if table not in names and table not in views:
            raise ValueError("La tabla o vista no existe en el esquema solicitado")
        cols, cut = _columns(metadata, table, schema)
        return {
            "database": database,
            "table": table,
            "kind": "view" if table in views else "table",
            "schema": schema,
            "rows": _row_counts(engine, connection.kind, schema, metadata.default_schema_name, [table]).get(table)
            if table in names else None,
            "columns": cols,
            "truncated": cut,
        }
    finally:
        engine.dispose()
