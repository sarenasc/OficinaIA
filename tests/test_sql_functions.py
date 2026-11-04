"""Corpus of read-only analytic queries an agent writes; each must pass validate_select."""
import pytest
from app.tools.connections import validate_select
from sqlglot.errors import ParseError

TSQL = [
    "SELECT CASE WHEN kilos > 0 THEN 'si' ELSE 'no' END AS c FROM t",
    "SELECT CASE especie WHEN 'A' THEN 1 ELSE 0 END FROM t",
    "SELECT IIF(kilos > 0, 1, 0) FROM t",
    "SELECT especie, SUM(kilos) AS k, COUNT(DISTINCT exportadora) FROM t GROUP BY especie "
    "HAVING SUM(kilos) > 0 ORDER BY k DESC",
    "SELECT TOP 10 * FROM t ORDER BY fecha DESC",
    "SELECT * FROM t ORDER BY fecha OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY",
    "SELECT * FROM t WITH (NOLOCK) WHERE a = 1 OR b = 2 AND NOT c = 3",
    "SELECT ROW_NUMBER() OVER (PARTITION BY especie ORDER BY fecha) AS rn, RANK() OVER (ORDER BY kilos), "
    "DENSE_RANK() OVER (ORDER BY kilos), LAG(kilos) OVER (ORDER BY fecha), LEAD(kilos, 1, 0) OVER (ORDER BY fecha), "
    "SUM(kilos) OVER (PARTITION BY especie), NTILE(4) OVER (ORDER BY kilos), FIRST_VALUE(kilos) OVER (ORDER BY fecha), "
    "LAST_VALUE(kilos) OVER (ORDER BY fecha), CUME_DIST() OVER (ORDER BY kilos), PERCENT_RANK() OVER (ORDER BY kilos) FROM t",
    "SELECT DATEPART(week, fecha), DATEPART(month, fecha), DATEPART(quarter, fecha), DATEPART(iso_week, fecha), "
    "DATENAME(month, fecha), DATENAME(weekday, fecha), DATEADD(day, -7, fecha), DATEDIFF(day, fecha, GETDATE()), "
    "EOMONTH(fecha), EOMONTH(fecha, -1), DATEFROMPARTS(2026, 1, 1), DATETIMEFROMPARTS(2026, 1, 1, 0, 0, 0, 0), "
    "DATETRUNC(month, fecha), YEAR(fecha), MONTH(fecha), DAY(fecha) FROM t",
    "SELECT CONVERT(date, fecha), CONVERT(varchar(10), fecha, 103), TRY_CAST(x AS int), TRY_CONVERT(int, x), "
    "CAST(kilos AS decimal(18, 2)), FORMAT(fecha, 'yyyy-MM'), FORMAT(kilos, 'N2'), STR(kilos), "
    "TRY_PARSE(x AS int), PARSE(x AS int), ISNUMERIC(x), ISDATE(x) FROM t",
    "SELECT ISNULL(kilos, 0), NULLIF(cajas, 0), COALESCE(a, b, 0), kilos / NULLIF(cajas, 0), CHOOSE(2, 'a', 'b') FROM t",
    "SELECT LEN(x), LTRIM(RTRIM(x)), TRIM(x), SUBSTRING(x, 1, 3), LEFT(x, 2), RIGHT(x, 2), REPLACE(x, 'a', 'b'), "
    "CONCAT(a, '-', b), CONCAT_WS('-', a, b), CHARINDEX('a', x), PATINDEX('%a%', x), UPPER(x), LOWER(x), REVERSE(x), "
    "REPLICATE('a', 2), SPACE(2), STUFF(x, 1, 1, 'b'), TRANSLATE(x, 'a', 'b'), ASCII(x), UNICODE(x), CHAR(65), "
    "NCHAR(65), QUOTENAME(x) FROM t",
    "SELECT STRING_AGG(x, ',') FROM t",
    "SELECT STRING_AGG(x, ',') WITHIN GROUP (ORDER BY x) FROM t",
    "SELECT GETDATE(), SYSDATETIME(), SYSDATETIMEOFFSET(), GETUTCDATE(), CURRENT_TIMESTAMP, CAST(GETDATE() AS date)",
    "SELECT ROUND(kilos, 2), ABS(x), CEILING(x), FLOOR(x), POWER(x, 2), SQUARE(x), SQRT(x), LOG(x), EXP(x), PI(), "
    "STDEV(kilos), STDEVP(kilos), VAR(kilos), VARP(kilos), AVG(CAST(kilos AS float)), MIN(fecha), MAX(fecha), "
    "SIGN(x), x % 2, -x FROM t",
    "SELECT COUNT_BIG(*), APPROX_COUNT_DISTINCT(x), GROUPING(a) FROM t GROUP BY ROLLUP(a)",
    "SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY kilos) OVER (), "
    "PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY kilos) OVER () FROM t",
    "WITH a AS (SELECT especie, SUM(kilos) k FROM t GROUP BY especie) SELECT * FROM a WHERE k > (SELECT AVG(k) FROM a)",
    "SELECT a FROM t UNION ALL SELECT a FROM u",
    "SELECT * FROM t WHERE EXISTS (SELECT 1 FROM u WHERE u.id = t.id) AND x IN (SELECT id FROM v) "
    "AND y BETWEEN 1 AND 2 AND z LIKE 'a%' AND w IS NOT NULL",
    "SELECT t.a, u.b FROM t LEFT JOIN u ON u.id = t.id AND u.activo = 1 CROSS JOIN v",
    "SELECT CAST(fecha AS date) d, COUNT(*) FROM t GROUP BY CAST(fecha AS date)",
    "SELECT t.name, SUM(p.rows) FROM sys.tables t JOIN sys.partitions p ON p.object_id = t.object_id "
    "AND p.index_id IN (0, 1) GROUP BY t.name",
    "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'VIEW'",
    "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'x'",
    "SELECT DB_NAME(), SCHEMA_NAME(), OBJECT_NAME(object_id), OBJECT_SCHEMA_NAME(object_id), OBJECT_ID('dbo.t'), "
    "COL_NAME(object_id, column_id), TYPE_NAME(system_type_id), USER_NAME(), SUSER_SNAME(), CURRENT_USER, "
    "HAS_PERMS_BY_NAME('dbo.t', 'OBJECT', 'SELECT') FROM sys.columns",
]
POSTGRES = [
    "SELECT date_trunc('month', fecha), to_char(fecha, 'YYYY-MM'), extract(week from fecha), fecha::date, now(), "
    "current_date, age(fecha), greatest(a, b), least(a, b), string_agg(x, ','), length(x), position('a' in x), "
    "split_part(x, '-', 1), mod(x, 2), ln(x), log(x), exp(x), stddev_samp(k), var_samp(k), bool_or(k > 0), "
    "array_agg(x), round(k::numeric, 2), date_part('year', fecha), make_date(2026, 1, 1) FROM t",
    "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY k), count(*) FILTER (WHERE k > 0) FROM t",
    "SELECT current_database(), current_schema(), table_name FROM information_schema.tables",
]
MYSQL = [
    "SELECT DATE_FORMAT(fecha, '%Y-%m'), IFNULL(a, 0), IF(a > 0, 1, 0), DATE(fecha), WEEK(fecha), QUARTER(fecha), "
    "DAYOFWEEK(fecha), DATE_SUB(fecha, INTERVAL 1 DAY), TIMESTAMPDIFF(DAY, a, b), NOW(), CURDATE(), "
    "GROUP_CONCAT(x), LOCATE('a', x), CHAR_LENGTH(x), TRUNCATE(k, 2), DATABASE() FROM t",
]
SQLITE = [
    "SELECT strftime('%Y-%m', fecha), date(fecha), datetime(fecha), julianday(b) - julianday(a), ifnull(a, 0), "
    "iif(a > 0, 1, 0), substr(x, 1, 2), instr(x, 'a'), group_concat(x), total(k), typeof(k), printf('%d', k) FROM t",
]
CORPUS = ([(q, "sqlserver") for q in TSQL] + [(q, "postgresql") for q in POSTGRES]
          + [(q, "mysql") for q in MYSQL] + [(q, "sqlite") for q in SQLITE])


@pytest.mark.parametrize("query,kind", CORPUS)
def test_analytic_queries_are_allowed(query, kind):
    assert validate_select(query, kind) == query


@pytest.mark.parametrize("query,kind", [
    ("SELECT * FROM OPENQUERY(srv, 'select 1')", "sqlserver"),
    ("SELECT * FROM OPENDATASOURCE('a', 'b').db.dbo.t", "sqlserver"),
    ("SELECT * FROM OPENROWSET('SQLNCLI', 's';'u';'p', 'select 1')", "sqlserver"),
    ("SELECT xp_cmdshell('dir')", "sqlserver"),
    ("SELECT 1 WHERE a = 1 AND xp_cmdshell('dir') = 1", "sqlserver"),
    ("SELECT CASE WHEN 1 = 1 THEN xp_cmdshell('dir') END", "sqlserver"),
    ("EXEC sp_who", "sqlserver"),
    ("WAITFOR DELAY '00:00:10'", "sqlserver"),
    ("SELECT * INTO copia FROM t", "sqlserver"),
    ("SELECT pg_sleep(10)", "postgresql"),
    ("SELECT pg_read_file('/etc/passwd')", "postgresql"),
    ("SELECT * FROM generate_series(1, 1000000000)", "postgresql"),
    ("SELECT * FROM dblink('host=x', 'select 1') AS t(a int)", "postgresql"),
    ("SELECT SLEEP(10)", "mysql"),
    ("SELECT LOAD_FILE('/etc/passwd')", "mysql"),
    ("SELECT load_extension('x')", "sqlite"),
])
def test_dangerous_queries_are_rejected(query, kind):
    with pytest.raises((PermissionError, ParseError)):
        validate_select(query, kind)
