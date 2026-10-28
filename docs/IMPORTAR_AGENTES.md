# Crear varios agentes desde un archivo JSON

En **Agentes → Importar JSON**, selecciona la oficina de destino y descarga la plantilla. Edita el archivo con cualquier editor de texto, cárgalo, pulsa **Validar y ver agentes** y revisa la vista previa. Pulsa **Crear agentes** para guardar el lote completo.

La oficina debe existir antes. Si un agente es inválido, no se crea ninguno. No se reemplazan agentes existentes: los nombres y claves del lote deben ser únicos. Se admiten hasta 100 agentes por archivo, con tamaño máximo de 2 MB en el selector. Importar no ejecuta tareas ni llama a proveedores IA.

Si omites position, la importación asigna puestos separados en el organigrama. Las tarjetas de agentes previamente importados con posiciones iguales también se separan al mostrarse. Selecciona la oficina en el filtro superior para ver su organigrama.

Ejemplo:

```json
{
  "version": 1,
  "coordinator": "coordinador",
  "agents": [
    {
      "key": "coordinador",
      "name": "Coordinador",
      "role": "Coordinador de tareas",
      "goal": "Organizar solicitudes y verificar resultados",
      "instructions": "Delega el análisis al Analista. No inventes resultados.",
      "delegates": ["analista"],
      "mode": "safe",
      "external_policy": "never"
    },
    {
      "key": "analista",
      "name": "Analista",
      "role": "Analista de datos",
      "goal": "Analizar datos reales",
      "tools": ["filesystem.list", "excel.read", "excel.chart"],
      "context_limit": 8192,
      "temperature": 0.2,
      "memory_mode": "off"
    }
  ]
}
```

- `key`: identificador dentro del archivo; la aplicación genera el ID real.
- `coordinator`: clave del agente que será coordinador de la oficina. Opcional. Si ya existe un coordinador, omite este campo para conservarlo.
- `delegates`: claves de los agentes del archivo a los que puede delegar. No se permiten ciclos.
- `tools`: nombres exactos de herramientas ya existentes y activas.
- Los demás campos son los del formulario de agentes: description, role, goal, instructions, rules, provider_id, model, temperature, context_limit, mode, external_policy, fallbacks, permissions, memory_mode, status, position y area_id. Los ID de proveedor y área deben existir; el área debe pertenecer a la oficina seleccionada.
- `office_id` puede omitirse: se utiliza la oficina elegida en el diálogo. Si se incluye, debe coincidir.

La plantilla deja proveedor y modelo pendientes para que elijas los que tienes configurados. Puedes añadir `provider_id` con el ID de tu proveedor existente y `model` con su nombre exacto para configurarlos desde el archivo. No incluyas contraseñas ni claves API. Los recursos, conexiones y habilidades se asignan después mediante **Herramientas y permisos**; no se copian permisos de otros agentes.

Después de importar, verifica proveedor/modelo y asignaciones antes de crear una tarea. Si vuelves a importar el mismo archivo, se rechazan los nombres duplicados.

API local autenticada: POST `/api/offices/ID/agents/import?preview=true` valida sin guardar. Con `preview=false` valida nuevamente y crea el lote dentro de una única transacción.
