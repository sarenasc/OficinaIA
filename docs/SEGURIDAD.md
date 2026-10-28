# Seguridad

Backend restringido a loopback, token de sesión obligatorio, orígenes permitidos y WebSocket autenticado en primer mensaje. Token nunca aparece en query string. Sin permisos globales implícitos. TRUSTED no concede acceso adicional por sí mismo.

Credenciales: Windows Credential Manager mediante WinVaultKeyring. En otros sistemas no hay fallback texto plano. Referencias UUID en base, API solo expone has_credential. Configuración JSON rechaza claves sensibles; logs redactan claves y patrones comunes. No incluya secretos en prompts, nombres, SQL o scripts; la redacción no puede reconocer todo texto arbitrario.

Filesystem exige recurso activo asignado, permiso específico y ruta relativa. Bloquea rutas absolutas, traversal, ADS, symlinks y junctions. No constituye una frontera contra otro proceso hostil con la misma identidad Windows que modifique rutas durante una operación; ese endurecimiento adicional está pendiente.

Python: contenedor sin red, usuario no privilegiado, root read-only, capacidades eliminadas, no-new-privileges, 512 MB RAM/1 CPU/64 procesos, tmpfs 64 MB, timeout y límites de trabajo. No se monta socket Docker. Scripts trabajan en staging; cambios publicados tras validar permisos. No se descargan imágenes automáticamente (`--pull never`). Las cuotas de staging se supervisan periódicamente, no son cuotas de disco del kernel.

SQL: parseo estructural, una Query, sin DML/DDL/INTO ni funciones fuera de allowlist. PostgreSQL/MySQL usan transacción read-only; SQLite URI mode=ro; SQL Server requiere cuenta/rol con SELECT únicamente. Timeouts por motor todavía no equivalentes. Probar conexión no cambia datos.

Se impiden cambios de configuración durante tareas activas. Datos de archivos y modelos son no confiables. Un prompt malicioso nunca reemplaza autorización del servidor. Límite de pasos y profundidad limita bucles/costos, no garantiza calidad del modelo.

APIs externas usan HTTPS oficial y política never/ask/auto. La autorización ask permite enviar el contexto de la tarea a ese proveedor/modelo; puede incluir datos leídos de recursos autorizados. Ollama admite únicamente endpoint local y filtra nombres cloud reconocibles. Garantía de desconexión total requiere además mantener Ollama en modo local y controlar red del host.
