"""Trusted stdlib-only worker. No eval, scripts, plugins, URLs or executable input."""
import csv
import io
import json
import math
import statistics
import sys
from pathlib import Path


def analyze(path, group_column, value_column):
    groups = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or len(reader.fieldnames) > 100 or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("CSV requiere encabezados únicos, máximo 100 columnas")
        if group_column not in reader.fieldnames or value_column not in reader.fieldnames:
            raise ValueError("Columnas solicitadas no existen en el CSV")
        count = 0
        for row in reader:
            count += 1
            if count > 10000 or None in row:
                raise ValueError("CSV excede 10000 filas o contiene filas mal formadas")
            group = row[group_column]
            if not group or len(group) > 200:
                raise ValueError("Grupo vacío o demasiado largo")
            value = float(row[value_column])
            if not math.isfinite(value) or value < 0 or value > 1000000:
                raise ValueError("Valor deportivo debe ser finito entre 0 y 1000000")
            groups.setdefault(group, []).append(value)
            if len(groups) > 200:
                raise ValueError("Máximo 200 grupos")
    if not count:
        raise ValueError("CSV sin datos")
    return {"rows": count, "group_column": group_column, "value_column": value_column,
            "summary": [{"group": key, "count": len(values), "sum": sum(values),
                         "mean": statistics.mean(values), "min": min(values), "max": max(values),
                         "poisson_zero": math.exp(-statistics.mean(values))}
                        for key, values in sorted(groups.items())],
            "notice": "Poisson(0) es una estimación con media observada; no predice resultados garantizados."}


def resolve(value, path):
    """Follow key, list index and key[field=value] segments; returns None when a step is missing."""
    for segment in [part for part in (path or "").split(".") if part]:
        selector = None
        if segment.endswith("]") and "[" in segment:
            segment, selector = segment[:-1].split("[", 1)
            if "=" not in selector:
                raise ValueError("Selector inválido; use clave[campo=valor]")
        if segment:
            if isinstance(value, dict):
                value = value.get(segment)
            elif isinstance(value, list) and segment.isdigit():
                value = value[int(segment)] if int(segment) < len(value) else None
            else:
                return None
        if selector is not None:
            field, expected = selector.split("=", 1)
            if not isinstance(value, list):
                return None
            value = next((item for item in value if isinstance(item, dict) and str(item.get(field)) == expected), None)
    return value


def describe(value):
    if isinstance(value, dict):
        return {"type": "object", "size": len(value)}
    if isinstance(value, list):
        return {"type": "list", "size": len(value)}
    return {"type": type(value).__name__, "value": value if not isinstance(value, str) else value[:120]}


def json_keys(path, at=""):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    value = resolve(data, at)
    if value is None:
        raise ValueError("La ruta 'at' no existe en el JSON")
    result = {"at": at, **describe(value)}
    if isinstance(value, list) and value:
        # Lists share a shape; describing the first element is enough to build a table.
        value = value[0]
        result["first_item"] = describe(value)
    if isinstance(value, dict):
        result["keys"] = {key: describe(item) for key, item in list(value.items())[:100]}
    return result


def json_table(path, rows, columns):
    items = resolve(json.loads(Path(path).read_text(encoding="utf-8-sig")), rows)
    if not isinstance(items, list) or not 1 <= len(items) <= 10000:
        raise ValueError("'rows' debe apuntar a una lista de entre 1 y 10000 elementos")
    table = []
    for item in items:
        row = {}
        for name, column_path in columns.items():
            cell = resolve(item, column_path)
            row[name] = json.dumps(cell, ensure_ascii=False)[:2000] if isinstance(cell, (dict, list)) else cell
        table.append(row)
    missing = {name: sum(row[name] is None for row in table) for name in columns}
    content = io.StringIO(newline="")
    writer = csv.DictWriter(content, fieldnames=list(columns))
    writer.writeheader()
    for row in table:
        writer.writerow({key: "'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@"))
                         else value for key, value in row.items()})
    # The worker's whole reply is capped at 1 MB; leave room for JSON escaping.
    if len(content.getvalue().encode()) > 600 * 1024:
        raise ValueError("La tabla generada excede 600 KB; elija menos columnas o una lista más pequeña")
    return {"row_count": len(table), "columns": list(columns), "sample": table[:3],
            "empty_cells": {name: count for name, count in missing.items() if count}, "content": content.getvalue()}


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--diagnostic":
        print(json.dumps({"python": sys.version.split()[0], "packages": {"stdlib": sys.version.split()[0]},
                          "operations": ["sports.analyze", "statistics.mean", "sports.group", "csv.read", "csv.create",
                                         "json.keys", "json.table"]}))
        return
    args = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if set(args) == {"operation", "parameters"}:
        print(json.dumps(run_operation(args["operation"], args["parameters"]), ensure_ascii=True, allow_nan=False))
        return
    if set(args) != {"path", "group_column", "value_column"}:
        raise ValueError("Parámetros no autorizados")
    print(json.dumps(analyze(**args), ensure_ascii=True, allow_nan=False))


def run_operation(operation, parameters):
    if operation == "statistics.mean" and set(parameters) == {"values"}:
        values = parameters["values"]
        if not isinstance(values, list) or not 1 <= len(values) <= 10000 or any(
            type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e12 for value in values
        ):
            raise ValueError("Valores numéricos finitos requeridos, máximo 10000")
        return {"operation": operation, "count": len(values),
                "sum": sum(values) if all(type(value) is int for value in values) else math.fsum(values),
                "mean": statistics.mean(values), "median": statistics.median(values),
                "population_stddev": statistics.pstdev(values)}
    if operation == "sports.group" and set(parameters) == {"path", "group_column", "value_column"}:
        return {"operation": operation, **analyze(**parameters)}
    if operation == "csv.read" and set(parameters) == {"path"}:
        with Path(parameters["path"]).open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            headers = reader.fieldnames
            if not headers or len(headers) > 30 or len(set(headers)) != len(headers):
                raise ValueError("CSV requiere hasta 30 encabezados únicos")
            rows = []
            for row in reader:
                if len(rows) >= 1000 or None in row or any(value is None or len(value) > 2000 for value in row.values()):
                    raise ValueError("CSV supera 1000 filas, celdas de 2000 caracteres o está mal formado")
                rows.append(row)
        result = {"operation": operation, "columns": headers, "rows": rows, "row_count": len(rows)}
        if len(json.dumps(result, ensure_ascii=True).encode()) > 512000:
            raise ValueError("CSV leído excede 512 KB de resultado")
        return result
    if operation == "csv.create" and set(parameters) == {"rows"}:
        rows = parameters["rows"]
        if not isinstance(rows, list) or not 1 <= len(rows) <= 1000 or not all(isinstance(row, dict) for row in rows):
            raise ValueError("CSV requiere entre 1 y 1000 registros")
        headers = list(rows[0])
        if not 1 <= len(headers) <= 30 or any(not isinstance(key, str) or not 1 <= len(key) <= 200 for key in headers):
            raise ValueError("Encabezados inválidos")
        content = io.StringIO(newline="")
        writer = csv.DictWriter(content, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            if set(row) != set(headers):
                raise ValueError("Todas las filas deben contener las mismas columnas")
            for value in row.values():
                if type(value) not in (str, int, float, bool, type(None)) or (
                    isinstance(value, str) and len(value) > 2000
                ) or (type(value) in (int, float) and (not math.isfinite(value) or abs(value) > 1e12)):
                    raise ValueError("Celda CSV inválida")
            # Neutralize spreadsheet formulas when the CSV is later opened in Excel.
            writer.writerow({key: "'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@"))
                             else value for key, value in row.items()})
        result = {"operation": operation, "row_count": len(rows), "columns": headers, "content": content.getvalue()}
        if len(json.dumps(result, ensure_ascii=True).encode()) > 512000:
            raise ValueError("CSV generado excede 512 KB de resultado")
        return result
    if operation == "json.keys" and set(parameters) in ({"path"}, {"path", "at"}):
        return {"operation": operation, **json_keys(**parameters)}
    if operation == "json.table" and set(parameters) == {"path", "rows", "columns"}:
        return {"operation": operation, **json_table(**parameters)}
    raise ValueError("Operación o parámetros no autorizados")


if __name__ == "__main__":
    main()
