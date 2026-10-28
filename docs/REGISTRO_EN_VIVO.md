# Registro en la ventana del lanzador

La consola que abre `Oficina IA.exe` muestra la actividad en tiempo real, con hora,
nivel, número de tarea y nombre del agente cuando corresponda:

- Inicio y cierre del sistema.
- Tareas creadas, iniciadas, completadas, canceladas o con error.
- Delegaciones y especialista de destino.
- Inicio, finalización y errores de llamadas al modelo y herramientas.
- Bloqueos de investigación, repeticiones sin progreso y aprobaciones pendientes.
- Cambios por la API y peticiones que devuelven un error HTTP.

Las consultas periódicas correctas no se imprimen para mantener el registro legible.
Una llamada al modelo muestra su inicio y, al terminar, su duración; no muestra el
razonamiento interno del modelo ni los prompts o respuestas completos.

La copia persistente se guarda en `data/logs/oficina-ia.log`, junto a los datos de
la aplicación. Cada archivo llega hasta 2 MB; se conservan tres archivos anteriores
(`.1`, `.2`, `.3`). Puedes abrirlos con Bloc de notas incluso después de cerrar la app.
Las credenciales identificables se ocultan. Si no puede escribirse el archivo, el
sistema mantiene el registro en consola y avisa del problema.

Para cargar una actualización, cierra el lanzador y vuelve a abrirlo. Cerrar la
pestaña del navegador no detiene el backend. La auditoría completa por tarea sigue
disponible en la interfaz.
