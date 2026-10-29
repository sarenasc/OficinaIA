"""Strict parameter contracts for the single python.execute tool."""
from jsonschema import validate


def object_schema(properties, required):
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


TEXT = {"type": "string", "minLength": 1, "maxLength": 1000}
FILE = {"resource_id": TEXT, "path": TEXT}
SCALAR = {"type": ["string", "number", "boolean", "null"], "maxLength": 2000}
OPERATIONS = {
    "statistics.mean": object_schema({"values": {"type": "array", "minItems": 1, "maxItems": 10000,
        "items": {"type": "number", "minimum": -1e12, "maximum": 1e12}}}, ["values"]),
    "sports.group": object_schema({**FILE, "group_column": TEXT, "value_column": TEXT},
                                  ["resource_id", "path", "group_column", "value_column"]),
    "csv.read": object_schema(FILE, ["resource_id", "path"]),
    "csv.create": object_schema({**FILE, "rows": {"type": "array", "minItems": 1, "maxItems": 1000,
        "items": {"type": "object", "minProperties": 1, "maxProperties": 30,
                  "propertyNames": {"type": "string", "minLength": 1, "maxLength": 200},
                  "additionalProperties": SCALAR}}}, ["resource_id", "path", "rows"]),
    # Dot paths: key, list index or key[field=value]; e.g. children.0.standings.entries
    "json.keys": object_schema({**FILE, "at": {"type": "string", "maxLength": 1000}}, ["resource_id", "path"]),
    "json.table": object_schema({**FILE, "rows": {"type": "string", "maxLength": 1000}, "output_path": TEXT,
        "columns": {"type": "object", "minProperties": 1, "maxProperties": 30,
                    "propertyNames": {"type": "string", "minLength": 1, "maxLength": 200},
                    "additionalProperties": TEXT}}, ["resource_id", "path", "rows", "columns", "output_path"]),
    # League title odds from a standings CSV and a pending-fixtures CSV in the same resource.
    "poisson.simulate": object_schema({
        "resource_id": TEXT, "table_path": TEXT, "pending_path": TEXT,
        "table_columns": object_schema({key: TEXT for key in ("team", "played", "points", "goals_for", "goals_against")},
                                       ["team", "played", "points", "goals_for", "goals_against"]),
        "pending_columns": object_schema({"home": TEXT, "away": TEXT}, ["home", "away"]),
        "simulations": {"type": "integer", "minimum": 1000, "maximum": 20000},
        "seed": {"type": "integer", "minimum": 0, "maximum": 2147483647},
        "home_advantage": {"type": "number", "minimum": 0.5, "maximum": 2.0},
    }, ["resource_id", "table_path", "pending_path", "table_columns", "pending_columns"]),
}
PYTHON_SCHEMA = {"oneOf": [object_schema({"code": {"type": "string", "maxLength": 2000000},
    "resources": {"type": "array", "items": TEXT, "uniqueItems": True}}, ["code", "resources"]), *[
    object_schema({"operation": {"const": name}, "parameters": parameters}, ["operation", "parameters"])
    for name, parameters in OPERATIONS.items()]]}


def validate_operation(name, parameters):
    if name not in OPERATIONS:
        raise ValueError("Operación Python no autorizada: " + str(name))
    validate(parameters, OPERATIONS[name])
