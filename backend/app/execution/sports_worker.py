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


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--diagnostic":
        print(json.dumps({"python": sys.version.split()[0], "packages": {"stdlib": sys.version.split()[0]},
                          "operations": ["sports.analyze", "statistics.mean", "sports.group", "csv.read", "csv.create"]}))
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
    raise ValueError("Operación o parámetros no autorizados")


if __name__ == "__main__":
    main()
