"""Registered data, filesystem, isolated Python and workbook capabilities."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tool


def schema(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


TEXT = {"type": "string"}
RESOURCE = {"resource_id": TEXT, "path": TEXT}
ROWS = {"type": "array", "items": {"type": "object"}, "maxItems": 100000}
BUILTINS = [
    (
        "excel.chart",
        "Agrupar datos reales y agregar gráfico de barras en otra pestaña del mismo Excel",
        "excel.chart",
        schema({**RESOURCE, "category_column": TEXT, "value_column": TEXT, "sheet": TEXT,
                "chart_sheet": TEXT}, ["resource_id", "path", "category_column", "value_column"]),
        [],
    ),
    (
        "filesystem.read",
        "Leer texto UTF-8 de un recurso autorizado",
        "filesystem.read",
        schema(RESOURCE, ["resource_id", "path"]),
        [],
    ),
    (
        "filesystem.write",
        "Crear texto; sobrescribir requiere permiso y aprobación en modo seguro",
        "filesystem.write",
        schema({**RESOURCE, "content": TEXT}, ["resource_id", "path", "content"]),
        [],
    ),
    (
        "filesystem.create_directory",
        "Crear carpeta en recurso autorizado",
        "filesystem.create_directory",
        schema(RESOURCE, ["resource_id", "path"]),
        [],
    ),
    (
        "csv.read",
        "Leer CSV en registros, máximo 10000 filas",
        "csv.read",
        schema({**RESOURCE, "delimiter": {"type": "string", "minLength": 1, "maxLength": 1}}, ["resource_id", "path"]),
        [],
    ),
    (
        "data.summarize",
        "Resumen real por columna: cantidad, suma, promedio, mínimo y máximo",
        "data.summarize",
        schema({"rows": ROWS}, ["rows"]),
        [],
    ),
    (
        "excel.create",
        "Crear Excel con datos, resumen, tablas, formatos y gráfico",
        "excel.create",
        schema({**RESOURCE, "rows": ROWS, "summary": ROWS}, ["resource_id", "path", "rows"]),
        [],
    ),
    (
        "excel.read",
        "Leer valores de las hojas de un workbook",
        "excel.read",
        schema(RESOURCE, ["resource_id", "path"]),
        [],
    ),
    (
        "filesystem.list",
        "Listar archivos reales de una carpeta autorizada, sin recorrer subcarpetas",
        "filesystem.list",
        schema({**RESOURCE, "limit": {"type": "integer", "minimum": 1, "maximum": 500}}, ["resource_id"]),
        [],
    ),
    (
        "excel.generate_sales",
        "Crear Excel de ventas ficticias con código. No escriba filas en el JSON; use count",
        "excel.generate_sales",
        schema(
            {**RESOURCE, "count": {"type": "integer", "minimum": 1, "maximum": 10000}, "seed": {"type": "integer"}},
            ["resource_id", "path", "count"],
        ),
        [],
    ),
    (
        "excel.from_csv",
        "Convertir CSV a Excel sin enviar sus filas al modelo",
        "excel.from_csv",
        schema(
            {
                "source_resource_id": TEXT,
                "source_path": TEXT,
                **RESOURCE,
                "delimiter": {"type": "string", "minLength": 1, "maxLength": 1},
            },
            ["source_resource_id", "source_path", "resource_id", "path"],
        ),
        [],
    ),
    (
        "sql.export_excel",
        "Ejecutar SELECT y crear Excel directamente; cálculos y agrupaciones se hacen en SQL",
        "sql.export_excel",
        schema({"connection_id": TEXT, "query": TEXT, **RESOURCE}, ["connection_id", "query", "resource_id", "path"]),
        [],
    ),
    (
        "social.prepare_post",
        "Preparar un borrador de publicación local. NO publica en redes ni autoriza publicación",
        "social.prepare_post",
        schema(
            {
                **RESOURCE,
                "platform": {"type": "string", "enum": ["linkedin", "facebook", "instagram"]},
                "text": {"type": "string", "minLength": 1, "maxLength": 10000},
            },
            ["resource_id", "path", "platform", "text"],
        ),
        [],
    ),
    (
        "python.execute",
        "Ejecutar script en Docker aislado; montajes definidos por recursos asignados",
        "python.execute",
        schema(
            {"code": TEXT, "resources": {"type": "array", "items": TEXT, "uniqueItems": True}}, ["code", "resources"]
        ),
        ["python.execute"],
    ),
    (
        "sql.describe",
        "Conocer tablas y columnas reales antes de formular consultas SQL. Solo metadatos",
        "sql.describe",
        schema({"connection_id": TEXT, "table": TEXT, "schema": TEXT}, ["connection_id"]),
        [],
    ),
    (
        "sql.query",
        "Ejecutar una única consulta de lectura en conexión asignada",
        "sql.query",
        schema({"connection_id": TEXT, "query": TEXT}, ["connection_id", "query"]),
        [],
    ),
]


def register_builtins(session: Session):
    from app.execution.catalog import PYTHON_SCHEMA
    from app.tools.stage3_builtins import PARAMETERS, TOOLS
    for name, description, kind, parameters, permissions in BUILTINS + TOOLS:
        if name == "python.execute":
            parameters = PYTHON_SCHEMA
            description = "Python: operation/parameters para cálculos y CSV controlados; code/resources requiere Docker aislado"
        if name == "sql.query":
            parameters = schema({"connection_id": TEXT, "query": TEXT, "parameters": PARAMETERS,
                                 "max_rows": {"type": "integer", "minimum": 1, "maximum": 10000}}, ["connection_id", "query"])
        existing = session.scalar(select(Tool).where(Tool.name == name))
        risk = "high" if name in {"sql.execute", "python.execute", "api.request"} else "medium" if name.startswith(("web.", "pdf.")) or name == "filesystem.write" else "low"
        if not existing:
            session.add(
                Tool(
                    name=name,
                    description=description,
                    kind=kind,
                    parameters=parameters,
                    required_permissions=permissions,
                    builtin=True,
                    config={"risk": risk},
                )
            )
        elif existing.builtin:
            existing.parameters = parameters
            if name in {"python.execute", "web.fetch"}:
                existing.description = description
            existing.config = {**existing.config, "risk": risk}
    session.commit()
