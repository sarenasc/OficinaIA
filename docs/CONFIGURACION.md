# Configuración

Todas las oficinas/agentes/áreas se crean desde interfaz. Puede configurar conexiones, recursos, habilidades, procedimientos y herramientas personalizadas. Identificadores UUID visibles permiten relacionar configuraciones avanzadas.

Variables: OFFICE_DATABASE_URL, OFFICE_DATA_DIR, OFFICE_OLLAMA_URL, OFFICE_REDIS_URL y OFFICE_SANDBOX_IMAGE. El lanzador genera OFFICE_SESSION_TOKEN; no es una API key y no se versiona. SQLite se selecciona expresamente con `--local`.

Recursos: ruta absoluta existente. Asignación a agente: read/create/modify y otros permisos previstos. Las herramientas implementadas solo usan capacidades reales; permisos de copiar/mover/ejecutar se reservan para herramientas futuras. Python staged aplica read/create/modify/delete por archivo.

Política externa por agente: never (prohibida), ask (aprobar proveedor/modelo para la tarea), auto (permitida). SAFE exige aprobación de sobrescrituras y scripts capaces de modificar/eliminar. TRUSTED conserva asignaciones y validación de rutas.

Configuración avanzada de conexión en JSON. SQL Server: `{"host":"SERVIDOR","database":"Produccion","auth":"windows","driver":"ODBC Driver 18 for SQL Server"}`. Para usuario/contraseña: auth=password, username y contraseña separada mediante Configurar credencial. PostgreSQL/MySQL: host, database, username, port. SQLite: path absoluto de una base existente.

Backups manuales desde interfaz disponibles; programación y restauración desde interfaz pendientes. PostgreSQL: use pg_dump/pg_restore según documentación de su versión. SQLite: copie office.db con aplicación cerrada. Las credenciales del vault no forman parte de ese backup.

## Varios servidores SQL

Conexiones guarda registros separados por servidor/base, con credenciales y asignaciones propias. El formulario SQL Server permite completar campos sin editar JSON. Las configuraciones nuevas se guardan inactivas por defecto, incluso incompletas; no se conecta al guardar. Para activar se exige servidor, base y usuario si la autenticación es SQL, además de puerto válido cuando se especifica. Una conexión inactiva no se prueba ni se usa en herramientas. La contraseña se configura aparte en Windows Credential Manager.
