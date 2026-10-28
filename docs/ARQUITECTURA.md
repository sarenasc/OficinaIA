# Arquitectura

Tauri 2 aloja React/TypeScript y arranca FastAPI nativo en Windows. El backend se enlaza a loopback y exige un token de sesión generado por el lanzador. El frontend obtiene ese token mediante un comando Tauri. En desarrollo Vite usa el mismo lanzador.

PostgreSQL y Redis funcionan en Docker. SQLite es una alternativa explícita de desarrollo. Windows Credential Manager conserva secretos; PostgreSQL guarda referencias. El backend nativo mantiene la identidad del usuario de Windows. El servicio backend del Compose es una alternativa API para desarrollo Linux, sin integración de credenciales Windows.

Los agentes se configuran en la base de datos. El motor selecciona proveedor, genera llamadas a herramientas, valida asignaciones y permisos, registra eventos y soporta delegación limitada. Las tareas y pasos se persisten. Un procedimiento determinista CSV → resumen → Excel verifica el mismo motor de herramientas sin simular una respuesta IA.

Python generado se ejecuta en un contenedor efímero sin red, usuario no privilegiado, filesystem de sistema de solo lectura, límites de memoria/CPU/procesos y únicamente montajes autorizados. Trusted no elimina la comprobación de asignaciones.

El motor inicial funciona dentro del backend con un trabajador serial. Redis se comprueba como servicio; la cola Redis distribuida queda pendiente. Reiniciar marca ejecuciones interrumpidas como error; no repite automáticamente acciones posiblemente ya realizadas.

## Capas

- `backend/app/models.py`: entidades y relaciones.
- `backend/app/api.py`: REST y progreso WebSocket.
- `backend/app/agents/engine.py`: tareas, delegación y aprobaciones.
- `backend/app/ai/providers.py`: interfaz intercambiable.
- `backend/app/tools/`: registro y ejecutores.
- `backend/app/security/`: recursos y secretos.
- `frontend/`: formularios, organigrama, tareas e historial.
- `src-tauri/`: ciclo de vida Windows.

Referencias: https://v2.tauri.app/reference/config/, https://fastapi.tiangolo.com/advanced/events/, https://docs.ollama.com/capabilities/tool-calling.

## Oficina 2D

La vista SVG reutiliza agentes, tareas y mensajes. WebSocket autenticado y REST de respaldo mantienen el estado; los personajes recorren rutas para representar mensajes. Su plano versionado se guarda en Office.visual; no altera posiciones del organigrama ni permisos. Arquitectura y alcance: [OFICINA_2D.md](OFICINA_2D.md).

## Oficina 3D

Three.js carga bajo demanda la sala y sus personajes. Consume el mismo snapshot autenticado y los mismos escritorios del plano 2D. Un controlador visual permite paseos únicamente a agentes disponibles; working cambia el destino al escritorio. Diseño y límites: [OFICINA_3D.md](OFICINA_3D.md).
