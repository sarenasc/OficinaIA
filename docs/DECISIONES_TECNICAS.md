# Decisiones técnicas

## DEC-001 — Tauri y backend nativo
Respeta la elección del requisito. Python nativo permite credenciales Windows y archivos del usuario. PostgreSQL/Redis y scripts no confiables se aíslan con Docker. Requiere Rust y herramientas de compilación para empaquetar.

## DEC-002 — SQLAlchemy y PostgreSQL, SQLite de desarrollo
Un mismo esquema relacional permite pruebas sin Docker. SQLite no sustituye la validación operativa PostgreSQL. Migraciones con Alembic para producción.

## DEC-003 — Windows Credential Manager
Keyring con backend WinVault explícito en Windows. En otros sistemas la configuración de secretos está deshabilitada antes que recurrir a almacenamiento inseguro. La base conserva únicamente UUID de referencia.

## DEC-004 — Ejecución persistente serial inicial
Un worker local limita concurrencia y reduce carreras. Estado durable y eventos consultables. Cola Redis y recuperación automática quedan para una evolución; nunca repetir operaciones al reiniciar sin autorización.

## DEC-005 — Mínimo privilegio desde el primer flujo
La seguridad condiciona toda herramienta. No aplazar permisos hasta fase 19. No ejecutar Python/PowerShell generados directamente en Windows. Herramientas personalizadas solo implementan los tipos efectivamente soportados.

## DEC-006 — Proveedores externos y fallback
Política `never`, `ask` o `auto` por agente. La aprobación autoriza únicamente proveedor/modelo de esa tarea. Fallos de transporte permiten fallback; no se afirma medir automáticamente la calidad semántica.

## DEC-007 — Python con staging
No montar carpetas Windows directamente con escritura. El script opera sobre copias limitadas. Al terminar se detectan cambios y se valida create/modify/delete antes de publicar. SAFE autoriza antes el script que pueda modificar/eliminar. Ventaja: permisos granulares y trazabilidad. Límite: copia adicional y publicación todavía no transaccional.

## DEC-008 — Backups y Windows Runtime tipados
Backup SQLite usa sqlite3.backup; PostgreSQL usa pg_dump con argumentos fijos. Operaciones Windows aceptan identificadores de artefactos y validan rutas/extensiones, nunca comandos arbitrarios. Crear backup, descargar, abrir archivo o ubicación son acciones explícitas de interfaz.

## DEC-009: Oficina 2D integrada

React y SVG locales representan los agentes ya persistidos. El plano se almacena en Office.visual.floorplan con revisión concurrente, separado del organigrama. La vista usa WebSocket autenticado con snapshot inicial y respaldo REST; pausa las animaciones sin conexión. Las rutas por cuadrícula representan intercambios registrados de mensajes y evitan escritorios. No añade otro motor de tareas.

## DEC-010: Oficina 3D y rendimiento local

Three.js se carga bajo demanda y construye geometrías locales sin servicios gráficos externos. Reutiliza plano y estados; los paseos son ambientación exclusiva de agentes disponibles, sin trabajo ficticio. El modelo predeterminado de la demo se ajustó a qwen3:1.7b con contexto 2048 tras observar presión de memoria y timeouts en 4b. Las excepciones HTTP tienen mensajes legibles; el motor conserva sus permisos y protocolo de acciones.
