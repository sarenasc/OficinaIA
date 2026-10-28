# Herramientas

Registro genérico con nombre único, descripción, JSON Schema, configuración, permisos requeridos, timeout, estado y ejecutor desacoplado. Activar o desactivar no altera asignaciones existentes. Contratos integrados no se pueden modificar ni eliminar; sí desactivar.

## Implementadas
- filesystem.read: texto UTF-8, 2 MB máximo.
- filesystem.write: crear texto y sobrescribir con modify; SAFE solicita aprobación.
- filesystem.create_directory: crea carpetas dentro del recurso.
- csv.read: UTF-8 BOM admitido, delimitador configurable, hasta 10000 filas/20 MB.
- data.summarize: columnas numéricas, faltantes, cantidad, suma, promedio, mínimo y máximo.
- excel.create: Datos/Resumen, tabla, filtro, panel congelado, formatos, anchos y gráfico de sumas; valida reapertura. No sobrescribe Excel existente.
- excel.read: valores de hojas con límites de tamaño.
- python.execute: Docker efímero sin red, límites y staging. No existe fallback nativo sin aislamiento.
- sql.query: consulta única de lectura, permisos connect/select.
- custom.sql/custom.python: configuración reutilizable asignable a cualquier agente.

Herramientas personalizadas PowerShell, HTTP y programas Windows, PDF, copiar/mover/eliminar archivos y modificaciones avanzadas de Excel: pendientes. El usuario no ve estos tipos como ejecutores disponibles.

## Python
Código recibe montajes `/workspace/<resource_id>`. Scripts trabajan con copias de carpetas asignadas (hasta 50 MB / 1000 archivos cada una). Antes de publicar se comparan cambios y se exige create/modify/delete por archivo; modificación/eliminación en SAFE requiere aprobar script y permisos. Cambios concurrentes en origen impiden publicar. Resultados y archivos se registran. La publicación de múltiples archivos aún no es transaccional; una falla del disco puede dejar una publicación parcial, registrada como error.

## Procedimientos
Pasos JSON: `{agent_id,tool,arguments}`. Referencias completas `$input.nombre` y `$steps.0.rows`, sin eval. Pasos persistidos en la tarea al iniciarla. Aprobación reanuda desde el paso pendiente, sin repetir pasos terminados. Procedimiento determinista no es una respuesta simulada IA.

## Ampliación del 7 de octubre de 2026

Se incorporaron excel.generate_sales, filesystem.list, excel.from_csv, sql.describe, sql.export_excel y social.prepare_post. Consulte [contratos y ejemplos](AMPLIACION_AGENTES.md). Los generadores/exportadores evitan copiar filas al contexto del modelo. social.prepare_post guarda borradores, no publica. SQL conserva lectura; toda publicación futura requerirá aprobación individual.
