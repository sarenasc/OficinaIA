# Corrección de delegación — oficina deportiva

Fecha local: 2026-10-08. Oficina real en la base: **Analisis deportivas**, ID `65b73f64-36d5-44af-8f57-8ec1c22ec697`.

## Causa raíz

`agents.list`, implementado en `backend/app/tools/registry.py`, consulta relaciones cuyo `source_id` es el agente que llama. Un agente de esa misma oficina devuelve `delegatable=true` si su ID está en esos `target_id` y su estado no es disabled. Ser activo, ser coordinador o tener herramientas no crea por sí solo una relación de delegación.

El coordinador real se identificó desde `Office.coordinator_id`: nombre **Coordinador**, ID `30a0673f-2152-467b-8f8f-61ac93ae195f`. No se creó otro “Coordinador Deportivo”. Los seis agentes estaban active y la oficina estaba activa. No había tareas pendientes, ejecutando o esperando aprobación.

Había cinco relaciones, pero tres apuntaban **especialista → coordinador**. Esto autoriza al especialista a delegar al coordinador, no al revés. Sólo las del Creador y Auditor apuntaban **coordinador → especialista**. Por eso agents.list mostraba exactamente dos delegables.

## Cambios aplicados en la base existente

Se invirtieron estas tres relaciones, conservando sus IDs:

| Relación | Destino del Coordinador | ID del especialista |
|---|---|---|
| `0dac0e27-4398-47a5-b755-d5b0ccd5bd18` | Investigador Deportivo | `58296a35-3c16-4e5d-adbe-a7aee698dacd` |
| `d8414fd0-afb1-4f6f-b81f-7dd9b5e37f9a` | Analista Deportivo | `6e624bc2-a9bc-4dd9-887d-8a2f219b55a1` |
| `7da75e75-dbbe-493e-b8f5-35a10b183e3b` | Gestor de Datos Deportivos | `c62b2dcd-30f3-4dbd-8918-51c275a1d5b8` |

Se conservaron las relaciones con Creador `0b280e98-ed1d-4cbd-9fde-338d09f6c13e` y Auditor `42e5d616-d377-45d4-b4f2-6a8ddd84c494`, y las de la oficina demo. No se duplicaron agentes, no se concedieron capacidades ni recursos, no se cambiaron modelos, proveedores, herramientas, habilidades, reglas o credenciales.

La reparación usa `scripts/correct_sports_delegation.py`: respaldo SQLite, revisión de oficina/estados/tareas, transacción con BEGIN IMMEDIATE, validación de relaciones de la aplicación (misma oficina, sin ciclos), revisión de huellas de tablas protegidas y auditoría. Si algo falla, se revierte la transacción. No se desactivó la validación de ciclos para añadir relaciones opuestas: se reemplazó la dirección incorrecta.

## Comprobaciones ejecutadas

Se ejecutó `agents.list` real mediante el registro autorizado antes y después. La tarea de historial **VERIFY-DELEGATION-26E5D96A** conserva las ejecuciones. Resultado final: los cinco especialistas con `delegatable=true`. Evidencia y respaldo: `data/verification/delegation-20261009T014247Z/correction.json` y `before.db`.

Las huellas de offices, agents, tools, skills, resources, connections, providers y sus asignaciones resultaron idénticas antes/después de cambiar relaciones. Sólo cambiaron las tres relaciones indicadas, más el diagnóstico/historial/auditoría añadidos.

Prueba real al Investigador: **VERIFY-DELEGATE-BC108298**, task `a5a3be17-3cba-42cf-888a-c7d605ecf17f`, completada. El motor registró mensaje Coordinador → Investigador y respuesta Investigador → Coordinador. El Investigador respondió usando Ollama `qwen3:1.7b`; el Coordinador confirmó mediante Anthropic `claude-opus-5-5`. Ambas ejecuciones constan completed, sin errores. No se simularon respuestas.

Prueba real al Analista: **VERIFY-DELEGATE-CB54776E**, task `833e178b-dbc6-4789-b401-cfc8dd851e46`, completada. Mensaje y respuesta reales en ambos sentidos, Ollama `qwen3:1.7b` y Anthropic `claude-opus-5-5`, ambas ejecuciones completed. Evidencia de ambos casos: `data/verification/delegation-probes-20261009T014838Z/probes.json`; nueva lectura de cinco relaciones y agents.list en `persistence.json`.

Al finalizar se comparó otra vez la configuración con el respaldo inicial: los once conjuntos protegidos permanecen iguales (en agentes se excluyen únicamente estado operativo y timestamp, que cambian al ejecutar). Los seis agentes quedaron active y no quedaron tareas activas. Evidencia `configuration-preserved.json` en esa misma carpeta. Los únicos elementos nuevos son tareas, ejecuciones, mensajes, memoria de diagnóstico cuando la política existente la permite y auditorías.

La exportación inicial del primer diagnóstico falló al consultar un nombre de atributo incorrecto en Execution. Se corrigió a provider/model y se reutilizó el historial real completado del Investigador; no se repitió su llamada ni se reemplazó por una respuesta simulada.

Los diagnósticos envían una acción delegate explícita usando el mecanismo real de acciones pendientes del motor. Esto comprueba autorización, envío, ejecución del especialista, respuesta e historial. No demuestra que el modelo del coordinador decida autónomamente esa primera delegación. Los proveedores y modelos son los existentes; no se sustituyeron por mocks. Las pruebas breves no solicitan archivos, búsquedas, Python ni SQL.

Persistencia: `scripts/verify_delegation_restart.py` arrancó, cerró y volvió a arrancar un backend real sobre una copia SQLite de la oficina existente, en puerto 18021. En ambos arranques se ejecutó agents.list mediante un procedimiento real y se confirmaron cinco relaciones y cinco delegables. Evidencia: `data/verification/delegation-restart-1bbbeab0/verification.json`. La ventana/backend del usuario no se interrumpió.

Regresión aislada: `tests/test_delegation_configuration.py` aprobada. Reproduce tres relaciones invertidas y dos correctas, corrige dirección y comprueba cinco delegables. Verifica además rechazo de ciclos, agentes disabled no delegables y rechazo de relaciones entre oficinas. No usa modelos ni modifica la base de uso diario. Ruff aprobado en los scripts de esta corrección.

## Capacidad de ejecutar trabajo: bloqueos separados

En el momento de inspección, ningún especialista tenía conexiones asignadas. El Investigador tiene las cuatro herramientas web/API y carpetas autorizadas, pero no recursos URL asignados ni conexión Brave/http_api. Por ello una investigación real necesita esa configuración adicional. No se concedió automáticamente.

El Analista tiene Python/Excel/archivos asignados y Ollama instalado; Docker no está disponible para `python.execute`. La operación fija Windows `sports.analyze` requiere asignación y capacidad propias que no se añadieron en esta corrección. Los archivos Excel pueden procesarse con sus herramientas autorizadas si el archivo solicitado existe y las rutas son relativas válidas.

Gestor y Auditor tienen sql.query, pero no conexión SQL asignada; una consulta real sigue necesitando conexión y permisos. Creador tiene herramientas de archivos/Excel/PDF y carpetas asignadas; crear o modificar un archivo sigue sujeto a permisos y aprobaciones existentes.

Estos bloqueos no alteran `delegatable`: la relación permite enviar la tarea, y cada especialista conserva sus propias restricciones para ejecutarla. No se verificó una investigación deportiva ni un análisis estadístico completo en estos diagnósticos.

El texto generado por el Coordinador afirmó que el análisis completo podría retomarse. Esa afirmación del modelo no comprueba las conexiones/Docker: el diagnóstico sólo validó mensajes y respuestas; para una investigación/análisis completos siguen vigentes los bloqueos de configuración enumerados arriba.

## Uso y prevención

Pulsar **Actualizar** para volver a cargar relaciones/listado de la oficina. En el organigrama, dibujar la flecha desde el agente que delega hacia quien recibe: Coordinador → Especialista. No hace falta reiniciar la aplicación para leer estas relaciones persistidas. Evitar recrear las flechas en sentido inverso.

El organigrama muestra flechas azules ampliadas y puntos que recorren el camino desde source_id hacia target_id. Naranja indica que el destinatario tiene estado working; gris discontinuo corresponde a un extremo disabled. La animación azul representa dirección autorizada, incluso sin una tarea en curso. Una leyenda aclara ambos significados. Se respeta la preferencia del sistema para reducir movimiento ocultando los puntos y conservando las flechas. La visualización no modifica relaciones ni permisos.
