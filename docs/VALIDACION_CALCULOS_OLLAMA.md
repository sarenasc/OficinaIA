# Validación de cálculos y tiempos de Ollama

Fecha local: 8 de octubre de 2026. Los registros de la tarea están fechados el 9 de octubre en UTC.

## Auditoría de TASK-2026-FC8801FB

Se consultaron los registros reales de `tasks`, `executions` y `audit_events` en `data/office.db`. La tarea original y su resultado histórico se conservaron; las verificaciones posteriores usan copias aisladas de SQLite. No se cambiaron modelos, permisos, asignaciones ni credenciales del proyecto.

Tarea: `fc8801fb-0933-4a91-b5ae-e00100cc9828`. Agente: Analista Deportivo, `6e624bc2-a9bc-4dd9-887d-8a2f219b55a1`.

| Registro Execution | Resultado real | Duración |
| --- | --- | ---: |
| `8cba9702-8488-4377-a62c-086b7cc66750` | Ollama/qwen3:1.7b seleccionó `statistics.mean`, pero agregó `result.sum_total=14` antes de ejecutar Python | 59 985 ms |
| `913ccbe9-d3fb-4834-a160-32b3f6be3827` | Python recibió `[2,1,3,0,4]` y devolvió `count=5`, `sum=10`, `mean=2`, `backend=native`, `worker_pid=23628` | 843 ms |
| `3e2c6598-48bb-435d-bc09-c54c5c8e1f54` | La segunda llamada al modelo volvió a declarar `suma_total=14` y lo atribuyó incorrectamente a la herramienta | 41 703 ms |

Los argumentos efectivos fueron:

```json
{"operation":"statistics.mean","parameters":{"values":[2,1,3,0,4]}}
```

El evento `tool.completed` (`5d1ac360-91e2-4d8a-bc39-94706d08ae3d`) confirma exactamente el mismo resultado correcto que Execution. El tiempo interno del motor fue 781 ms y el de la herramienta completa 843 ms: tienen alcances diferentes.

## Causa raíz

El error numérico nació en el modelo, no en el trabajador Python. El motor de agentes aceptaba propiedades adicionales de la acción, incluyendo un `result` inventado. Después agregaba toda esa acción al historial del asistente. La segunda solicitud contenía tanto el falso `14` como el resultado real `10`; el modelo repitió el falso valor y el motor aceptó esa respuesta final sin comprobarla contra Python.

`model_tool_result` no modificó la suma: para este resultado pequeño devuelve el mismo objeto. La herramienta antigua solo calculaba suma y promedio; mediana y desviación aparecían en la respuesta del modelo sin haber sido obtenidas mediante esa operación. Aunque sus valores coincidían con los correctos, la atribución al trabajador era falsa.

Evidencia completa, redactada, de Execution y AuditEvent: `data/verification/python-model-881a02a4/historical-audit.json`. Se conserva también en la segunda verificación. La tarea original continúa mostrando su error histórico; no se reescribió para aparentar una ejecución correcta.

## Correcciones

1. `canonical_action` valida los campos esenciales de cada acción y descarta las propiedades superiores ajenas al protocolo. No altera los argumentos de la herramienta: estos siguen validándose con su esquema y permisos. Execution conserva la respuesta original del modelo para auditoría; `model.action_sanitized` identifica los campos descartados. El historial solo recibe la acción canónica.
2. `statistics.mean` ahora devuelve `count`, `sum`, `mean`, `median` y `population_stddev`, todos calculados dentro del mismo trabajador real. Usa `statistics.pstdev`, con divisor poblacional N. Para enteros conserva la suma exacta; para decimales usa `math.fsum`. Las validaciones de números finitos, máximo 10 000 valores y magnitud máxima 10^12 se mantienen.
3. Para solicitudes independientes reconocidas de cálculo, el resultado final se serializa directamente desde el resultado exitoso del trabajador. Se incluye herramienta, motor, identificador del trabajo y tiempo real. No se pide al modelo que vuelva a calcular ni reescribir esos números. Si la salida está incompleta, el modelo cambió los valores o intenta responder sin una ejecución comprobada, la tarea falla explícitamente.
4. Las solicitudes explícitas reconocidas también se encaminan directamente a `python.execute`, sin una llamada al modelo para seleccionar una operación conocida. `calculation.routed` y `calculation.verified` registran ambos pasos. Se utiliza `execute_tool` y el servicio de ejecución existentes: herramienta asignada y activa, capacidad `python.execute`, esquema, estados del agente/tarea, cancelación, límites del trabajador, selección del motor y auditoría siguen vigentes. La construcción de instrucciones sigue comprobando herramientas requeridas por habilidades.
5. Para llamadas reales a Ollama se registra en `model.completed` el tiempo observado por la aplicación y las métricas suministradas por el proveedor: carga, evaluación del contexto, generación, total, cantidades y tasa de generación. Los nanosegundos se convierten a milisegundos sin estimarlos.

La selección directa es deliberadamente conservadora: reconoce la solicitud completa de esta auditoría, la prueba «Ejecuta mediante python.execute un cálculo con los goles [...] y calcula su promedio» y «Calcula promedio/suma/mediana/desviación estándar poblacional de [...]». Requiere una única lista JSON numérica válida y una solicitud completa que coincida. Una petición de guardar Excel, consultar SQL, delegar, leer archivos o añadir otros pasos continúa por el flujo normal de agentes. No se promete que cualquier redacción active esta optimización.

Los cálculos operan sobre números; no necesitan acceder a una carpeta. Las operaciones CSV siguen pasando por las autorizaciones de recursos. Código arbitrario continúa exigiendo Docker/aislamiento; la ruta directa no concede permisos nuevos.

## Investigación de latencia

En la tarea original, Ollama consumió 101 688 ms sumando sus dos llamadas, frente a 843 ms de Python. Primera llamada: 3 076 elementos de contexto contabilizados como tokens y 142 generados. Segunda: 3 297 de entrada y 162 de salida. Los registros antiguos no guardaron tiempos internos de Ollama; no es posible separar retrospectivamente carga, evaluación y generación con esos datos.

Se repitió la solicitud original con el agente y Ollama configurados, sobre SQLite aislado, después de incorporar el cálculo completo y evitar la segunda llamada. Evidencia: `data/verification/python-model-881a02a4/verification.json`.

| Medición real en esa repetición | Tiempo |
| --- | ---: |
| Única llamada a Ollama, medida por la aplicación | 81 516 ms |
| Total informado por Ollama | 81 099,7245 ms |
| Carga del modelo | 12 188,0156 ms |
| Evaluación del contexto, 3 102 tokens | 53 486,703 ms |
| Generación, 59 tokens | 15 211,407 ms |
| Python completo / motor interno | 1 250 / 1 203 ms |
| Flujo completo de diagnóstico | 82 968 ms |

La tasa real fue aproximadamente 3,88 tokens generados por segundo. El estado local `/api/ps` mostró `qwen3:1.7b`, contexto 8192 y `size_vram=0`; `/api/version` informó 0.40.1. Esto es compatible con ejecución sin descarga del modelo a GPU, pero no prueba el estado del equipo durante la tarea histórica. La evaluación del contexto fue la fase dominante en la repetición. Estos tiempos no se extrapolan a otros equipos ni se presentan como un benchmark controlado de hardware.

`think=false` para qwen3 ya existía; no explica un cambio introducido aquí. Se conservaron temperatura, contexto, número configurado de hilos y modelo. La mejora principal evita inferencias innecesarias para aritmética explícita, en lugar de aumentar el timeout o quitar comprobaciones.

Con la ruta directa final se repitió otra vez la misma solicitud original y las mismas configuraciones copiadas:

- Resultado: `sum=10`, `mean=2`, `median=2`, `population_stddev=1.4142135623730951`, `count=5`.
- Motor real `native`, `worker_pid=25420`, trabajo `25d904f2-cc5a-4ed6-9a72-87bd90c00b14`.
- Motor interno: 250 ms. Flujo completo: 453 ms. Cero llamadas al modelo; no se simuló una respuesta de Ollama.
- El resultado final coincide exactamente con el resultado de Execution, añadiendo solo el nombre `python.execute`.
- Evidencia: `data/verification/python-model-3371cfb6/verification.json` y su SQLite aislado.

La reducción medida corresponde a esta solicitud; las tareas que necesitan interpretación del modelo conservan sus costos y tiempos de inferencia.

## Pruebas de regresión

`tests/test_calculation_integrity.py` ejecuta procesos reales del trabajador Windows mediante la herramienta registrada. Comprueba las cuatro métricas con `[2,1,3,0,4]`, una lista de longitud par, una sola observación, valores negativos y decimales. Verifica coincidencia entre resultado final, Execution y AuditEvent, y que la transformación de resultados no cambia los números.

También verifica rechazo de listas vacías, booleanos, NaN, infinito y valores fuera del límite; descarte del `14` inventado antes de ejecutar; rechazo de respuestas finales sin herramienta; rechazo de cambio de valores; ausencia de la segunda llamada; ausencia de ambas llamadas en la ruta directa; denegación de capacidad sin devolver un resultado; y conservación del flujo normal para peticiones con otros pasos.

`tests/test_provider_contracts.py` comprueba conversión de duraciones y tasa de generación mediante transporte HTTP de prueba. Estos contratos simulados se distinguen de las verificaciones reales indicadas arriba.

Comandos:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_calculation_integrity.py tests/test_provider_contracts.py -q --tb=short -p no:cacheprovider --basetemp=data/verification/pytest-calculations-routing
.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider --basetemp=data/verification/pytest-calculations-release
.venv\Scripts\python.exe scripts/verify_python_execute_model.py --calculations
.venv\Scripts\python.exe -m ruff check backend/app tests/test_calculation_integrity.py tests/test_provider_contracts.py scripts/verify_python_execute_model.py
```

Las rutas de `--basetemp` deben ser nuevas y exclusivas para cada ejecución. El script clona la base de producción en modo lectura, comprueba que no haya tareas activas y prepara su propio trabajador antes de verificar. No modifica la base original.

Resultado de pruebas específicas: 21 aprobadas. Suite final: 129 aprobadas y 5 omitidas, en 65,89 s. Los cinco casos Docker requieren Docker y la imagen; no se simularon porque no están disponibles. Ruff: sin errores. La advertencia de deprecación de Starlette/httpx no afectó los resultados.

Para activar estos cambios en una instancia ya iniciada, reiniciar el backend de Oficina IA. No volver a ejecutar la tarea histórica para modificar su registro: crear una nueva tarea y contrastar su ejecución con este documento.

Referencia primaria sobre duraciones y campos de Ollama: [API de chat de Ollama](https://docs.ollama.com/api/chat).
