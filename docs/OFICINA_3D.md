# Oficina 3D: arquitectura

La nueva vista usa Three.js con una cámara isométrica y objetos locales: escritorios, monitores, sillas, personajes articulados, plantas, cafetera, comedor y sillones. No descarga modelos gráficos externos. Convive con el plano 2D y el organigrama.

El snapshot REST/WebSocket existente sigue siendo la fuente de estados y tareas. La distribución de escritorios se reutiliza de Office.visual.floorplan. Seleccionar un personaje abre el panel de agente y sus tareas. La edición y persistencia continúan en la vista 2D.

Un controlador visual determina los recorridos: agentes disponibles pasean a la cafetería, comedor o descanso; working devuelve al personaje a su escritorio; waiting/approval/error/disabled tienen un estado fijo. Los paseos no ejecutan herramientas ni llaman modelos y se identifican como ambientación. Al perder conexión o activar movimiento reducido se detienen. Las rutas evitan escritorios. Los materiales y geometrías se liberan al cerrar la vista.

La cámara permite rotar y acercar con controles de ratón. Si WebGL no está disponible, la interfaz conserva el acceso a la vista 2D. La generación real se verifica independientemente de las animaciones.

## Actividad visible

El panel Actividad del equipo, debajo de la oficina en tarjetas adaptables, muestra todos los agentes sin necesidad de seleccionarlos: operación actual o última registrada, recurso, archivo y error completo redactado. Comparte las actualizaciones WebSocket y el respaldo REST con el plano 2D. Una tarea nueva reemplaza la actividad anterior para evitar mostrar como actual un error histórico. Sin conexión se advierte que los datos pueden estar desactualizados. No expone los mensajes completos enviados al modelo ni los argumentos de las herramientas.

Los argumentos rechazados por el esquema también generan una ejecución `tool.error`, visible en Actividad del equipo. Los mensajes explican la herramienta y el problema sin volcar el esquema completo ni los datos de entrada. `excel.create` no admite `format=csv`; se mantiene la validación estricta.
