# Activar las herramientas en Oficina IA

## Reinicio

Tras actualizar, detén el lanzador con Ctrl+C y ejecuta `npm.cmd run dev:local` desde la raíz. El registro conserva IDs y muestra las herramientas nuevas. Si la interfaz nueva devuelve Not Found, el servidor sigue usando código anterior.

## Perfiles de la oficina deportiva

scripts/configure-stage3.py agrega herramientas por rol únicamente a la oficina deportiva y conserva asignaciones previas. Se aplicó durante esta implementación. No concede recursos ni conexiones nuevas y no cambia las relaciones existentes.

| Agente | Nuevas herramientas | Capacidad adicional |
|---|---|---|
| Investigador Deportivo | web.search, web.fetch, web.download, api.request | internet.access |
| Analista Deportivo | python.execute, python.packages, filesystem.read | python.execute |
| Gestor de Datos Deportivos | filesystem.read/write, sql.query | Ninguna escritura SQL automática |
| Creador de Archivos Deportivos | filesystem.read/write, pdf.create/read/merge | Conserva herramientas Excel previas |
| Auditor Deportivo | filesystem.read, sql.query | Python solo si ya está autorizado explícitamente |
| Coordinador / Coordinador Deportivo | agents.list, tasks.status | Delegación nativa del motor, sin herramientas privilegiadas heredadas |

Conecta las relaciones desde Coordinador hacia los especialistas. La acción JSON `delegate` existente ejecuta y espera al hijo, con historial persistido; no se añade una herramienta ficticia de delegación. Selecciona al coordinador en Oficinas → Editar si deseas usarlo por defecto.

## Autorizar páginas y datasets

1. Recursos → Crear → tipo url. Ruta: `https://www.fifa.com/`, o una ruta concreta de dataset público.
2. Agentes → Investigador → Herramientas y permisos: asigna ese recurso con read.
3. Asigna la carpeta de destino con read/create; modify solo si requiere modificar archivos y con modo safe.
4. Ejecuta web.fetch o web.download. Cada redirección debe seguir dentro de URLs autorizadas; no se accede a otras páginas implícitamente.

No se crearon estos accesos automáticamente. Internet no implica permiso para todo el equipo ni para todos los sitios. external_policy controla las llamadas a proveedores IA; el acceso web/API usa la capacidad internet.access y sus autorizaciones separadas.

## Búsqueda y APIs deportivas

Conexiones → Crear:

- Motor web_search: proveedor Brave Search. Guarda el registro inactivo, configura su clave con Configurar credencial y actívalo. Asigna una única conexión de búsqueda al Investigador con connect/select. web.search requiere esa clave; no existe búsqueda gratuita simulada ni scraping de resultados.
- Motor http_api: URL base de la API, autenticación bearer/header/none, cabecera de clave opcional y rate limit. Guarda la credencial en el botón separado, activa y asigna connect/select. Los endpoints son relativos a esa base; no incluyen secretos. POST/PUT/PATCH/DELETE requieren connect/execute y aprobación, incluso trusted.
- allow_private es una excepción explícita solo para una API configurada; cada tarea requiere aprobación y queda limitada a esa procedencia. Por defecto se bloquean localhost, redes privadas y metadatos. No se envían credenciales por HTTP sin TLS.

Probar conexión de HTTP/búsqueda valida configuración sin consumir API ni realizar una llamada de red. Para verificar acceso real usa api.request/web.search desde un agente autorizado. Puede haber costos según el proveedor contratado. Ninguna clave deportiva fue inventada ni configurada.

## Python y Docker

Instala y abre Docker Desktop con contenedores Linux. Luego:

```powershell
docker compose --profile sandbox-build build python-sandbox
```

La imagen oficina-python-sandbox:local incluye pandas, numpy, scipy, scikit-learn, statsmodels, matplotlib, openpyxl y xlsxwriter. python.packages informa versiones y faltantes. No se ejecuta pip durante tareas de agentes.

Asigna carpetas concretas con read/create. El código las usa como `/workspace/UUID-DEL-RECURSO`; la salida devuelve esa correspondencia. Las carpetas se copian a un staging y solo se publican cambios autorizados y comprobados. En safe, modify/delete requiere aprobación. No montes todo C:. No se monta Docker socket en el contenedor del agente.

El backend nativo Windows usa la CLI Docker del equipo. El perfil container-api no incluye Docker socket ni puede lanzar el sandbox por sí solo: usa el backend nativo para python.execute. No se publica ningún puerto del sandbox. PostgreSQL/Redis opcionales conservan sus volúmenes existentes y puertos solo en loopback.

## SQL

Conexiones múltiples existentes se conservan; activa cada una después de configurarla. Para lectura, asigna connect/select y sql.query; usa `:nombre` con parameters.

Para escritura, configura writable_enabled=true, write_tables (lista de tablas exactas, con esquema si aplica), write_operations (insert/update/delete) y max_write_rows (por defecto 1000). En SQL Server hay campos visuales para habilitar escritura y tablas; SQLite/PostgreSQL usan el JSON existente. Asigna sql.execute, capacidad sql.write y connect/execute únicamente al agente autorizado. Toda operación espera aprobación; UPDATE/DELETE necesitan WHERE; DDL, funciones y subconsultas de escritura no se habilitan. El usuario SQL real debe tener privilegios mínimos. Una operación que supera el límite de filas se revierte.

## Habilidades

required_tools guarda IDs; importar JSON permite nombres y los resuelve a IDs. Las habilidades no otorgan herramientas ni recursos. Antes de llamar al modelo, el motor verifica que todas las herramientas requeridas estén asignadas y activas; informa los nombres faltantes y bloquea la tarea. JSON antiguos siguen funcionando. No se asignaron habilidades nuevas automáticamente.
