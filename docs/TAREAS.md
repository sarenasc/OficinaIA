# Tareas

Solicitudes se convierten en tareas con UUID y número legible TASK-año-identificador. Oficina, responsable, prioridad, solicitud, resultado, error y fechas persistentes. Participantes, herramientas, archivos, modelos, tokens y tiempos se derivan de ejecuciones y mensajes relacionados.

Estados reales: pending, executing, waiting_approval, completed, error, cancelled. planning reservado para evolución del plan. Motor serial local; prioridad solo ordena pendientes recuperadas al iniciar, la cola inicial normal es FIFO.

Solicitudes IA usan marcos persistentes de contexto. Delegación únicamente a agentes conectados como hijos directos en la misma oficina. Conversación interna registrada y visible. Procedimientos usan pasos de herramientas y referencias de datos; resultados reales se conservan por paso.

SAFE pausa acciones críticas, guarda aprobación y reanuda sin repetir pasos terminados. Rechazar cancela. Cancelación es cooperativa: no revierte archivos ni interrumpe inmediatamente una herramienta en curso. Un cierre marca tareas en curso como error al reiniciar; no repite operaciones posiblemente terminadas.

Progreso por WebSocket y consulta REST. Historial muestra lo recibido, resultado, herramienta/modelo y tiempo de cada ejecución. Artefactos vinculados a tarea, agente y recurso; descargar o abrir desde Windows requiere que el agente conserve permiso read. El runtime bloquea apertura de programas/scripts como artefactos.

No scheduler complejo, recuperación automática de tarea interrumpida ni cola Redis distribuida en esta versión. Cola en memoria se recupera para tareas aún pending; estado/resultados permanecen en base.

## Aprobaciones visibles

Un aviso Aprobaciones pendientes aparece en las pantallas para las tareas de la oficina seleccionada. Revisar aprobación abre el detalle antes del historial. Allí se puede ver la acción exacta y pulsar Autorizar esta tarea o Rechazar. La selección no autoriza automáticamente ninguna acción.
