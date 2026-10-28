# Herramientas ejecutables — Etapa 3

Todas pasan por execute_tool: asignación, capacidades, JSON Schema estricto, Execution y AuditEvent con errores/duración. Los UUID existentes se conservan; el nombre identifica el contrato estable. El registro actualiza parámetros opcionales de sql.query y metadata config.risk. El riesgo visible es informativo; los permisos y aprobaciones se comprueban en el backend.

| Herramienta | Argumentos principales | Resultado y límites | Capacidad / autorización |
|---|---|---|---|
| web.search | query, max_results=5, language=es, date_range opcional | Título, URL, descripción, fecha disponible, fuente y fecha de consulta. Máximo 20 resultados. Brave Search | internet.access + una conexión web_search activa con connect/select y clave en vault |
| web.fetch | url, timeout=20 (1–60) | URL final, HTTP, texto procesado hasta 20000 caracteres, fecha, errores; cuerpo máximo 10 MB | internet.access + recurso URL asignado con read |
| web.download | url, destination: {resource_id,path opcional}, filename opcional | Ruta, bytes, SHA-256 y verificación. CSV/JSON/XLSX, máximo 10 MB | internet.access + URL read + carpeta create; modify/aprobación para sobrescribir en safe |
| api.request | connection_id, endpoint relativo, method=GET, params={} | URL final, HTTP, JSON y fecha. Sin credenciales en argumentos | internet.access; connect/select para GET, connect/execute para escritura; aprobación siempre para escritura o API privada explícita |
| python.execute | code, resources=[UUID] | stdout/stderr, JSON si stdout lo contiene, montajes y artefactos publicados | python.execute + herramienta asignada + permisos por carpeta |
| python.packages | {} | Versiones de pandas/numpy/scipy/scikit-learn/statsmodels/matplotlib/openpyxl en el contenedor. Nunca instala | python.execute; Docker e imagen preparada |
| filesystem.read | resource_id, path relativo | Texto UTF-8 hasta 2 MB | read |
| filesystem.write | resource_id, path, content | Archivo publicado, bytes, SHA-256 verificado | create; modify y aprobación en safe si existe |
| sql.query | connection_id, query, parameters={}, max_rows=10000 | Registros reales y cantidad; una SELECT de lectura con funciones permitidas | connect/select; límites, timeout SQL y conexión configurada |
| sql.execute | connection_id, query, parameters={} | Operación, tablas, filas afectadas y committed | sql.write + connect/execute + writable_enabled + write_tables; aprobación siempre |
| pdf.create | resource_id, path .pdf, title, paragraphs, tables, charts, images, sources, header, footer | PDF validado, páginas, bytes, SHA-256 | create; lecturas de imágenes read; sobrescritura modify + aprobación safe |
| pdf.read | resource_id, path | Texto por página, metadatos, páginas sin texto, possibly_scanned, ocr_performed=false | read; máximo 20 MB, 200 páginas y 200000 caracteres |
| pdf.merge | resource_id, path, sources=[{resource_id,path}] | PDF combinado validado y hash | read en cada origen; create/modify en destino; máximo 20 fuentes y 200 páginas |
| agents.list | {} | Agentes de la misma oficina, estado y delegatable | Herramienta asignada; no hereda permisos de especialistas |
| tasks.status | task_id opcional | Estado, error y últimos 20 pasos de una tarea de la oficina | Herramienta asignada; no expone contexto interno |

Se conservan filesystem.list/create_directory, CSV, resúmenes, Excel, gráficos, generación de ventas, conversión CSV, sql.describe/sql.export_excel, herramientas personalizadas y borradores sociales existentes. No hay instalación de paquetes ni navegación de navegador automatizada mediante estas herramientas.

## Ejemplos JSON de argumentos

```json
{"url":"https://www.fifa.com/","timeout":20}
```

```json
{"url":"https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json","destination":{"resource_id":"ID-CARPETA","path":"datasets"},"filename":"competitions.json"}
```

```json
{"connection_id":"ID-SQL","query":"SELECT team, SUM(goals) AS goals FROM matches WHERE season=:season GROUP BY team","parameters":{"season":2026},"max_rows":100}
```

```json
{"connection_id":"ID-SQL","query":"UPDATE matches SET goals=:goals WHERE id=:id","parameters":{"goals":2,"id":10}}
```

```json
{"resource_id":"ID-CARPETA","path":"informe.pdf","title":"Informe deportivo","paragraphs":["Resultados calculados con herramientas."],"tables":[{"headers":["Equipo","Goles"],"rows":[["A",5],["B",3]]}],"charts":[{"title":"Goles","labels":["A","B"],"values":[5,3]}],"sources":["Ruta del dataset utilizado"]}
```

Estos valores ilustran argumentos, no resultados deportivos reales. Las herramientas no inventan estadísticas: la IA debe usar datos obtenidos y calculados con herramientas.

api.request admite destination opcional con resource_id y path .json para guardar la respuesta completa sin enviar filas al modelo. Requiere permiso create y un nombre nuevo; no sobrescribe salidas de API para evitar repetir operaciones externas durante una aprobación posterior. Los resultados grandes de herramientas se muestran al modelo como muestras; la auditoría conserva la respuesta completa. Ninguna muestra permite calcular totales del dataset entero.

## Dependencias

Backend: ReportLab, pypdf y Pillow agregados a pyproject.toml e instalados en .venv. Sandbox: versiones fijadas en sandbox/requirements.txt, instaladas solo al construir la imagen. El backend no importa librerías estadísticas para ejecutar código arbitrario. SQL Server requiere pyodbc y ODBC Driver 18 en el equipo; PostgreSQL ya cuenta con psycopg. No se conectaron bases externas.

Fuentes técnicas: [Brave Search API](https://api-dashboard.search.brave.com/api-reference/web/search/get), [parámetros vinculados en SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/connections.html). Se usa transporte HTTP estándar con DNS público fijado y TLS verificado.

## Archivos de esta implementación

- Nuevos módulos: backend/app/tools/network.py, pdf.py, files.py y stage3_builtins.py.
- Backend ampliado: tools/builtins.py, registry.py, sandbox.py, connections.py; agents/engine.py; schemas.py; http/common.py, assignments.py y configuration.py.
- Frontend: components/ExternalConnectionFields.tsx (nuevo), Editor.tsx, SQLConnectionFields.tsx, Assignments.tsx, EntityList.tsx; forms.ts y App.tsx.
- Dependencias/imagen: pyproject.toml, sandbox/Dockerfile y sandbox/requirements.txt (nuevo). Docker Compose existente se reutiliza sin agregar servicios ni sockets.
- Configuración/verificación: scripts/configure-stage3.py, verify-stage3-public.py y verify-stage3-ui.mjs.
- Pruebas nuevas: tests/test_stage3_tools.py, test_stage3_network.py, test_stage3_contracts.py y test_stage3_docker.py.
- Documentación nueva: ETAPA3_AUDITORIA.md, HERRAMIENTAS_IMPLEMENTADAS.md, CONFIGURACION_AGENTES.md, SEGURIDAD_HERRAMIENTAS.md y PRUEBAS_ETAPA3.md. Actualizados README.md, MANUAL_USUARIO.md y AMPLIACION_AGENTES.md.
- Datos de ejecución: perfiles de herramientas añadidos a los seis agentes de la oficina deportiva, preservando asignaciones anteriores; sin nuevas carpetas/conexiones autorizadas. Artefactos/evidencias de prueba se guardan bajo data/verification.
