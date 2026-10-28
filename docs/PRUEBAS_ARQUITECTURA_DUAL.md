# Pruebas de arquitectura dual

## Corrección del contrato único python.execute — 2026-10-08

La auditoría confirmó que python.execute sólo aceptaba code/resources; el motor Windows previo funcionaba con sports.analyze, pero no resolvía esa llamada. Se agregó operation/parameters a la misma herramienta. Modelos y asignaciones de producción conservados; pruebas en base aislada, sin resultados inventados por un modelo.

Pruebas específicas reales: **16 passed**, 23,90 s. Cubren promedio calculado por otro proceso, CSV creado/leído/agrupado, artefacto con SHA256, auditoría y duración persistidas, escapes/unassigned resources, código arbitrario nativo bloqueado, mezcla de contratos/operaciones desconocidas rechazadas, aprobación de sobrescritura y protección de fórmulas CSV. Incluyen las pruebas previas de timeout/cancelación y selección del motor.

Suite completa actual: **112 passed, 5 skipped**, 55,82 s (`data/verification/pytest-python-fixed-complete`). Las cinco omisiones corresponden a las pruebas reales Docker. Frontend: 9 pruebas aprobadas, TypeScript/Vite build aprobado; continúa la advertencia previa de tamaño del chunk 3D. Ruff aprobado. Chromium verificó selección, diagnóstico, operación específica, motor y duración; es un contrato de UI con fixture y sin escrituras de producción, no una simulación del cálculo. Captura `data/verification/dual-execution-ui.png`.

Comprobación real por HTTP, sin Ollama ni Docker, en puerto 18019 y con reinicio: `data/verification/dual-startup-5281aaae/verification.json` y `calculations.json`. statistics.mean procesó [2,1,3,0,4]: count=5, sum=10, mean=2 (numéricamente 2.0), backend=native, worker_pid=27832, duration_ms=250. El CSV partidos.csv fue generado por csv.create, leído por csv.read y agrupado por sports.group (grupo A: suma 6, promedio 3.0). Los resultados, artefacto, preferencia y jobs persisten tras reiniciar. El PID es del proceso lanzado para el trabajador; no es una afirmación de cálculo del modelo.

Prompt original con modelo real: `scripts/verify_python_execute_model.py` probó “Ejecuta mediante python.execute un cálculo con los goles [2,1,3,0,4] y calcula su promedio” sobre una copia SQLite, con el Analista Deportivo y su configuración existentes. **Completada**, Ollama/qwen3:1.7b sin mocks ni cambio de modelo; el agente eligió statistics.mean y python.execute devolvió backend=native, mean=2, sum=10, count=5, worker_pid=28420, duration_ms=1296. La ejecución completa de herramienta figura con 1375 ms. Evidencia `data/verification/python-model-6a0d0055/verification.json`, tarea de copia `VERIFY-PYTHON-MODEL-876B9C36`. No se escribió en la base de producción.

Límite observado: el modelo tardó 72953 ms en elegir la acción y 17688 ms en producir el final. El motor ya no requiere Docker para este cálculo, pero esta corrección no acelera Ollama. Un procedimiento directo evita las dos llamadas al modelo cuando la operación y parámetros ya se conocen. El test exige una ejecución real de python.execute con resultado 2.0; una respuesta del modelo sin herramienta no se considera aprobada.

Se detectó un fallo real de limpieza al cancelar: el intérprete hijo podía conservar abiertos los logs y producir WinError 32. Se corrigió terminando el Job Object y esperando que sus procesos terminen antes de limpiar. La segunda ejecución aprobó las pruebas de cancelación/timeout. También se ajustó una aserción de prueba a la redacción existente de escapes; no se relajó el control de rutas.

Docker no disponible: se prepararon pruebas reales para promedio fijo, cuotas CPU/memoria de cgroup y cancelación sin publicar, además de generación de artefactos y timeout anteriores. Se omiten si no existe daemon/imagen; no se declaran aprobadas ni se ejecuta código libre en el host como sustituto. Selección explícita docker en pruebas que consultan paquetes del contenedor.

Se utilizan bases y recursos de prueba separados de `data/office.db`; no se modifican agentes, conexiones, credenciales o permisos del usuario.

## Verificaciones ejecutadas

- Suite completa final: **106 passed, 2 skipped** (48,76 s). Incluye los 94 casos previos, 11 nuevos del motor dual y un caso adicional de limpieza Docker con timeout. Las dos omisiones son Docker real por falta del entorno. Directorio `data/verification/pytest-dual-complete-final-20261009`.
- Suite específica ampliada: **11 passed** (11,82 s), incluyendo selección auto real, paquetes y cancelación desde el endpoint de tareas sin publicar archivo.
- Windows real: venv gestionado, proceso independiente con Job Object, análisis de CSV, archivo JSON/artifact verificado, preferencia persistente y estados finalizados en Settings.
- Windows real: timeout y cancelación terminan el proceso; no quedan trabajos activos. Un worker de espera se usa sólo como fixture de prueba, jamás como entrada disponible para agentes.
- Python arbitrario bloqueado en native; en auto permanece Docker y falla explícitamente cuando éste no existe. Denegación de rutas y capacidades; validación de valores finitos/columnas; entorno del worker sin secretos.
- Diagnóstico real del worker preparado: Python **3.12.14**, biblioteca estándar, operación sports.analyze.
- React/TypeScript/Vite: build exitoso. 9 pruebas del frontend aprobadas. Advertencia previa por tamaño del chunk 3D, sin error de compilación.
- Chromium: selección de motor, estados, paquetes y diagnóstico visibles; fixture de UI, sin cambiar preferencia de producción. Captura `data/verification/dual-execution-ui.png`.
- Arranque/reinicio real del sidecar desde fuente, por HTTP en puerto 18019 con datos separados: agentes/habilidades persistidos, CSV procesado sin modelo, JSON verificado, preferencia y trabajo conservados al reiniciar, cierre del árbol. Evidencia `data/verification/dual-startup-01b2d344/verification.json`. No es prueba de un EXE compilado.
- Ruff aprobado en backend y scripts nuevos. La limpieza Docker se reforzó para intentar siempre cerrar el cliente y preservar errores/cancelación si la eliminación del contenedor falla; deja advertencia de log cuando no puede confirmar eliminación.
- La suite conserva Excel, PDF, SQLite, carga de agentes/habilidades, rutas y delegación de Etapa 3. La delegación usa un proveedor de respuestas de prueba y herramientas reales; no se afirma una llamada real a un modelo comercial.

Se detectaron y corrigieron dos fallos mediante ejecución real: límite inicial de un proceso incompatible con el redirector del venv Windows, y mutación in-place JSON que impedía persistir el estado final. El límite es ahora dos procesos y se reasigna un JSON nuevo al terminar.

## Repetir

```powershell
.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider --basetemp=data/verification/pytest-dual-NUEVO
npm.cmd test -- --run
npm.cmd run build
```

Usar un nombre nuevo para basetemp, dedicado a pruebas; pytest puede limpiar ese directorio. Las pruebas Windows se omiten en otro SO. Las pruebas reales Docker necesitan daemon e imagen construida.

## Pendientes explícitos

Docker real (no disponible), SQL Server real (no configurado), compilación/arranque de sidecar EXE y ventana Tauri instalada (faltan herramientas y runtime portable), prueba de actualización/desinstalación en máquina limpia. No se cuentan como aprobadas. La preparación AppData no copia datos existentes ni se considera una migración probada.
