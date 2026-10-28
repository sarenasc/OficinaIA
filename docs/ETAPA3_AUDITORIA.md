# Etapa 3 — auditoría antes de implementar

Fecha: 2026-10-08. Proyecto inspeccionado: Oficina IA.

## Arquitectura encontrada

- Backend Python/FastAPI en backend/app. SQLAlchemy persiste agentes, tareas, ejecuciones, aprobaciones, memoria y artefactos. La instalación local usa data/office.db (SQLite); Docker Compose también permite PostgreSQL.
- Frontend React/TypeScript/Vite en frontend, puerto local 1420. API autenticada con token de sesión en 127.0.0.1:38080. Escritorio Tauri y lanzador Windows scripts/launch.py.
- docker-compose.yml ya define PostgreSQL, Redis, un perfil opcional container-api y la imagen de análisis python-sandbox. El backend local no requiere Docker; ejecutar Python de agentes sí.
- Registro en tools/builtins.py, despacho y auditoría en tools/registry.py. Los IDs UUID de herramientas existentes se conservan. Los nombres contractuales identifican la capacidad.
- AgentTool, AgentResource, AgentConnection y AgentSkill separan las asignaciones. resource_path comprueba permisos, límites de ruta y deniega junctions/symlinks.
- agents/engine.py ejecuta JSON de acciones, delegación jerárquica sin ciclos y pausas reanudables por aprobación. Execution y AuditEvent conservan respuestas, errores y duración.
- Importaciones JSON de agentes y habilidades tienen vista previa y creación transaccional. La importación de agentes no concede acceso a recursos; la de habilidades no asigna permisos ni herramientas.

## Implementaciones reutilizables

filesystem.read/write/list, Excel, CSV, sql.query de lectura, sql.describe, SQL → Excel y python.execute ya tienen implementaciones reales. SQL Server admite configuraciones múltiples e inactivas y credenciales de Windows Credential Manager. La ejecución Python ya prepara copias de recursos y usa contenedor sin red, usuario 10001, CPU/memoria/PIDs limitados, timeout y publicación controlada de artefactos. La imagen actual solo tiene pandas, openpyxl y xlsxwriter.

## Faltantes detectados

Internet/API configurables y SSRF, paquetes estadísticos y consulta de versiones, parámetros SQL y escritura aprobada, PDF, validación de dependencias de habilidades, perfiles por agente y documentación integral de herramientas/riesgos. El modelo Tool guarda permisos y config pero no un campo risk: se usará metadata de config sin alterar tablas.

## Disponibilidad inicial

Docker no está disponible en PATH al comenzar esta etapa. Bibliotecas PDF/estadísticas no están instaladas en el entorno del backend. No hay credenciales de búsqueda/API deportiva ni servidores SQL reales configurados. La oficina deportiva existe y sus seis agentes están creados. No se conectarán bases externas automáticamente. Se verificarán integraciones locales y se separarán pruebas de contrato, servicios de prueba y pruebas reales contra servicios disponibles.

## Decisión de implementación

Ampliar módulos existentes y añadir módulos de red/PDF, sin reemplazar el motor ni el CRUD. Conservar compatibilidad de esquemas antiguos con parámetros nuevos opcionales. Conexiones HTTP/búsqueda y recursos URL serán opt-in, con destinos públicos explícitos; las escrituras SQL requerirán aprobación incluso en modo trusted. Las herramientas nuevas se asignarán por rol exclusivamente a la oficina deportiva, sin conceder conexiones ni carpetas nuevas.
