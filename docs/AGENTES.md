# Agentes

Entidad configurable: nombre, descripción, rol libre, objetivo, instrucciones, oficina/área, proveedor/modelo, temperatura, contexto, fallback, reglas, memoria, capacidades y posición. No existen roles de producción predefinidos.

Asignaciones se guardan separadas. Un agente solo ve herramientas, recursos y conexiones propios. Habilidades aportan conocimiento, no permisos. La jerarquía restringe delegación directa; no hay acceso automático a recursos del superior.

Memoria off: sin registros adicionales. Session: asociada a tarea. Persistent: separada por agent_id, últimos diez recuerdos incluidos en contexto. Compartir memoria explícitamente entre agentes y gestión/eliminación desde interfaz quedan pendientes.

Una oficina puede designar coordinador opcional. No se exige jerarquía. Doble clic en nodo edita agente; drag guarda posición. Creación/eliminación de aristas valida oficina y ausencia de ciclos. Agentes working/waiting no se asignan manualmente.

Duplicar oficina copia puestos, áreas, relaciones, herramientas y habilidades. Recursos y conexiones deben autorizarse de nuevo. Historial/procedimientos/memoria no se duplican automáticamente.
