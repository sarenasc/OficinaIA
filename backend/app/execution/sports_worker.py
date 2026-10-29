"""Trusted stdlib-only worker. No eval, scripts, plugins, URLs or executable input."""
import bisect
import csv
import io
import json
import math
import random
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


def read_csv(path, required):
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = [column for column in required if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("Columnas inexistentes en el CSV: " + ", ".join(missing))
        rows = []
        for row in reader:
            if len(rows) >= 1000 or None in row:
                raise ValueError("CSV supera 1000 filas o está mal formado")
            rows.append(row)
    if not rows:
        raise ValueError("CSV sin datos")
    return rows


def number(value, label):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Valor numérico inválido en {label}: {value!r}") from None
    if not math.isfinite(result) or not 0 <= result <= 100000:
        raise ValueError(f"Valor fuera de rango en {label}")
    return result


def goal_cdf(rate):
    """Cumulative Poisson probabilities for 0..15 goals; the tail goes to the last bucket."""
    term, total, cdf = math.exp(-rate), 0.0, []
    for goals in range(16):
        total += term
        cdf.append(total)
        term *= rate / (goals + 1)
    cdf[-1] = 1.0
    return cdf


def poisson_simulate(table_path, pending_path, table_columns, pending_columns, simulations=10000, seed=2026,
                     home_advantage=1.0):
    columns = table_columns
    teams = {}
    for row in read_csv(table_path, list(columns.values())):
        name = row[columns["team"]].strip()
        if not name or name in teams:
            raise ValueError("Equipo vacío o repetido en la tabla: " + name)
        played = number(row[columns["played"]], "played")
        if played < 1:
            raise ValueError(f"{name} no tiene partidos jugados")
        teams[name] = {"played": played, "points": number(row[columns["points"]], "points"),
                       "goals_for": number(row[columns["goals_for"]], "goals_for"),
                       "goals_against": number(row[columns["goals_against"]], "goals_against")}
    if not 2 <= len(teams) <= 40:
        raise ValueError("La tabla debe tener entre 2 y 40 equipos")
    fixtures = []
    for row in read_csv(pending_path, [pending_columns["home"], pending_columns["away"]]):
        home, away = row[pending_columns["home"]].strip(), row[pending_columns["away"]].strip()
        unknown = [team for team in (home, away) if team not in teams]
        if unknown or home == away:
            raise ValueError("Partido pendiente con equipos que no están en la tabla: " + ", ".join(unknown or [home]))
        fixtures.append((home, away))
    # Per-team calendars list each direct meeting twice; it is played once.
    duplicates = len(fixtures) - len(set(fixtures))
    fixtures = list(dict.fromkeys(fixtures))
    if simulations * len(fixtures) > 3000000:
        raise ValueError("Demasiados partidos para esa cantidad de simulaciones; reduzca simulations")
    # Strengths relative to the league's goals per team per match, from this table only.
    average = sum(t["goals_for"] for t in teams.values()) / sum(t["played"] for t in teams.values())
    if average <= 0:
        raise ValueError("La tabla no registra goles")
    attack = {name: t["goals_for"] / t["played"] / average for name, t in teams.items()}
    defense = {name: t["goals_against"] / t["played"] / average for name, t in teams.items()}
    rates = [(home, away,
              goal_cdf(min(max(average * attack[home] * defense[away] * home_advantage, 0.01), 10)),
              goal_cdf(min(max(average * attack[away] * defense[home], 0.01), 10))) for home, away in fixtures]
    rng = random.Random(seed)
    titles = dict.fromkeys(teams, 0.0)
    expected = dict.fromkeys(teams, 0.0)
    for _ in range(simulations):
        points = {name: t["points"] for name, t in teams.items()}
        difference = {name: t["goals_for"] - t["goals_against"] for name, t in teams.items()}
        scored = {name: t["goals_for"] for name, t in teams.items()}
        for home, away, home_cdf, away_cdf in rates:
            home_goals = bisect.bisect_left(home_cdf, rng.random())
            away_goals = bisect.bisect_left(away_cdf, rng.random())
            points[home] += 3 if home_goals > away_goals else 1 if home_goals == away_goals else 0
            points[away] += 3 if away_goals > home_goals else 1 if home_goals == away_goals else 0
            difference[home] += home_goals - away_goals
            difference[away] += away_goals - home_goals
            scored[home] += home_goals
            scored[away] += away_goals
        # Tie-break: points, goal difference, goals scored; a remaining tie shares the title equally.
        best = max((points[t], difference[t], scored[t]) for t in teams)
        leaders = [t for t in teams if (points[t], difference[t], scored[t]) == best]
        for team in leaders:
            titles[team] += 1 / len(leaders)
        for team in teams:
            expected[team] += points[team]
    pending = {name: sum(name in fixture for fixture in fixtures) for name in teams}
    results = sorted(({"team": name, "points_now": t["points"], "pending_matches": pending[name],
                       "max_points": t["points"] + 3 * pending[name],
                       "expected_points": round(expected[name] / simulations, 2),
                       "champion_probability": round(titles[name] / simulations, 4)} for name, t in teams.items()),
                     key=lambda item: (-item["champion_probability"], -item["points_now"]))
    return {"simulations": simulations, "seed": seed, "home_advantage": home_advantage, "fixtures": len(fixtures),
            "duplicate_fixtures_removed": duplicates,
            "league_goals_per_team_match": round(average, 4), "results": results,
            "teams_without_pending": [name for name in teams if not pending[name]],
            "notice": "Modelo de Poisson con fuerzas de ataque y defensa de la tabla entregada; desempate por puntos, "
                      "diferencia de gol y goles a favor. Equipos sin partidos pendientes conservan sus puntos actuales. "
                      "Es una estimación, no una predicción garantizada."}


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--diagnostic":
        print(json.dumps({"python": sys.version.split()[0], "packages": {"stdlib": sys.version.split()[0]},
                          "operations": ["sports.analyze", "statistics.mean", "sports.group", "csv.read", "csv.create",
                                         "json.keys", "json.table", "poisson.simulate"]}))
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
    if operation == "poisson.simulate" and {"table_path", "pending_path", "table_columns", "pending_columns"} <= set(
            parameters) <= {"table_path", "pending_path", "table_columns", "pending_columns", "simulations", "seed",
                            "home_advantage"}:
        return {"operation": operation, **poisson_simulate(**parameters)}
    raise ValueError("Operación o parámetros no autorizados")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # -I ignores PYTHONIOENCODING; write UTF-8 bytes so accents survive, without a traceback.
        sys.stderr.buffer.write(f"{type(exc).__name__}: {exc}".encode("utf-8"))
        sys.exit(1)
