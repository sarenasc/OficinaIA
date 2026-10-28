# Ejecución Windows nativa

## Preparación e inicio

Desde la raíz del proyecto, preparar el trabajador gestionado:

```powershell
.venv\Scripts\python.exe scripts/setup_native_worker.py
npm.cmd run dev:local
```

El script crea `data/runtime/native-venv` usando el Python de desarrollo y sin pip ni descargas. No instala software global. Los cálculos disponibles utilizan csv, statistics y math de la biblioteca estándar. No se anuncian pandas, SciPy o matplotlib como instalados en este modo. Es un entorno de dependencias, no un sandbox.

Si se utiliza AppData: preparar con `--data-dir "$env:LOCALAPPDATA\OficinaIA"` e iniciar `.venv\Scripts\python.exe scripts/launch.py --local --user-data`. Ese modo usa una base separada; no traslada automáticamente los agentes del checkout.

En Configuración → Motor de ejecución elegir Automático o Windows nativo y pulsar diagnóstico. Se muestran versión real del trabajador, biblioteca estándar, herramientas compatibles, trabajos, disponibilidad y errores. No se instala nada desde el diagnóstico. Reiniciar el lanzador antiguo es necesario para cargar los endpoints y herramientas nuevos.

## Configurar el agente

### Usar la misma herramienta python.execute

Si el Analista ya tiene python.execute asignada y esa capacidad, conservar su configuración. Reiniciar el lanzador para cargar el contrato nuevo y elegir auto o native en Configuración → Motor de ejecución. No cambiar Ollama ni el modelo. No se interpreta código libre como una operación permitida: pedir expresamente operation/parameters.

Promedio sin Docker, argumentos exactos:

```json
{"operation":"statistics.mean","parameters":{"values":[2,1,3,0,4]}}
```

Prompt sugerido: “Usa python.execute con operation statistics.mean y parameters values [2,1,3,0,4]. No envíes code ni resources. Informa el promedio y el motor de la respuesta real de la herramienta”. Para verificar sin depender del modelo, poner esos argumentos en un paso de procedimiento con herramienta python.execute.

También se verificó el prompt natural original con el Analista y qwen3:1.7b reales sobre una copia: el agente seleccionó statistics.mean y obtuvo 2.0 del worker. La selección puede seguir siendo lenta en Ollama; el procedimiento directo elimina esa espera. Los tiempos observados y evidencia están en PRUEBAS_ARQUITECTURA_DUAL.md.

Las llamadas de agente mantienen el formato habitual:

```json
{"type":"tool","name":"python.execute","arguments":{"operation":"statistics.mean","parameters":{"values":[2,1,3,0,4]}}}
```

Otras operaciones, reemplazando el UUID por un recurso asignado:

```json
{"operation":"csv.create","parameters":{"resource_id":"UUID","path":"partidos.csv","rows":[{"equipo":"A","goles":2},{"equipo":"A","goles":4},{"equipo":"B","goles":1}]}}
```

```json
{"operation":"csv.read","parameters":{"resource_id":"UUID","path":"partidos.csv"}}
```

```json
{"operation":"sports.group","parameters":{"resource_id":"UUID","path":"partidos.csv","group_column":"equipo","value_column":"goles"}}
```

csv.create requiere crear; si el destino existe también requiere modificar y aprobación en modo safe. csv.read y sports.group requieren lectura. No se amplían permisos por elegir el motor. csv.create genera el contenido en el worker y el backend lo publica con SHA256 y artefacto; protege cadenas que podrían convertirse en fórmulas al abrir el CSV en Excel. Los valores numéricos negativos siguen siendo números.

Promedio: entre 1 y 10000 números finitos, magnitud hasta 1e12. CSV lectura/creación: hasta 1000 filas, 30 columnas, celdas de 2000 caracteres y resultado serializado de 512 KB. Agrupación deportiva conserva 10000 filas, 100 columnas y 200 grupos. Entradas de archivos hasta 20 MB. Los resultados incluyen motor y tiempo; el PID del worker permite comprobar que es otro proceso.

### Compatibilidad con sports.analyze

1. Agregar `"sports.analyze"` a Capacidades (JSON), conservando las capacidades que ya tenga.
2. En Herramientas y permisos asignar `sports.analyze`.
3. Asignar un recurso carpeta con lectura. Agregar crear si se guardará un resultado JSON nuevo.
4. Usar un CSV UTF-8 con encabezados, una columna de equipo/grupo y otra numérica no negativa.
5. Para prescindir completamente de Ollama, crear un procedimiento con un paso de herramienta y ejecutar ese procedimiento.

Ejemplo de argumentos (reemplazar el UUID):

```json
{"resource_id":"UUID-recurso","path":"partidos.csv","group_column":"equipo","value_column":"goles","output_path":"resumen-goles.json"}
```

Ejemplo CSV: `equipo,goles` con filas `A,2`, `A,4`, `B,1`. Devuelve cantidad de filas, y por grupo: cantidad, suma, media, mínimo, máximo y probabilidad de cero de una distribución Poisson con esa media. Es una estadística descriptiva parametrizada; no es un modelo predictivo validado. No inventa partidos.

`output_path` es opcional y requiere un nombre nuevo terminado en .json. El resultado se publica mediante el mecanismo existente de integridad y artefactos. Para gráficos o Excel usar después `excel.create`/`excel.chart`; PDF continúa disponible con `pdf.create`. No se sobrescriben resultados deportivos existentes.

## Límites y cancelación

CSV hasta 20 MB, 100 columnas, 10000 filas y 200 grupos. Valores finitos entre 0 y 1000000. Dos trabajos simultáneos; límite Windows de 512 MB por trabajo y máximo dos procesos (redirector del venv e intérprete). Timeout de la herramienta, salida hasta 1 MB; sin parámetros de código, paquetes, URL o comandos.

Cancelar desde la tarea activa envía un evento al trabajador. Se cierra el Job Object, se termina el árbol y se limpia el staging antes de publicar resultados. El polling es de 50 ms, sujeto a planificación del sistema. Las credenciales, variables Python, proxies y token de sesión no se heredan en el trabajador. Tras reiniciar, un trabajo incompleto aparece interrumpido; no se repite.

Se añadió terminación explícita del Job Object y espera de procesos activos para evitar que el intérprete hijo aún mantenga abiertos stdout/stderr al limpiar temporales. Referencias: [TerminateJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject), [contabilidad de procesos del Job Object](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information).

Limitaciones: requiere Windows y un Python base disponible para el venv de desarrollo. No ofrece token restringido, bloqueo de red por SO ni aislamiento de la cuenta del usuario. Por eso sólo admite el catálogo de operaciones revisadas y bloquea cualquier código arbitrario. Si Windows no permite aplicar los límites, el trabajador falla de forma explícita.
