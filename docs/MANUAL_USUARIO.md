# Manual de Oficina IA

Guía de uso, configuración y ampliación. Actualizada el **7 de octubre de 2026** según los formularios y ejecutores del proyecto. Los nombres de ejemplo se pueden cambiar. Un ejemplo marcado como «pendiente» describe un desarrollo futuro, no una función disponible.

Actualización de **Etapa 3, 8 de octubre de 2026**: internet/API autorizados, PDF, SQL con parámetros y escritura aprobada, paquetes estadísticos de Docker y seguimiento ya tienen implementaciones. [Configuración actual](CONFIGURACION_AGENTES.md), [contratos de herramientas](HERRAMIENTAS_IMPLEMENTADAS.md), [seguridad](SEGURIDAD_HERRAMIENTAS.md) y [resultados de pruebas](PRUEBAS_ETAPA3.md) actualizan las referencias históricas a funciones pendientes en los capítulos siguientes. El vigilante de archivos y los conectores sociales OAuth siguen pendientes.

## Ampliación del 7 de octubre de 2026

Ya están implementadas excel.generate_sales (hasta 10000 ventas), filesystem.list, excel.from_csv, sql.describe, sql.export_excel y social.prepare_post (solo borradores locales). El motor admite dos correcciones de argumentos rechazados antes de ejecutar. Véase [Ampliación de agentes](AMPLIACION_AGENTES.md) para configuración, límites y prioridad SQL Server. Publicar en redes requerirá aprobación por publicación; los conectores siguen pendientes.

## Índice

1. [Qué hace el proyecto](#1-qué-hace-el-proyecto)
2. [Ponerlo en marcha](#2-ponerlo-en-marcha)
3. [Recorrido por la aplicación](#3-recorrido-por-la-aplicación)
4. [Crear oficinas y recursos](#4-crear-oficinas-y-recursos)
5. [Configurar proveedores IA](#5-configurar-proveedores-ia)
6. [Crear un agente paso a paso](#6-crear-un-agente-paso-a-paso)
7. [Herramientas y permisos](#7-herramientas-y-permisos)
8. [Crear y comprobar tareas](#8-crear-y-comprobar-tareas)
9. [Habilidades, equipos y delegación](#9-habilidades-equipos-y-delegación)
10. [Procedimientos repetibles](#10-procedimientos-repetibles)
11. [Crear herramientas](#11-crear-herramientas)
12. [Ejemplos de tareas complejas](#12-ejemplos-de-tareas-complejas)
13. [Caso completo: detectar cambios en Excel y sincronizar SQL](#13-caso-completo-detectar-cambios-en-excel-y-sincronizar-sql)
14. [Errores frecuentes](#14-errores-frecuentes)
15. [Mantenimiento y comprobación](#15-mantenimiento-y-comprobación)

## 1. Qué hace el proyecto

Oficina IA permite organizar agentes que usan un modelo de IA y herramientas autorizadas para trabajar con archivos y datos. La oficina 2D/3D muestra estados reales; los paseos a la cafetería son animaciones ambientales y no ejecutan tareas.

| Concepto | Para qué sirve | Ejemplo |
|---|---|---|
| Oficina | Agrupar un equipo | Oficina de Ventas |
| Área | Organizar agentes dentro de una oficina | Reportes |
| Agente | Definir responsable, instrucciones y modelo | Analista de Ventas |
| Proveedor | Conectar un servicio IA | Ollama o Anthropic |
| Recurso | Identificar una carpeta, archivo u otro destino | Prueba Oficina |
| Herramienta | Ejecutar una operación programada | excel.read |
| Conexión | Identificar una base de datos | SQL Ventas |
| Habilidad | Dar conocimiento e instrucciones reutilizables | Validar ventas |
| Procedimiento | Ejecutar una secuencia definida de herramientas | CSV → resumen → Excel |
| Tarea | Registrar una solicitud y su ejecución | Crear reporte del mes |
| Artefacto | Registrar un archivo producido | reporte.xlsx |

**Un prompt no concede permisos ni implementa funciones.** Registrar una carpeta no autoriza a todos los agentes. Crear una herramienta con un nombre nuevo no programa su ejecución.

### Capacidades y límites actuales

| Capacidad | Estado |
|---|---|
| Crear oficinas, agentes, áreas y relaciones | Disponible |
| Leer y crear texto, leer CSV, leer y crear Excel | Disponible |
| Calcular resúmenes por columna | Disponible |
| Consultar SQL con SELECT | Disponible; depende del servidor y driver |
| Usar Ollama y configurar proveedores externos | Disponible; comprobar cada modelo y credencial |
| Procedimientos, aprobaciones y actividad visible | Disponible |
| Ejecutar Python en Docker aislado | Implementado; requiere Docker e imagen sandbox, integración real por validar |
| Actualizar un Excel existente con excel.create | No disponible; esa herramienta crea archivos nuevos |
| Detectar automáticamente modificaciones de archivos | Pendiente |
| Programar tareas periódicas dentro de Oficina IA | Pendiente |
| Escribir INSERT/UPDATE/DELETE o crear tablas vía sql.query | No disponible; SQL es de lectura |
| Generar ventas ficticias con código | Disponible: excel.generate_sales, hasta 10000 filas |
| Listar carpetas mediante filesystem.list | Disponible, listado limitado sin recursión |
| Controlar Excel Desktop o publicar Power BI | Pendiente |

## 2. Ponerlo en marcha

### Instalación existente: modo local

1. Abre PowerShell en la carpeta del proyecto:

   ```powershell
   Set-Location 'C:\Users\Sergio Arenas\OneDrive\Almahue\Python\Oficina IA'
   npm.cmd run dev:local
   ```

2. Mantén esa consola abierta.
3. Abre `http://127.0.0.1:1420/` y comprueba **Backend conectado**.
4. Para aplicar cambios del backend, detén el lanzador con `Ctrl+C`, ejecútalo de nuevo y recarga la página.

El modo local usa SQLite en `data/office.db`. No requiere Docker para las herramientas integradas de texto, CSV y Excel. Las herramientas Python sí requieren Docker. No inicies Vite por separado: el lanzador entrega la autenticación de la sesión.

### Instalación desde cero

Consulta [Instalación Windows](INSTALACION_WINDOWS.md). Python y Node son necesarios para desarrollo; Docker, Rust y C++ corresponden a las funciones y empaquetado que los requieren. No hay todavía un instalador autónomo final verificado.

## 3. Recorrido por la aplicación

| Pantalla | Uso principal |
|---|---|
| Resumen | Estado y consumo registrado |
| Oficinas / Áreas | Organizar equipos |
| Agentes | Crear agentes, ver la oficina y asignar capacidades |
| Herramientas | Consultar herramientas y crear configuraciones Python/SQL |
| Habilidades | Guardar instrucciones reutilizables |
| Recursos | Registrar carpetas y destinos |
| Conexiones | Configurar bases de datos |
| Proveedores IA | Modelos, endpoints y credenciales |
| Procedimientos | Definir secuencias de herramientas |
| Tareas | Ejecutar, revisar y gestionar solicitudes |
| Auditoría | Investigar eventos y operaciones detalladas |
| Archivos | Consultar artefactos registrados |
| Configuración | Diagnóstico y demo opcional |

En **Agentes**, la actividad aparece **debajo de la oficina**, en tarjetas por persona. Muestra operación actual o última registrada, recurso, archivo, estado y error. **Abrir tarea** lleva al detalle. Si hay desconexión, la información puede estar desactualizada.

En 3D, arrastra para girar la cámara y usa la rueda para acercarte. En **Plano 2D → Editar distribución**, mueve escritorios, ajusta X/Y y guarda. La distribución visual no modifica permisos ni jerarquías.

## 4. Crear oficinas y recursos

### Oficina y área

1. Ve a **Oficinas → + Crear**.
2. Nombre: `Oficina de Ventas`.
3. Escribe una descripción, deja Activo marcado y guarda.
4. Selecciona esa oficina en el filtro superior.
5. Opcional: en **Áreas**, crea `Reportes` para esa oficina.
6. Después de crear un coordinador, puedes seleccionarlo como coordinador de la oficina.

### Carpeta de trabajo

1. Crea o verifica la carpeta en el Explorador de Windows.
2. En **Recursos → + Crear**, completa:

   | Campo | Ejemplo |
   |---|---|
   | Nombre | Prueba Oficina |
   | Tipo | directory |
   | Ruta absoluta o dirección | C:\Users\Sergio Arenas\OneDrive\Almahue\prueba oficina |
   | Descripción | Entradas y reportes de ventas |
   | Activo | Marcado |

3. Guarda. Los recursos de archivo/carpeta deben existir; no se admiten enlaces o junctions.
4. Asigna el recurso a cada agente que lo necesite, con permisos explícitos.

**Diferencia entre las dos rutas:** el recurso guarda la ruta absoluta. Las llamadas de herramientas reciben una ruta relativa dentro del recurso.

| Correcto en una herramienta | Incorrecto |
|---|---|
| ventas26.xlsx | /ventas26.xlsx |
| entradas/ventas.xlsx | C:\Users\…\ventas.xlsx |
| reportes/reporte.xlsx | ../otra-carpeta/reporte.xlsx |

Evita mezclar entrada y salida en el mismo archivo. Para archivos en OneDrive, espera a que estén disponibles localmente y a que termine su guardado/sincronización.

## 5. Configurar proveedores IA

### Ollama

1. Inicia la aplicación Ollama. Si utilizas su servidor de consola, `ollama serve` lo inicia; no abras otro servidor si ya está funcionando.
2. Comprueba modelos:

   ```powershell
   ollama list
   ```

3. Para instalar voluntariamente el modelo usado en esta instalación:

   ```powershell
   ollama pull qwen3:1.7b
   ```

4. En **Proveedores IA**, crea o edita el proveedor local:
   - Tipo: `ollama`.
   - URL: `http://127.0.0.1:11434`.
   - Modelo predeterminado: nombre exacto mostrado por `ollama list`.
5. Pulsa **Probar conexión / modelos**.

El indicador «conectado» confirma disponibilidad, no que toda tarea termine correctamente. En este PC con 8 GB se observaron tiempos de espera en solicitudes largas. La configuración actual usa contexto 2048 en la demo, máximo de generación 2048, espera de 300 s y cuatro hilos por defecto. `OFFICE_OLLAMA_THREADS` permite configurar los hilos; reinicia para aplicar el cambio. Aumentar tokens/contexto no crea memoria adicional.

### Claude / Anthropic

1. Obtén una API key en la consola oficial de Claude y habilita la facturación de API según tu cuenta.
2. En **Proveedores IA → + Crear**:
   - Nombre: `Claude`.
   - Tipo: `anthropic`.
   - URL: `https://api.anthropic.com/v1`.
   - Activo: marcado.
3. Guarda y usa **Configurar credencial** para introducir la API key.
4. Pulsa **Probar conexión / modelos** y copia un identificador disponible al modelo predeterminado.
5. Asigna este proveedor al agente y configura su política externa.

La credencial se guarda en Windows Credential Manager. No la pegues en instrucciones, tareas, configuración JSON ni archivos del proyecto. La prueba de modelos no realiza una generación.

### Política externa y modelos

| Valor | Comportamiento |
|---|---|
| never | Bloquea proveedores externos; apropiado para un agente solo Ollama |
| ask | Pausa para aprobar el uso externo en esa tarea/agente/proveedor/modelo |
| auto | Permite enviar contexto al proveedor externo sin esa pausa |

Un modelo vacío en el agente hereda el predeterminado del proveedor. Si escribes uno, debe ser el identificador exacto. Los agentes delegados tienen su propia política.

Fallback opcional, con identificadores reales:

```json
[{"provider_id":"UUID_DEL_PROVEEDOR","model":"IDENTIFICADOR_DEL_MODELO"}]
```

El fallback reacciona a fallos técnicos; no evalúa por sí mismo la calidad de los datos o de la respuesta. Las tarifas configuradas sirven para estimar consumo; sin tarifa el costo es desconocido.

## 6. Crear un agente paso a paso

Ejemplo: **Generador de Reportes**.

1. Selecciona la oficina.
2. Ve a **Agentes → Crear agente**.
3. Completa los campos:

   | Campo | Valor inicial recomendado para este ejemplo |
   |---|---|
   | Nombre | Generador de Reportes |
   | Área | Reportes, si fue creada |
   | Rol | Analista de archivos de ventas |
   | Objetivo | Leer archivos autorizados y crear reportes comprobados |
   | Proveedor | Ollama local, o el proveedor configurado |
   | Modelo | Vacío para heredar |
   | Temperatura | 0.2 |
   | Contexto máximo | 2048 para la prueba breve local de esta instalación |
   | Modo de ejecución | safe |
   | Política API externa | never para Ollama; ask o auto para Claude |
   | Memoria | off para empezar |
   | Estado | active |

El contexto adecuado depende del modelo y del tamaño de la tarea. Si un archivo o el historial no cabe, divide el trabajo o utiliza un procedimiento; no supongas que el valor inicial sirve para todos los datos.

4. En **Instrucciones del sistema**, pega:

```text
Trabaja únicamente con las herramientas y recursos asignados.
Usa Prueba Oficina como carpeta de trabajo cuando la tarea lo indique.
Lee el archivo antes de describir su contenido.
Usa nombres completos y rutas relativas, sin barra inicial ni ruta absoluta.
Para Excel usa excel.create con resource_id, path y rows; no agregues format.
Para CSV usa filesystem.write con resource_id, path y content, si está asignada.
Si faltan datos o permisos, informa el problema; no inventes resultados.
No reemplaces datos solicitados por filas vacías.
No sobrescribas un Excel existente: utiliza un nombre nuevo.
Confirma creación y ruta solo después de una respuesta exitosa de herramienta.
```

5. En **Reglas**, pega:

```text
Conservar archivos de entrada. No eliminar archivos.
No usar credenciales en instrucciones ni en archivos de salida.
No cambiar identificadores de ventas ni completar importes desconocidos.
Informar las inconsistencias encontradas.
```

6. Guarda.
7. Abre **Herramientas y permisos** y realiza las asignaciones de la sección siguiente.
8. Prueba una tarea pequeña antes de darle un flujo complejo.

### Memoria y modo

- `off`: sin recuerdos adicionales del agente.
- `session`: recuerdos asociados a la tarea.
- `persistent`: recuerdos por agente; el motor incorpora los últimos diez recuerdos persistentes.

La memoria no sustituye un registro fiable de sincronización ni una base de datos. `trusted` no elimina restricciones de recursos, herramientas o conexiones. Los estados de trabajo/espera los establece el motor.

## 7. Herramientas y permisos

### Tres autorizaciones diferentes

1. **Herramienta asignada:** permite pedir una operación.
2. **Recurso o conexión asignado:** permite operar sobre el destino concreto.
3. **Capacidad del agente:** algunas herramientas exigen una capacidad adicional, como `python.execute`.

En **Agentes → Herramientas y permisos**, marca las herramientas, habilidades y permisos de cada recurso/conexión. Guarda las asignaciones.

| Permiso de recurso | Significado |
|---|---|
| read | Leer y acceder a artefactos del recurso |
| create | Crear archivos/carpetas |
| modify | Modificar archivos existentes cuando el ejecutor lo admite |
| delete | Eliminar mediante ejecutores que lo admitan |

Marcar `modify` no hace que excel.create sobrescriba libros. Marcar `delete` no crea una herramienta de borrado.

### Herramientas integradas

| Nombre | Argumentos principales | Uso / límite |
|---|---|---|
| filesystem.read | resource_id, path | Leer texto UTF-8, máximo 2 MB |
| filesystem.write | resource_id, path, content | Crear texto o CSV; sobrescritura requiere modify y aprobación en safe |
| filesystem.create_directory | resource_id, path | Crear subcarpeta autorizada |
| csv.read | resource_id, path, delimiter opcional | Leer CSV, hasta 10000 filas / 20 MB |
| data.summarize | rows | Estadísticas por columna |
| excel.read | resource_id, path | Leer valores de hojas; límites de 20 MB, 10000 filas de datos y 100 columnas |
| excel.create | resource_id, path, rows, summary opcional | Crear .xlsx, hojas Datos/Resumen y validar reapertura |
| sql.query | connection_id, query | Una consulta SELECT permitida, hasta 10000 resultados |
| python.execute | code, resources | Ejecutar código en Docker aislado |

`excel.create` agrega `.xlsx` cuando falta y corrige `.xlxs`; rechaza otros formatos. Para crear CSV usa texto CSV con filesystem.write. Las cadenas que parecen fórmulas se protegen al crear Excel: no uses excel.create para insertar fórmulas ejecutables.

### Asignación de ejemplo

Para Generador de Reportes:

- Herramientas: `excel.read`, `excel.create`, `csv.read`, `data.summarize`, `filesystem.write`.
- Recurso Prueba Oficina: `read` y `create`.
- No necesitas capacidad Python para estas herramientas integradas.
- Añade `modify` solo para operaciones de modificación realmente necesarias y compatibles.

### Conexión SQL de lectura

1. En **Conexiones → + Crear**, elige el motor.
2. SQL Server: completa los campos Servidor o instancia, Base de datos, Autenticación y Driver ODBC. Para dejarlo pendiente, guarda con Activo desmarcado. Cada servidor/base se guarda como una conexión distinta. El equivalente en configuración interna es:

   ```json
   {"host":"SERVIDOR\\INSTANCIA","database":"Ventas","auth":"windows","driver":"ODBC Driver 18 for SQL Server"}
   ```

3. Si usas autenticación con contraseña, configura usuario y credencial por separado. No incluyas password en JSON.
4. Asigna al agente `sql.query` y la conexión con `connect` y `select`.
5. Prueba una consulta pequeña sobre una tabla conocida.

Necesitas conectividad y el driver apropiado. Crear una conexión no crea el servidor ni sus tablas. `custom.sql` conserva las restricciones de lectura: no admite UPDATE aunque su nombre diga «actualizar».

## 8. Crear y comprobar tareas

1. Pulsa **Nueva tarea**.
2. Elige oficina y agente responsable.
3. En Modo, selecciona **Solicitud IA en lenguaje natural** o un procedimiento existente.
4. Describe entrada, destino, operación y cómo comprobar el resultado.
5. Ejecuta y mira **Actividad del equipo**.
6. Si hay una aprobación pendiente, revisa la acción concreta en el detalle de tarea y aprueba o rechaza.
7. Comprueba ejecuciones y archivos reales antes de dar el trabajo por terminado.

### Plantilla de solicitud

```text
Entrada: [archivo exacto] dentro del recurso [nombre].
Operación: [qué calcular, leer o transformar].
Salida: [archivo nuevo y formato] dentro del recurso [nombre].
Reglas: [columnas obligatorias, manejo de errores, conservación de entrada].
Comprobación: [cantidad de filas, campos y resultado esperado].
```

### Primera tarea CSV

```text
Usa filesystem.write para crear ventas_prueba.csv dentro de Prueba Oficina.
Contenido:
id,producto,cantidad,precio_unitario,total
1,Cuaderno,2,1500,3000
2,Lápiz,3,500,1500
No sobrescribas archivos existentes. Devuelve la ruta registrada.
```

### Primera tarea Excel

```text
Crea ventas_prueba.xlsx en Prueba Oficina con cinco ventas ficticias.
Incluye id, fecha, producto, cantidad, precio_unitario y total.
Calcula total como cantidad por precio_unitario. No agregues el parámetro format.
Usa una ruta relativa y confirma la creación con el resultado de herramienta.
```

El modelo escribe estas cinco filas. Para volúmenes grandes utiliza un generador programado; no pidas miles de filas en JSON al modelo.

### Estados

| Estado | Qué significa |
|---|---|
| pending | En cola |
| executing | En ejecución |
| waiting_approval | Esperando una decisión |
| completed | Motor terminado; revisa resultado y artefactos |
| error | Falló una etapa; consulta el mensaje |
| cancelled | Cancelada |

La cola local ejecuta tareas en serie. Cancelar no revierte archivos y puede no detener inmediatamente una herramienta en curso. Una tarea con error puede haber terminado pasos anteriores. Al reiniciar, tareas interrumpidas se marcan como error; no se repiten automáticamente operaciones que pudieron terminar.

## 9. Habilidades, equipos y delegación

### Habilidad reutilizable

En **Habilidades → + Crear**:

- Nombre: `Validar ventas`.
- Procedimiento / conocimiento:

```text
Comprobar que cada venta tenga id único, fecha válida, cantidad positiva
y precio_unitario no negativo. Verificar total = cantidad * precio_unitario.
Informar filas inconsistentes; no corregirlas silenciosamente.
```

- Formato esperado: `Resumen de filas válidas, inválidas y motivo por fila`.
- Asigna la habilidad al agente desde Herramientas y permisos.

Una habilidad aporta instrucciones; no concede herramientas ni acceso a carpetas.

### Equipo de ejemplo

| Agente | Responsabilidad | Asignaciones |
|---|---|---|
| Coordinador | Distribuir trabajo y reunir resultados | Relación directa con especialistas |
| Analista | Leer y comprobar datos | csv.read / excel.read, recurso read |
| Generador Reportes | Crear salidas | excel.create / filesystem.write, recurso create y read |

Conecta al coordinador con los especialistas en el organigrama. El motor permite delegar a hijos directos de la misma oficina y rechaza ciclos. Cada especialista debe tener sus propias asignaciones; no hereda las del coordinador. El coordinador necesita permisos propios si debe leer los artefactos finales.

Instrucción del coordinador:

```text
Delega la validación al Analista. Si hay inconsistencias, informa y detén el reporte.
Si los datos son válidos, pide al Generador Reportes crear un archivo nuevo.
Usa solo agentes delegables y reúne sus resultados comprobados.
```

## 10. Procedimientos repetibles

Un procedimiento ejecuta herramientas en un orden definido y pasa datos entre pasos. Es preferible para conversiones repetidas porque evita que el modelo copie las filas en su respuesta.

### Ejemplo disponible: CSV → resumen → Excel

1. Crea un agente con `csv.read`, `data.summarize` y `excel.create`.
2. Autoriza el recurso de entrada/salida con read y create.
3. En **Procedimientos → + Crear**, selecciona la oficina y escribe `CSV a Excel`.
4. En Pasos (JSON), pega lo siguiente y reemplaza los UUID por los identificadores reales:

```json
[
  {"agent_id":"UUID_AGENTE","tool":"csv.read","arguments":{"resource_id":"UUID_RECURSO","path":"$input.csv"}},
  {"agent_id":"UUID_AGENTE","tool":"data.summarize","arguments":{"rows":"$steps.0.rows"}},
  {"agent_id":"UUID_AGENTE","tool":"excel.create","arguments":{"resource_id":"UUID_RECURSO","path":"$input.output_name","rows":"$steps.0.rows","summary":"$steps.1.rows"}}
]
```

5. Guarda. En Nueva tarea selecciona **Procedimiento: CSV a Excel**.
6. Entradas del procedimiento:

```json
{"csv":"ventas_prueba.csv","output_name":"reporte-ventas-01.xlsx"}
```

7. Ejecuta y verifica los tres pasos y el artefacto final. Usa un nombre de salida nuevo al repetir.

Las referencias deben ocupar el valor completo: `$input.csv` o `$steps.0.rows`. Los índices empiezan en cero. No hay expresiones arbitrarias ni un editor visual de procedimientos todavía. La demo opcional ofrece un procedimiento similar preconfigurado para aprender sin armar sus UUID manualmente.

## 11. Crear herramientas

### Lo que admite la pantalla

**Herramientas → + Crear** ofrece ejecución `custom.sql` o `custom.python`. Campos: nombre técnico, descripción, JSON Schema de parámetros, configuración JSON, permisos necesarios, timeout y activo.

| Tipo | Configuración | Restricción actual |
|---|---|---|
| custom.sql | connection_id y query | SELECT fijo de lectura |
| custom.python | code y resources | Script fijo dentro de Docker sin red |

**Límite importante:** estos ejecutores usan su configuración fija. Declarar `count` en el JSON Schema no lo entrega automáticamente al script; no hay sustitución genérica de argumentos en custom.python/custom.sql. Usa un esquema vacío para una herramienta fija o implementa un ejecutor nativo para parametrizarla.

### Ejemplo: consulta SQL reutilizable

1. Crea y prueba la conexión SQL de lectura.
2. Herramientas → + Crear:
   - Nombre: `ventas.resumen_sql`.
   - Ejecución: `custom.sql`.
   - Descripción: `Resumen de ventas por producto`.
   - JSON Schema:

   ```json
   {"type":"object","properties":{},"additionalProperties":false}
   ```

   - Configuración, adaptando tabla y columnas a tu base:

   ```json
   {"connection_id":"UUID_CONEXION","query":"SELECT producto, SUM(total) AS total_ventas FROM dbo.Ventas GROUP BY producto"}
   ```

   - Permisos necesarios: `[]` (los permisos de conexión se comprueban aparte).
3. Guarda y asigna la herramienta y la conexión connect/select al agente.
4. Solicita: `Ejecuta ventas.resumen_sql y explica el resultado sin inventar columnas`.

### Herramienta Python fija

Requiere Docker Desktop y construir la imagen desde la raíz:

```powershell
docker compose build python-sandbox
```

Configura `custom.python` con `code` y una lista `resources` de UUID autorizados. El script encuentra copias de las carpetas en `/workspace/UUID_RECURSO`. Asigna la herramienta, las capacidades `python.execute` y los permisos de recurso necesarios. El sandbox no tiene red: no sirve como atajo para conectarse a SQL Server. Su publicación de múltiples archivos no es transaccional.

Consulta [Herramientas](HERRAMIENTAS.md) antes de crear un script. No hay fallback de Python sin Docker.

### Agregar una herramienta nativa al proyecto

Para un generador parametrizado o una nueva operación, hay que desarrollar:

1. Su función y límites en `backend/app/tools/`.
2. Su contrato en `backend/app/tools/builtins.py`.
3. Su tipo permitido en `backend/app/schemas.py`.
4. Su despacho en `backend/app/tools/registry.py`.
5. Permisos, auditoría y registro de archivos cuando corresponda.
6. Pruebas de resultado real y rechazo de rutas/permisos inválidos.
7. Nombre legible en la actividad y documentación.

Después de reiniciar, una herramienta integrada nueva se registra y puede asignarse. Cambiar el esquema de una integrada existente requiere una actualización/migración explícita: el registro actual no reemplaza automáticamente contratos existentes.

Herramientas incorporadas y propuestas pendientes (véase la ampliación para los contratos reales):

| Herramienta | Argumentos propuestos | Resultado esperado |
|---|---|---|
| filesystem.list, disponible | resource_id, path | Nombres reales de archivos autorizados |
| excel.generate_sales, disponible | resource_id, path, count, seed opcional | Excel ficticio validado, ruta y cantidad |
| csv.create | resource_id, path, rows | CSV escrito con escape correcto |
| excel.validate_import | resource_id, path, sheet, mapping_id | Validación y referencia a datos preparados |
| sql.upsert_rows | connection_id, mapping_id, batch_id | Escritura controlada, conteos y transacción |

## 12. Ejemplos de tareas complejas

### A. Reporte de ventas a partir de CSV — disponible

Utiliza el procedimiento de la sección 10 para manejar las filas sin pasarlas por el modelo. Después crea una tarea IA breve para interpretar el resumen, si cabe en contexto.

```text
Analiza el resumen del reporte de ventas: identifica columnas con datos faltantes,
explica cantidades y totales, e informa limitaciones. No inventes tendencias
temporales si el resumen no contiene una agrupación por fecha.
```

El resumen integrado calcula por columna; no implementa automáticamente todos los agrupamientos de negocio. Para ventas por mes/producto utiliza una consulta SQL o una transformación programada.

### B. SQL → Excel de ventas por producto — disponible con conexión válida

Agente: sql.query o la consulta custom.sql de la sección 11, excel.create, conexión connect/select y carpeta create/read.

```text
Consulta el total de ventas por producto en SQL Ventas usando la herramienta
ventas.resumen_sql. Crea reporte-productos-01.xlsx en Prueba Oficina con las
filas devueltas. No modifiques la base. Confirma la ruta y cantidad de filas.
```

Para muchos resultados, pasa `$steps.0.rows` de la consulta a excel.create mediante un procedimiento, evitando que la IA reproduzca todos los registros.

### C. Revisar un Excel antes de importar — disponible para una muestra pequeña

```text
Lee entradas/ventas.xlsx en Prueba Oficina. Comprueba que la hoja Datos tenga
id, fecha, producto, cantidad, precio_unitario y total. Informa ids duplicados,
campos vacíos e importes inconsistentes. No modifiques el Excel ni SQL.
Si no puedes analizar todas las filas por límites de contexto, dilo claramente.
```

Para validaciones masivas, implementa una herramienta de validación determinista. El modelo por sí solo no garantiza inspeccionar correctamente miles de filas.

### D. Generar 5000 ventas ficticias — disponible con nueva herramienta

Con excel.generate_sales asignada, la tarea puede ser:

```text
Usa excel.generate_sales para crear ventas-sinteticas.xlsx con 5000 filas
en Prueba Oficina. Usa semilla 123 y marca el archivo como datos ficticios.
Devuelve la cantidad comprobada y la ruta. No escribas las filas en tu respuesta.
```

La herramienta genera las filas con código; el modelo envía solo los parámetros. También se puede ejecutar como procedimiento sin IA. El máximo actual es 10000 ventas.

## 13. Caso completo: detectar cambios en Excel y sincronizar SQL

### Qué significa «crear o actualizar un SQL»

Puede significar generar un archivo `.sql` para revisión o modificar registros de una base SQL. Este caso describe **sincronizar datos de un Excel con una tabla SQL Server**. Crear tablas es una operación distinta: el esquema se prepara una vez por un administrador, no se recrea en cada cambio.

**Estado actual:** puedes crear el agente, asignarle Excel y una conexión de lectura y ensayar una revisión manual. No puedes activar todavía la detección automática ni ejecutar el INSERT/UPDATE desde las herramientas actuales. El diseño siguiente requiere desarrollo adicional.

### Resultado deseado

- Archivo fuente: `entradas/ventas.xlsx` del recurso Prueba Oficina.
- Hoja: `Datos`.
- Destino: `dbo.Ventas` en SQL Ventas.
- Clave de cada venta: `id`.
- Si cambia un id existente, actualizarlo; si es nuevo, insertarlo.
- Si desaparece una fila del Excel, conservarla en SQL por defecto. Borrar requiere una política adicional explícita.
- Si se repite el mismo contenido, no repetir la importación.

### Paso 1. Definir el contrato de datos

| Columna Excel | Columna SQL | Tipo de ejemplo | Validación |
|---|---|---|---|
| id | id | BIGINT | Obligatorio, único y estable |
| fecha | fecha | DATE | Fecha válida; acordar formato |
| producto | producto | NVARCHAR(200) | Texto no vacío |
| cantidad | cantidad | INT | Mayor que cero |
| precio_unitario | precio_unitario | DECIMAL(18,2) | No negativo |
| total | total | DECIMAL(18,2) | Cantidad × precio, redondeo acordado |

Antes de automatizar, acuerda moneda, decimales, hoja, encabezados, zona de fechas y tratamiento de filas vacías. En esta propuesta cualquier fila inválida rechaza el lote completo. No conviertas importes desconocidos a cero.

Si hay fórmulas en el Excel, exige valores calculados y guardados por Excel o calcula los valores en el importador. openpyxl no calcula fórmulas; un valor cacheado puede faltar o estar desactualizado.

### Paso 2. Crear el agente hoy

Nombre: `Supervisor de Importación de Ventas`.

Objetivo:

```text
Revisar el Excel de ventas, informar inconsistencias y supervisar su futura
sincronización con SQL, conservando evidencia de cada lote.
```

Instrucciones utilizables ahora:

```text
Trabaja con entradas/ventas.xlsx dentro de Prueba Oficina.
Lee la hoja Datos y valida las columnas acordadas.
Usa SQL Ventas solo para consultas SELECT autorizadas.
No afirmes que actualizaste SQL: las herramientas actuales son de lectura.
Informa datos inválidos y operaciones pendientes de implementación.
No borres registros, no recrees tablas y no sobrescribas el archivo fuente.
```

Asignaciones actuales: excel.read, sql.query, recurso read y conexión connect/select. Añade filesystem.write y create si debe producir un informe de texto.

### Paso 3. Ensayar el flujo manual actual

1. Prepara un Excel de prueba de cinco filas y una tabla de prueba conocida.
2. Ejecuta una tarea de validación del archivo.
3. Consulta los registros de SQL por los ids de la muestra usando SELECT.
4. Pide un informe de diferencias sin escrituras.
5. Comprueba manualmente el informe. No lo uses como importación automática ni como única validación de un lote grande.

Tarea de ejemplo:

```text
Revisa entradas/ventas.xlsx en Prueba Oficina. Consulta en SQL Ventas los ids
correspondientes a la muestra y prepara un informe de filas nuevas, cambiadas
e inválidas. No ejecutes INSERT, UPDATE o DELETE. Si faltan permisos,
columnas o datos, detén el análisis e informa el motivo.
```

### Paso 4. Implementar un vigilante de archivos

Servicio propuesto, independiente del paseo visual del agente:

1. Observar únicamente el recurso y archivo autorizados; ignorar temporales como `~$ventas.xlsx`.
2. Agrupar eventos cercanos: un guardado puede producir varias notificaciones.
3. Esperar a que tamaño y fecha permanezcan estables entre comprobaciones y que pueda leerse el archivo.
4. Crear una copia consistente y calcular SHA-256. Si cambia mientras se copia, reintentar.
5. Comparar el hash con el último lote **confirmado**; si coincide, no importar.
6. Encolar una tarea de importación con el hash/copia, sin abrir una llamada IA por cada evento.
7. Persistir estado de vigilancia y lotes para reinicios. Evitar importaciones simultáneas del mismo destino.

No basta con comprobar «fecha modificada»: copiar, sincronizar o guardar sin cambiar los datos también modifica fechas. Para OneDrive, contempla archivos bloqueados, disponibilidad local y reemplazo del archivo completo.

### Paso 5. Validar y preparar el lote fuera del modelo

Una herramienta nueva lee todas las filas, valida el contrato y produce un lote preparado. El modelo recibe un resumen: filas válidas/invalidas, columnas y hash. Los registros no deben viajar completos por su contexto.

La comparación y el cálculo de totales deben ser deterministas. Guarda las filas inválidas y sus motivos en un informe. Si el Excel contiene instrucciones escritas en celdas, se tratan como datos, no como órdenes.

### Paso 6. Agregar escritura SQL controlada

Crear un ejecutor específico, por ejemplo sql.upsert_rows. No relajar sql.query para aceptar SQL arbitrario.

El nuevo ejecutor debe:

- Autorizar conexión, tabla y mapeo definidos; no aceptar nombres de tabla arbitrarios del modelo.
- Exigir permisos de escritura propios, todavía pendientes en el proyecto.
- Obtener credenciales del almacén existente.
- Usar parámetros para valores; impedir concatenación de datos en sentencias.
- Cargar un staging validado y ejecutar UPDATE de filas cambiadas + INSERT de nuevas en una transacción.
- Mantener clave única por id y controlar concurrencia de importaciones.
- Revertir todo el lote ante un fallo.
- Registrar hash, origen, conteos y resultado de confirmación.

En modo safe, la aprobación debe estar ligada al lote/hash concreto. Si cambia el archivo después de aprobar, no se importa un contenido distinto bajo la misma aprobación. Para un flujo desatendido futuro, define una autorización específica con tabla, columnas y límites; no basta con cambiar el agente a trusted.

El usuario SQL de este flujo necesitaría SELECT/INSERT/UPDATE sobre las tablas autorizadas, sin DROP ni permisos generales. Preparar tablas puede ser una tarea administrativa separada.

### Paso 7. Confirmar y guardar el estado

En la misma transacción SQL, registra el lote confirmado y su hash junto con las actualizaciones. El estado local se puede reconciliar con ese registro si la aplicación se cierra justo después del commit.

Devuelve un resumen como este **ejemplo de salida futura**:

```json
{"status":"committed","inserted":2,"updated":1,"unchanged":2,"deleted":0,"invalid":0,"source_hash":"SHA256_DEL_ARCHIVO"}
```

Nunca marque el hash como procesado antes del commit. Reintentar un lote ya confirmado debe devolver «sin cambios» y no duplicar ventas. Un error debe dejar evidencia y permitir un reintento controlado.

### Paso 8. Probar antes de activar la vigilancia

| Prueba | Resultado exigido |
|---|---|
| Primer Excel de cinco filas | Cinco inserciones |
| Repetir contenido idéntico | Ninguna importación adicional |
| Cambiar una cantidad y su total | Una actualización |
| Agregar un id nuevo | Una inserción |
| Eliminar una fila del archivo | No borrar en SQL por la política inicial |
| Dos filas con el mismo id | Lote rechazado, base intacta |
| Archivo en proceso de guardado | Esperar; no leer una versión parcial |
| SQL desconectado | Error visible y reintento controlado |
| Fallo en mitad del lote | Rollback total |
| Reinicio después de commit | Detectar lote confirmado, sin duplicados |
| Cambio después de una aprobación | Invalidar aprobación del contenido anterior |
| Dos guardados seguidos | Importar versiones de forma serial o consolidar con política definida |

### Qué verías en la oficina una vez implementado

```text
Supervisor de Importación de Ventas
Detectando cambio en entradas/ventas.xlsx
Validando 1250 filas
Esperando aprobación del lote
Sincronizando dbo.Ventas
Terminado: 20 nuevas, 7 actualizadas, 1223 sin cambios
```

Esos estados son una propuesta para la ampliación. La oficina actual muestra la operación registrada por el ejecutor y sus errores; no inventa fases de una vigilancia inexistente.

### Desarrollo necesario para habilitarlo

| Componente | Trabajo pendiente |
|---|---|
| Vigilante | Eventos, estabilización, hash, copia y reinicio |
| Validador Excel | Mapeo, tipos, claves, fórmulas y lotes grandes |
| Conexiones | Modelo de permisos y escritura parametrizada |
| Importador SQL | Staging, transacción, idempotencia y reconciliación |
| Motor | Encolar por evento, reintentos y bloqueo por destino |
| Interfaz | Configurar vigilancia, aprobar lote, mostrar conteos |
| Pruebas | Casos anteriores y servidor SQL real de prueba |

## 14. Errores frecuentes

| Error | Causa / acción |
|---|---|
| Modelos disponibles: ninguno instalado | Comprobar ollama list, instalar voluntariamente uno y repetir prueba |
| No se pudo conectar con ollama | Iniciar servicio y verificar URL/puerto |
| Tiempo de espera agotado (300 s) | Solicitud lenta; probar menos filas, cerrar programas que consumen memoria o usar un procedimiento/generador |
| Límite de generación antes de completar JSON | Respuesta demasiado larga; no pedir las filas de un lote grande al modelo |
| Contexto excede límite | Reducir datos/historial o pasar resultados entre herramientas en un procedimiento |
| APIs externas prohibidas | Cambiar política del agente responsable/delegado a ask o auto, o usar Ollama |
| El archivo debe tener extensión .xlsx | excel.create no crea CSV; usar .xlsx o filesystem.write para texto CSV |
| format fue inesperado | El modelo agregó un parámetro no admitido; usar el contrato exacto |
| Ruta escapa del recurso | Quitar barra inicial, ruta absoluta o ..; usar nombre relativo exacto |
| Archivo/carpeta no encontrado | Verificar carpeta del recurso y nombre real del archivo |
| Herramienta no asignada | Marcar herramienta en asignaciones del agente ejecutor |
| Conexión no asignada | Asignar conexión con connect/select para lectura |
| El Excel ya existe | Elegir nombre de salida nuevo; excel.create no sobrescribe |
| Docker no está instalado | Python exige Docker; usar integradas o preparar sandbox |
| SQL rechaza UPDATE | sql.query/custom.sql solo admiten SELECT; hace falta nuevo ejecutor de escritura |

Los cambios requieren una nueva tarea; los errores anteriores permanecen como historial. Si un paso ya creó un archivo y otro falló, verifica el artefacto antes de repetir y evita sobrescribirlo por accidente.

## 15. Mantenimiento y comprobación

- Mantén una sola instancia del lanzador en los puertos locales.
- Conserva una copia de la base y de los archivos de trabajo antes de cambios importantes. En SQLite, detén la aplicación antes de copiar archivos manualmente; no confundas exportar un reporte con respaldar la configuración.
- Las credenciales del vault se gestionan aparte: una copia de la base no incluye las claves.
- El costo de Ollama registrado es costo de API local, no electricidad/hardware. Los costos externos dependen de tarifas configuradas.
- La prioridad no proporciona todavía una cola normal ordenada compleja; no uses el orden como garantía de automatización.
- Antes de una tarea grande, verifica un archivo pequeño y un resultado concreto.
- Una tarjeta «completada» de otra tarea no prueba la que estás revisando: usa su identificador y artefactos.

Para desarrollo:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd run test
npm.cmd run build
```

Si Windows bloquea el directorio temporal de pytest, usa `--basetemp` con una carpeta nueva destinada exclusivamente a pruebas; pytest limpia ese destino. No apuntes a una carpeta de trabajo con datos.

### Ruta de aprendizaje recomendada

1. Crear recurso y agente, y escribir un CSV de dos filas.
2. Crear y comprobar un Excel de cinco filas.
3. Ejecutar el procedimiento CSV → Excel.
4. Configurar una conexión SQL de lectura y generar un reporte.
5. Crear habilidades y delegación entre dos especialistas.
6. Usar los generadores y exportadores nuevos; ampliar validadores para lotes grandes.
7. Desarrollar y probar vigilancia + importación SQL antes de habilitar operación automática.

### Documentación del proyecto

- [Instalación Windows](INSTALACION_WINDOWS.md)
- [Agentes](AGENTES.md)
- [Herramientas](HERRAMIENTAS.md)
- [Tareas](TAREAS.md)
- [Proveedores IA](PROVEEDORES_IA.md)
- [Ollama](OLLAMA.md)
- [Seguridad](SEGURIDAD.md)
- [Oficina 2D](OFICINA_2D.md) y [Oficina 3D](OFICINA_3D.md)
- [Arquitectura](ARQUITECTURA.md) y [Estado del proyecto](ESTADO_PROYECTO.md)
- [Power BI: alcance actual](POWER_BI.md)

Este manual documenta el proyecto y un diseño futuro. No crea agentes, vigilantes, tablas SQL ni herramientas nuevas al abrirlo.

## Configuraciones SQL para completar después

En Conexiones hay una configuración inactiva SQL Server — configurar después. Se pueden crear varias desde + Crear; no se realiza una conexión al guardarlas. Completa los campos, configura la credencial aparte si corresponde, activa y luego usa Probar conexión. Asigna cada conexión al agente con connect/select por separado.
