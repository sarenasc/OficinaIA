# Diagnóstico del Investigador Deportivo

Fecha local: 9 de octubre de 2026, America/Santiago. Algunos registros corresponden al 10 de octubre UTC.

## Conclusión y alcance

TASK-2026-2259E43A agotó la espera de la primera inferencia del Investigador, antes de ejecutar ninguna herramienta. Independientemente del rendimiento del modelo, el agente no tenía fuentes web utilizables: herramientas registradas, pero ninguna conexión de búsqueda/API ni URL asignada con read.

La solicitud de los últimos 20 partidos oficiales de Colo-Colo **no está resuelta**. No se obtuvieron sus estadísticas ni se generó un análisis ejecutivo. El bloqueo de configuración ahora se detecta antes de inferir, sin aumentar el timeout ni cambiar los modelos del usuario. Las pruebas de transporte y procesamiento con otros datasets no acreditan cobertura de Colo-Colo.

## Auditoría histórica

Tarea: `2259e43a-a19b-41f0-a88b-b96b75d14380`. Investigador: `58296a35-3c16-4e5d-adbe-a7aee698dacd`.

| Ejecución | Proveedor/modelo real | Resultado | Duración | Entrada/salida |
| --- | --- | --- | ---: | --- |
| e85b33e0-c687-40e7-94aa-54261ad2ff44 | anthropic/claude-opus-5-5 | Una delegación al Investigador | 11.843 ms | 9.309 / 1.130 tokens |
| d8e2a405-35b6-4f9a-a34f-9f961940045e | ollama/qwen3:1.7b | Espera agotada, sin respuesta | 300.093 ms | No disponibles |

Los campos históricos de tokens del fallo contienen 0: no representan una medición de cero tokens. La solicitud Ollama era no streaming, por lo que no hubo respuesta final con contadores ni duraciones internas. No es posible separar retrospectivamente carga, evaluación y generación.

Se conservaron Task, Execution, AuditEvent y Message originales. Evidencia: `data/verification/investigator-timeout/historical.json` y `original-prompt.txt`.

Solo existen dos llamadas a modelos y un mensaje Coordinador → Investigador. Los eventos son task.created, task.started, model.completed, model.error y task.error. No hubo web.search, web.fetch, web.download, api.request, reintentos, llamadas adicionales a Ollama ni delegaciones a otros especialistas.

El prompt del Investigador tenía 9.265 caracteres de sistema y 1.332 de solicitud, total **10.597**. Presentaba cuatro herramientas. Distribución del sistema: identidad/instrucciones/reglas 1.906; habilidades 3.058; memoria 19 (vacía); herramientas 1.993; recursos 306; conexiones 15; agentes delegables 23; protocolo y ayudas generales 1.945 caracteres. Incluía instrucciones de Excel, ventas, gráficos y Python, aunque ninguna de esas herramientas estaba asignada al Investigador. Sus instrucciones y dos habilidades repiten procedimientos de investigación, normalización y fuentes. No se borraron instrucciones o habilidades del usuario.

La delegación además pedía devolver 20 objetos de partidos como JSON y prohibía escribir archivos. Esa petición incentiva resultados extensos en la conversación. No hay evidencia de que Ollama llegara a generarlos: es un factor de riesgo, no una causa demostrada por una respuesta inexistente.

## Rendimiento medido y causa

La prueba real HOLA, con el mismo proveedor y modelo configurados, terminó en **84.155 ms**. La llamada al proveedor registró 83.875 ms; Ollama informó total 83.248,44 ms, carga 12.332,21 ms, evaluación del contexto 68.309,62 ms y generación 2.363,09 ms. Entrada: 2.357 tokens; salida: 11. Aproximadamente 4,65 tokens/s de generación.

La evaluación del contexto dominó esa medición. Esto demuestra lentitud de inferencia en una repetición y permite justificar reducir contexto y llamadas. No demuestra qué fase exacta consumió los 300 segundos históricos, ni constituye un benchmark controlado de hardware. La consulta de herramientas también respondió correctamente, pero tardó 183.562 ms.

Se diferencian:

- Timeout de IA: model_timeout; no respuesta final, uso desconocido. No se repite automáticamente una inferencia cuyo resultado no llegó.
- Conexión fallida al proveedor: network_connect, como máximo dos intentos totales; solo se repite ConnectError, antes de enviar la inferencia.
- Interrupción de red o HTTP del proveedor: network/provider_http; no se reenvía automáticamente.
- Herramientas: permiso, argumentos, timeout de herramienta, aprobación o error de herramienta, con su propia ejecución y duración.
- Configuración sin fuentes: research.blocked, antes de llamar al modelo.

## Permisos y fuentes efectivos

Estado previo y restaurado:

| Elemento | Hallazgo |
| --- | --- |
| web.search, web.fetch, web.download, api.request | Asignadas y activas |
| Capacidad internet.access | Asignada |
| Conexiones del Investigador | Ninguna |
| Recursos URL con read | Ninguno |
| Informes, 99380b37-988c-4567-aaa0-dc20b741c5e3 | read/create/modify/delete; carpeta existente |
| Reporte Coordinador, e10bec27-19f4-4079-9d11-89b76348d3ce | read/modify; falta create para nuevos datasets |
| filesystem.read/write en Investigador | No asignadas |
| Delegación | Las cinco relaciones reales parten del Coordinador; no son la causa del timeout histórico |

Una herramienta asignada no concede acceso a cualquier URL ni crea una conexión Brave/API. Las rutas de cada redirección también requieren autorización. La carpeta Informes permite descargas; no permite al Investigador escribir texto con una herramienta que no tiene. Reporte Coordinador no sirve para crear un dataset nuevo con sus permisos actuales.

Fuentes comprobadas:

- [Catálogo de StatsBomb Open Data](https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json): consulta y descarga reales. El catálogo descargado no contiene competiciones con country_name=Chile. Esto no prueba que ningún partido chileno pueda aparecer en una competición internacional; tampoco acredita los últimos 20 partidos oficiales de Colo-Colo.
- [CSV inglés 2025/26 de Football Data](https://football-data.co.uk/mmz4281/2526/E0.csv): descargado realmente, 380 partidos, columnas HC/AC, HS/AS y HST/AST. Es útil para probar procesamiento; no cubre Colo-Colo. La URL tentativa `/new/Chile.csv` devolvió HTTP 404; no se presenta como una fuente válida.
- [Documentación API-Football](https://www.api-football.com/documentation-v3) y [estadísticas de partidos](https://www.api-football.com/news/post/match-facts): documentan córners y tiros a puerta. Es un candidato, pendiente de credencial, liga/temporada, plan y verificación real de todos los campos en los 20 partidos; no se conectó ni se compró un plan.
- [Datasets de Primera División chilena de FootyStats](https://footystats.org/chile/primera-division/datasets): el proveedor anuncia exportaciones y recomienda su API para acceso programático. Eso no garantiza todos los campos, acceso gratuito, ni cobertura de Copa Chile/torneos internacionales. No hay conexión autorizada configurada.

## Correcciones implementadas

1. Preflight genérico de investigación deportiva para agentes con herramientas web: verifica herramientas y capacidades efectivas, URLs legibles, conexiones activas con connect/select y referencias de credencial cuando corresponda, o herramientas de lectura de datos locales/SQL. Tener una ruta posible no implica cobertura; se registra coverage_verified=false. No bloquea al Coordinador por carecer personalmente de herramientas de investigación.
2. El prompt muestra tipo, estado y permisos de recursos/conexiones y las URLs autorizadas. Elimina ayudas de herramientas ajenas al agente, compacta el catálogo JSON y presenta habilidades sin una envoltura JSON adicional. Conserva modelos, contexto configurado, temperatura, instrucciones y permisos. Sistema final del Investigador: **8.693 caracteres**, frente a 9.265, una reducción moderada (~6,2%). Se conservó todo el contenido propio de sus instrucciones/habilidades; no se promete una reducción grande ni una velocidad determinada.
3. Memorias extensas y respuestas extensas de otros agentes se presentan como vistas parciales identificadas; los registros originales siguen en la base. Los previews conservan referencias de recursos/archivos y ejecución. Los datasets completos se guardan mediante herramientas de descarga/API en carpetas autorizadas, y se entregan referencias y resúmenes.
4. web.fetch permite destination para conservar el texto completo como .txt con integridad y artefacto. Devuelve como máximo 2.000 caracteres de vista previa, con advertencia, tamaño y referencia. web.download/API también devuelven dataset_ref con resource_id y ruta relativa. Esquemas, SSRF, DNS público, autorización por redirección, permisos de creación y aprobación de sobrescritura siguen vigentes. La nueva opción requiere reiniciar para actualizar el registro builtin.
5. Telemetría model.started/model.completed/model.error: ID de ejecución, caracteres y número de mensajes/herramientas, duración, uso cuando existe y métricas Ollama. El uso se registra como contadores bajo usage; los secretos siguen redactándose. Los fallos tienen usage desconocido, nunca se presentan como cero tokens medidos. Los eventos de herramientas incluyen duración y categoría de error.
6. Máximo 20 acciones por marco, profundidad 8, 80 acciones totales persistidas por tarea. Se bloquea la cuarta repetición consecutiva de una llamada idéntica exitosa. Las dos correcciones preexistentes de argumentos se conservan; no se reintentan denegaciones de permisos ni escrituras ya iniciadas.
7. Agentes sin subordinados reciben un protocolo que prohíbe delegate. En una prueba real el Investigador confundió el ID de una carpeta con un agente: el motor rechazó la delegación. El cambio de instrucciones no elimina esa comprobación.
8. Solicitudes explícitas de una única herramienta pueden evitar ambas llamadas del modelo:

   ```text
   Ejecuta únicamente la herramienta autorizada: {"name":"python.execute","arguments":{"operation":"sports.group","parameters":{"resource_id":"ID_AUTORIZADO","path":"dataset.csv","group_column":"HomeTeam","value_column":"HC"}}}
   ```

   Se exige ese prefijo y un único JSON completo con name/arguments. El motor pasa por execute_tool y sus esquemas, habilidades requeridas, herramientas/capacidades, permisos, aprobación, cancelación, límites y auditoría. Devuelve únicamente el resultado de ejecución, sin una reescritura numérica del modelo. Un esquema incorrecto falla; no se pide a la IA que lo repare. Las solicitudes abiertas mantienen el flujo normal.
9. Pruebas de timeout/cancelación detectaron una carrera previa del trabajador Windows: el redirector del venv podía crear su intérprete hijo antes de asociarse al Job Object. Ahora el proceso se crea oculto y suspendido, se aplican límites y luego se reanuda. También se espera al hilo de herramienta antes de cerrar/confirmar su sesión al cancelar el worker, evitando commits concurrentes. Referencia: [CREATE_SUSPENDED](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags) y [ResumeThread](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-resumethread).

10. La suite detectó además un bloqueo SQLite al consultar tareas durante commits de auditoría. La base local ahora usa WAL para permitir lectura concurrente con escritura; PostgreSQL no cambia. Se añadió una regresión con un lector de tareas/eventos y un escritor de auditoría en conexiones distintas. Referencia: [concurrencia en SQLite WAL](https://www.sqlite.org/wal.html). No se aumentó el timeout de Ollama ni se desactivaron transacciones.

## Pruebas reales y evidencia

Evidencia principal: `data/verification/investigator-real-8220c63e/verification.json`, su office.db, datasets brutos y normalizados. Los modelos no fueron simulados; las pruebas usan los proveedores/modelos configurados. Los transportes simulados se usan únicamente en pruebas unitarias y se identifican como fixtures.

| Etapa | Resultado observado | Tiempo |
| --- | --- | ---: |
| Solicitud histórica con permisos originales | Bloqueo específico sin inferencia | 46 ms |
| 1. HOLA del Investigador | Texto HOLA real; aceptada | 84.155 ms |
| 2. Herramientas disponibles | Enumeró las cuatro asignadas; aceptada | 183.562 ms |
| 3. Consulta web con permisos originales | Denegada: sin recurso URL | 141 ms |
| Búsqueda con configuración original | Sin conexión de búsqueda activa | 656 ms |
| 4. Descarga con permisos originales | Denegada: sin recurso URL | 203 ms |
| Consulta autorizada en fixture | Texto completo guardado, preview acotado | 610 ms |
| Descarga pública StatsBomb en fixture | Catálogo real y hash comprobado | 218 ms |
| Descarga E0.csv en fixture | 380 partidos reales | 3.172 ms |
| Procesamiento inicial del bruto | Rechazado: más de 100 columnas | 562 ms |
| 5. Procesamiento normalizado real | Agrupación HC por HomeTeam mediante trabajador native | 1.233 ms |
| 6. Delegación abierta inicial | Rechazada: Investigador intentó delegar a un recurso | 43.000 ms |
| Repetición con protocolo sin delegación en hijo | Respuesta HOLA recibida por Coordinador | 61.203 ms |
| 7. Entrega al Analista en lenguaje natural | **RECHAZADA**: respondió cifras sin python.execute | 122.750 ms |
| Operación explícita con JSON mal delimitado | Rechazada antes de herramienta: texto sobrante | 27.235 ms |
| 7. Delegación explícita final Coordinador → Analista → Coordinador | **ACEPTADA**: Python real, 380 filas y 20 grupos, sin inferencia en el Analista | 20.655 ms |
| Procesamiento directo final sin inferencias simultáneas | Agrupación real en native | 483 ms |

El CSV bruto incluye cotizaciones de muchas casas y supera el contrato de 100 columnas del trabajador. La preparación de prueba conserva las 380 filas y proyecta Date/HomeTeam/AwayTeam/HC/AC/HS/AS/HST/AST a E0-stats.csv, sin valores inventados. El original permanece intacto. SHA256 del normalizado: a6de280d6a09e39282a7292d7256d2a9cf34fafac30dc62e504c673544e174d2.

La primera entrega al Analista no es una prueba aprobada aunque Task terminara completed: informó 1.234 filas y otras cifras que no corresponden al dataset. Execution solo contiene modelos, ninguna herramienta. El Coordinador advirtió que los resultados no estaban verificados. Se conserva ese fallo. La repetición explícita final sí está aceptada: Execution registra python.execute del Analista, 1.860 ms de herramienta y 1.812 ms de motor, 380 filas y 20 grupos. Hubo dos llamadas reales a Claude en el Coordinador (4.188 y 8.108 ms), ninguna a Ollama en el Analista; el resto de los 20.655 ms corresponde al motor y persistencia. El Coordinador recibió una vista parcial marcada como tal, sin valores de todas las filas. Una primera formulación añadió texto después del JSON y fue rechazada; el script ahora delimita la acción de delegación completa y no repite el HTTP 404 conocido.

## Incidente del script y restauración

Al reanudar el script, faltó fijar las variables de base aislada. Esa ejecución abrió la base principal y creó cinco tareas VERIFY, recursos URL/carpeta de prueba, asignaciones, una memoria y un job. Se detuvo y archivó la evidencia antes de retirar esos registros exclusivamente de diagnóstico; los archivos de prueba estaban dentro de data/verification.

Se verificó igualdad completa con la copia previa para tasks, agents, providers, resources, agent_resources, connections, agent_connections, agent_tools, agent_skills, agent_relations, memories, messages, executions, audit_events, artifacts y settings. Pruebas: cleanup-verification.json y final-production-verification.json, nuevamente iguales tras completar el diagnóstico aislado. La tarea histórica se conservó intacta. El contrato builtin actualizado de web.fetch forma parte del cambio de código.

El script ahora exige una copia bajo data/verification, establece OFFICE_DATA_DIR/OFFICE_DATABASE_URL en cada entrada (también resume/finish) y comprueba la configuración cargada antes de cualquier escritura. Hay una regresión que rechaza el directorio de producción antes de importar su base. El incidente se informa explícitamente; los resultados durante esa reanudación se conservan como evidencia real con su procedencia, no se presentan como una ejecución totalmente aislada.

## Activación y pendientes

Reiniciar el backend/lanzador para cargar cambios (`npm.cmd run dev:local`). No volver a ejecutar TASK-2026-2259E43A para alterar su historia: crear una tarea nueva.

Falta configurar una fuente que efectivamente entregue fecha, competición, rival, estado finalizado, condición local/visitante, córners, tiros totales y tiros a puerta de ambos equipos en los últimos 20 partidos oficiales de Colo-Colo. Conectar esa API o asignar sus URLs con read; asignar connect/select, credencial cuando corresponda y una carpeta con create/read compartida con el Analista. La configuración final de producción conserva los permisos previos, como acredita la comparación tras restaurar el incidente descrito arriba.

Verificar cobertura en los 20 partidos, orden temporal, duplicados, nulidad, definiciones de métricas, fuentes y fecha de extracción antes de calcular. Si la fuente cubre solo liga, no llamarla “todas las competiciones”. Si faltan campos, detener ese análisis con un bloqueo de datos concreto. No sustituir silenciosamente 20 partidos por una muestra menor ni usar Inglaterra/StatsBomb como prueba de cobertura chilena.

Ollama continúa siendo lento en tareas abiertas. Los límites por caracteres no son un tokenizador exacto; los contadores del proveedor son la medición real cuando existen. El preflight no descubre por sí mismo la cobertura de una API configurada ni garantiza que su credencial siga vigente. No se completó la solicitud real de Colo-Colo, por lo que no se declara resuelto el problema de extremo a extremo.

## Regresiones y comandos reproducibles

`tests/test_investigator_timeout.py` verifica bloqueo antes del modelo, fuentes y permisos efectivos, conservación de instrucciones propias, exclusión de ayudas ajenas, texto web íntegro frente a preview, permisos antes de consultar, conservación de referencias, límite de repeticiones y presupuesto persistido, clasificación de errores y reintento exclusivo de conexión. Incluye rechazo de producción por el script y operaciones explícitas con trabajador Windows real, tanto permitidas como denegadas. Los contratos de red de estas regresiones son transportes simulados; no se confunden con las descargas reales anteriores.

Se ejecutaron también las regresiones existentes de cálculo, ejecución dual, aprobación, cancelación y herramientas. Las primeras suites detectaron archivos temporales bloqueados, commits concurrentes durante cancelación y bloqueo SQLite al consultar tareas; se conservaron esos fallos y se corrigieron el arranque/espera del trabajador y la concurrencia de la base. Ruff pasó. La suite final terminó con **139 pruebas aprobadas y 5 omitidas en 35,88 segundos**. Las omisiones corresponden a Docker no disponible; queda una advertencia existente de deprecación de Starlette/httpx.

```powershell
.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider --basetemp=data/verification/pytest-investigator-wal-final
.venv\Scripts\python.exe -m ruff check backend/app tests/test_investigator_timeout.py scripts/verify_investigator_timeout.py
.venv\Scripts\python.exe scripts/verify_investigator_timeout.py
```

El primer comando usa un directorio nuevo exclusivo de cada corrida. El script crea una nueva copia, exige que no haya tareas activas y prepara un venv solo stdlib para el trabajador de prueba. Ejecuta modelos reales y puede consumir la API externa ya configurada en el Coordinador; no necesita cambiar sus modelos ni concede permisos de producción. Para reanudar se pasa la ruta absoluta de esa copia y --resume o --finish; la guardia comprueba el aislamiento también en esas entradas.
