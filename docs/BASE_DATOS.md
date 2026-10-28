# Modelo de datos

Entidades independientes: Office, Area, Agent, AgentRelation, Provider, Tool, Resource, Connection, Skill, Procedure, Task, Execution, Message, AuditEvent, Artifact, Memory, Approval y Setting.

Asignaciones many-to-many: AgentTool, AgentResource, AgentConnection y AgentSkill. Los permisos se almacenan por asignación de recurso/conexión y capacidad de agente. JSON se utiliza para esquemas de parámetros, configuración de proveedor/herramienta, pasos de procedimiento y contexto de ejecución; las relaciones importantes tienen claves foráneas.

UUID como identificador interno. Número legible de tarea separado. Relaciones restringidas a una oficina, sin ciclos. Memoria aislada por agente y, si corresponde, por tarea. Posiciones visuales persistentes. Secretos referenciados, nunca contraseñas en configuración.

Alembic contiene la migración inicial. `create_all` se admite solo en SQLite de desarrollo/pruebas; producción ejecuta `alembic upgrade head` antes de iniciar.
