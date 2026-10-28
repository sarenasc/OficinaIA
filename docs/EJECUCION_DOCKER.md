# Ejecución Docker

Instalar e iniciar Docker Desktop por separado. La aplicación no lo instala ni inicia silenciosamente.

```powershell
docker compose --profile sandbox-build build python-sandbox
npm.cmd run dev:local
```

En Configuración → Motor de ejecución seleccionar Docker o Automático. Diagnóstico verifica el daemon/imagen `oficina-python-sandbox:local`. La disponibilidad de Docker no se deduce únicamente de encontrar el ejecutable.

`python.execute` conserva el contrato `{"code":"...","resources":["UUID"]}` y la capacidad del mismo nombre. `custom.python` también requiere este aislamiento. `python.packages` consulta versiones del contenedor; no instala paquetes. `sports.analyze` puede ejecutar el mismo código fijo en Docker, con el mismo formato de parámetros y resultados.

Ahora python.execute también acepta `{"operation":"statistics.mean","parameters":{"values":[2,1,3,0,4]}}`, sports.group, csv.read y csv.create. En modo docker esas operaciones usan el catálogo fijo dentro del contenedor. No puede mezclarse code con operation. En auto/native las operaciones fijas pueden usar Windows; code/resources sigue requiriendo aislamiento Docker. Sin Docker el error de código libre recomienda el contrato parametrizado, sin ejecutar ni traducir el código en la cuenta del usuario.

Los resultados de ambos contratos incluyen backend, job_id y duration_ms. Las operaciones fijas leen archivos sólo desde recursos autorizados y csv.create publica con los controles del backend. Las herramientas existentes SQL/web/Excel/PDF no cambian.

Se conserva usuario 10001, raíz de sólo lectura, red deshabilitada, sin capacidades, no-new-privileges, 512 MB, una CPU, 64 procesos y tmpfs de 64 MB. No se monta el socket Docker. Los únicos recursos son copias temporales de carpetas autorizadas; antes de publicar se revisan cambios, permisos y que el origen no haya cambiado. El modo safe conserva sus aprobaciones para modificación/eliminación. Por ello un análisis Docker sobre un recurso con permisos de escritura puede pedir aprobación previa; usar recurso de sólo lectura cuando no necesite escribir.

El timeout y la cancelación de tareas ahora también se comprueban durante el proceso Docker y antes de publicar. El finally elimina el contenedor temporal y cierra el cliente. Si Docker falta, no se ejecuta código en Windows como alternativa. El perfil backend container-api carece de Docker socket: la ejecución Docker desde ese perfil necesita otra arquitectura de servicio y no se considera habilitada.

Si el daemon no responde durante la limpieza, se conserva el error/cancelación original y se deja una advertencia en el log; no se garantiza eliminar un contenedor contra un daemon inaccesible. Revisar esos contenedores tras recuperar Docker. El cliente local se cierra igualmente.

Bibliotecas fijadas en `sandbox/requirements.txt`: pandas, numpy, scipy, scikit-learn, statsmodels, matplotlib, openpyxl y xlsxwriter. Mantener y reconstruir la imagen al actualizar versiones revisadas. Docker no estaba disponible en el equipo de esta implementación; las pruebas reales de contenedor permanecen omitidas explícitamente.
