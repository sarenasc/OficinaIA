# Estado del proyecto

## Actualización 2026-10-08: Etapa 3 y motor dual

El detalle posterior conserva el hito histórico inicial. Estado actual: Internet/APIs, PDF y SQL parametrizado/escritura aprobada de Etapa 3 están implementados. La arquitectura dual añade `sports.analyze` en un trabajador Windows real, catálogo fijo, Job Object, cancelación y timeout, jobs persistidos y Configuración → Motor de ejecución. Python arbitrario continúa siendo sólo Docker; Docker real permanece sin verificar por falta del entorno. Se conserva Tauri y se prepara entrada/receta del sidecar; instalador autónomo aún pendiente.

Ver [arquitectura dual](ARQUITECTURA_DUAL.md), [pruebas actuales](PRUEBAS_ARQUITECTURA_DUAL.md) y [pendientes del instalador](EMPAQUETADO_WINDOWS.md). No se modificaron credenciales ni asignaciones de agentes existentes en esta fase.

Actualizado: 2026-10-06. Primer hito funcional implementado y probado en modo desarrollo. **El alcance completo de las 20 fases todavía no está terminado.**

## Terminado
- Arquitectura modular, modelo relacional y migración Alembic inicial sin diferencias pendientes.
- CRUD oficinas/áreas/agentes, duplicación, activación, coordinador opcional, relaciones sin ciclos y posiciones persistidas.
- Interfaz React/TypeScript con formularios, React Flow, tareas, aprobaciones, eventos, archivos, consumo y configuración.
- Asignación explícita de herramientas, habilidades, recursos y conexiones por agente.
- Herramientas reales filesystem, CSV, resumen, Excel y SQL de lectura. Excel valida reapertura y contenido.
- Motor serial de tareas persistentes, delegación limitada por jerarquía, mensajes, memoria por agente, aprobaciones y cancelación cooperativa.
- Adaptadores Ollama/OpenAI/Anthropic/Gemini y fallback con políticas never/ask/auto; contratos y políticas probados con fixtures identificados como tests.
- Secretos referenciados: prueba real Windows Credential Manager de escritura/lectura/eliminación temporal exitosa.
- Auditoría y resultados por ejecución, artefactos con descarga autenticada.
- Costos conocidos/desconocidos y desglose total/día/mes/agente/oficina/tarea, zona America/Santiago.
- Procedimientos reutilizables y demo opcional aislada CSV → Excel, eliminable desde interfaz.
- Backup SQLite consistente probado y soporte pg_dump; diagnóstico de servicios.
- Registro de dependencias exactas Python y lockfile npm; auditoría npm sin vulnerabilidades reportadas.

## Implementado parcialmente o pendiente de integración real
- Tauri: shell y ciclo de vida backend preparados. No compilados; falta Rust y el workload C++ de Visual Studio.
- PostgreSQL/Redis/Compose: configuración, migración y servicios escritos. Docker ausente, sin validación operativa.
- Python Docker: aislamiento, staging, cuotas supervisadas y publicación granular implementados; pruebas de contrato pasan, falta ejecución en Docker real.
- SQL Server/PostgreSQL/MySQL: adaptadores implementados; drivers Python instalados. Flujo SQL → Excel verificado con SQLite; falta servidor/driver ODBC y conexión real SQL Server.
- IA real: generación local validada con Ollama/qwen3:1.7b. Las tareas complejas con herramientas dirigidas por modelo y las APIs externas requieren validación adicional. No se llamó a APIs pagadas.
- Windows Runtime: operaciones tipadas para abrir archivo/carpeta de artefactos; no servicio genérico de programas/PowerShell. No se abrieron aplicaciones del usuario durante pruebas.
- Excel: creación/lectura y resumen completos para el primer flujo; modificación avanzada, fórmulas explícitas, validaciones y gráficos arbitrarios pendientes.

## Pendiente
- Instalador `.exe` autónomo con Python empaquetado como sidecar. La fuente Tauri usa actualmente la ruta del checkout.
- Cola Redis distribuida, recuperación automática segura y prioridad en cola normal (inicialmente FIFO).
- Inicio automático de Docker desde interfaz, backups programados y restauración en interfaz.
- Herramientas HTTP, PowerShell y programas locales con autorización estricta; filesystem copy/move/delete y PDF.
- Edición visual de procedimientos, gestión/compartición explícita de memorias, historial paginado y búsqueda.
- Aislamiento adicional contra carreras de paths locales y publicación transaccional de cambios Python.
- Automatización Excel Desktop/Power BI y scheduler se mantienen fuera del alcance inicial según requisitos.

## Verificación
- 39 pruebas backend y 7 frontend; compilación TypeScript/Vite y Ruff correctos.
- Navegador real: instalar demo, ejecutar procedimiento, ver tres pasos, comprobar Excel en disco y renderizar organigrama; sin errores JavaScript de página.
- Alembic upgrade/check en SQLite. PostgreSQL no validado.
- Credencial temporal creada/leída/eliminada en Windows vault; ningún secreto de usuario leído.
- Evidencias reproducibles en `docs/VERIFICACION.md` y scripts de prueba. Artefactos de prueba en `data/verification`, excluidos de Git.

## Errores conocidos y límites
- Starlette advierte que el adaptador TestClient httpx se deprecará; las pruebas pasan.
- Cancelar espera que termine la llamada/herramienta en curso; no revierte archivos.
- Excel existente exige nombre nuevo. No se presenta sobrescritura de Excel como implementada.
- Publicación Python de varios archivos puede ser parcial si falla el disco después de validar permisos.
- Un cierre de escritorio puede interrumpir una ejecución; al reiniciar se marca error y no se repite.
- El módulo SecretStore necesita sesión interactiva Windows; la sesión aislada de pruebas no tenía vault y se verificó con la sesión Windows disponible.

## Decisiones
DEC-001 a DEC-010 documentadas. Backend nativo + contenedores de servicios/sandbox. SQLite exclusivamente para desarrollo. Windows vault sin fallback inseguro. Sin nombres de oficinas ni agentes hardcodeados en lógica de producción.

## Siguiente paso recomendado
Preparar Docker Desktop y Rust + C++ Build Tools; ampliar las pruebas de herramientas dirigidas por Ollama; validar el mismo flujo con PostgreSQL y Python sandbox reales, conectar SQL Server de lectura y empaquetar el escritorio. No considerar las fases 2/3/7/10/12/16/20 cerradas antes de esa integración.

## Git
Repositorio inicializado. Sin commits: no existe autor user.name/user.email configurado. No se inventó una identidad ni se cambió configuración global. Secretos, dependencias y resultados excluidos con .gitignore.

## Ampliación: oficina 2D

Integrada en Agentes: sala SVG, personas animadas según estado real, selección y enlace al detalle existente, arrastre/teclado/X/Y y persistencia con revisión. Duplicar una oficina remapea el plano a sus nuevos agentes. WebSocket autenticado por oficina con heartbeats, reconexión y respaldo REST. Las visitas entre escritorios responden a mensajes y usan rutas que evitan mesas. Los tres pendientes 2D anteriores están terminados. Esta ampliación no cambia los pendientes generales anteriores.

Ollama verificado en este PC: qwen3:1.7b completa una tarea real de saludo en 23,75 s. Proveedor predeterminado asignado y contexto 2048 en los agentes demo. qwen3:4b se conserva instalado; con contexto 8192 agotó la espera en este PC de 8 GB de RAM.

## Ampliación: oficina 3D

Sala Three.js local con escritorios, personajes articulados, cafetera, comedor, sillones y plantas. Agentes disponibles pasean; trabajar los devuelve al escritorio. Selección, cámara y zoom, movimiento reducido, desconexión y alternativa 2D integrados. Renderizado y paseos verificados en navegador WebGL. WebView2/Tauri empaquetado sigue sin validar por las dependencias Windows pendientes.

## Ampliación del 7 de octubre de 2026

Implementadas seis herramientas: excel.generate_sales, filesystem.list, excel.from_csv, sql.describe, sql.export_excel y social.prepare_post. Corrección limitada de argumentos previos a ejecución: hasta dos reintentos, sin reintentar permisos ni operaciones iniciadas. SQL sigue siendo de lectura. Los borradores sociales no publican; conectores y aprobación de publicación por API siguen pendientes.

Prueba real de Ollama: solicitud de 50 ventas seleccionó excel.generate_sales con count=50, 70 tokens de salida y 54,4 s; no incluyó rows y no ejecutó herramientas ni creó archivos del usuario en esa prueba. Las pruebas de herramientas generaron y reabrieron Excel de 50 ventas y comprobaron conversión CSV y cálculo SQL con SQLite. No hay conexión real SQL Server todavía.

Se registraron las herramientas y se asignaron tres de archivos al Generador Reportes existente. Se creó el procedimiento Generar ventas Excel con código para su recurso autorizado. Existe respaldo SQLite anterior a estas asignaciones en data/verification/office-before-expansion-20261007.db.
