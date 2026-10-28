# Ampliación de agentes y herramientas

Actualizada el 7 de octubre de 2026. Prioridad acordada: Excel, después SQL Server y análisis. Toda publicación en redes requiere aprobación individual del usuario.

## Capacidades entregadas

| Herramienta | Resultado | Argumentos |
|---|---|---|
| excel.generate_sales | Excel ficticio de 1 a 10000 ventas, totales calculados y marcado como sintético | resource_id, path, count, seed opcional |
| filesystem.list | Archivos y carpetas reales, sin recorrer subcarpetas ni seguir enlaces | resource_id, path opcional, limit opcional hasta 500 |
| excel.from_csv | CSV convertido a Excel sin pasar todas las filas por el modelo | source_resource_id, source_path, resource_id, path, delimiter opcional |
| sql.describe | Nombres de tablas o columnas y tipos de una tabla; no entrega registros | connection_id, table y schema opcionales |
| sql.export_excel | SELECT, agregaciones y reporte Excel sin copiar filas al contexto de la IA | connection_id, query, resource_id, path |
| social.prepare_post | Borrador JSON local para LinkedIn, Facebook o Instagram; no publica | resource_id, path terminado en .json, platform, text |

Todas exigen asignación de herramienta y permisos del destino. Las nuevas herramientas Excel no sobrescriben archivos existentes. El generador es código nativo controlado: no requiere Docker ni ejecuta scripts redactados por el modelo.

`filesystem.list` devuelve una lista limitada y la marca truncated si hay más elementos. No es un listado recursivo completo. Las fechas del generador son ficticias de 2026; los importes son enteros de ejemplo, no representan transacciones reales.

El motor permite hasta dos correcciones de argumentos rechazados antes de ejecutar una herramienta. Guarda el error, pide corregir la llamada y conserva el contexto. No reintenta automáticamente errores de permisos, escrituras iniciadas, consultas fallidas o publicación externa. No convierte una respuesta vacía o incompleta del modelo en un éxito.

## Prueba disponible en esta instalación

Se registraron las herramientas nuevas y se asignaron `excel.generate_sales`, `excel.from_csv` y `filesystem.list` al agente existente Generador Reportes, conservando sus asignaciones anteriores.

Se creó el procedimiento **Generar ventas Excel con código**, que usa el recurso Prueba Oficina ya autorizado al agente.

1. Reiniciar Oficina IA y recargar la página.
2. Nueva tarea → agente Generador Reportes.
3. Modo → Procedimiento: Generar ventas Excel con código.
4. Entradas:

```json
{"output_name":"ventas-ampliacion-01.xlsx","count":50}
```

5. Ejecutar y verificar la ruta, rows=50 y validated=true. Elegir un nombre nuevo al repetir.

Este procedimiento evita una llamada a Ollama: genera los datos y el archivo directamente. Una tarea IA también puede seleccionar la herramienta, pero sigue dependiendo de que el modelo formule una acción válida.

## SQL Server y decisiones

Flujo disponible con conexión autorizada:

1. Configurar SQL Server con driver ODBC y credencial o autenticación Windows.
2. Asignar conexión con connect/select y herramientas sql.describe, sql.query y sql.export_excel.
3. Consultar tablas y columnas reales, evitando inventar nombres.
4. Calcular agrupaciones y métricas en SQL. Para decidir, definir objetivo, periodo, umbrales, datos suficientes y acciones permitidas.
5. Enviar al modelo resultados agregados pequeños para explicar una recomendación.
6. Exportar registros directamente a Excel cuando sean demasiados para su contexto.

Ejemplo, reemplazando nombres por los reales de la base:

```sql
SELECT producto, SUM(total) AS ventas, SUM(cantidad) AS unidades
FROM dbo.Ventas
GROUP BY producto
```

Ejemplo de tarea:

```text
Consulta la estructura de SQL Ventas y confirma las columnas disponibles.
Calcula ventas y unidades por producto en el periodo que acordemos.
Recomienda qué productos revisar, mostrando los datos que sustentan la recomendación.
Si faltan costos, no afirmes rentabilidad; si falta stock, no propongas cantidades de reposición definitivas.
Exporta el detalle a analisis-ventas-01.xlsx en Prueba Oficina usando sql.export_excel.
No modifiques SQL ni ejecutes acciones comerciales.
```

Una decisión compleja necesita criterios verificables y datos suficientes. El modelo no obtiene autoridad para escribir en SQL o publicar por producir una recomendación. SQL sigue siendo de lectura; el flujo de detección de cambios Excel → INSERT/UPDATE requiere vigilante, importador transaccional e idempotencia descritos en el manual.

Las pruebas actuales verifican consultas, estructura y cálculos con SQLite de prueba. No equivalen a una conexión real SQL Server: falta verificar la conexión del usuario, driver y tabla destino.

## Publicación con aprobación

La herramienta entregada prepara un borrador local:

```json
{"resource_id":"UUID_RECURSO","path":"linkedin-borrador-01.json","platform":"linkedin","text":"Contenido para revisar"}
```

El archivo y resultado incluyen `published=false`. Guardarlo no es aprobación ni publicación. No existe todavía un conector de publicación o una cuenta social vinculada en este proyecto.

Arquitectura del siguiente paso:

1. Conector por plataforma con API oficial, autenticación OAuth y tokens en vault.
2. Cuenta, página o perfil autorizado explícitamente; validar capacidades al conectar.
3. Borrador versionado: texto, medios, destino y vista previa.
4. Aprobación que identifica el contenido exacto por hash y la cuenta destino. Cualquier edición invalida esa aprobación.
5. El ejecutor verifica aprobación incluso si el agente está en trusted.
6. Publicación con estado persistente, identificación de operación y respuesta externa registrada.
7. Si la red pierde la respuesta, marcar resultado incierto y reconciliar antes de repetir: no publicar duplicados por un reintento ciego.
8. Mostrar enlace/identificador devuelto por la plataforma. No decir «publicado» solo por terminar el flujo local.

Las políticas ask/auto del proveedor IA regulan enviar contexto al modelo; no sustituyen la aprobación de una publicación.

Fuentes de referencia para desarrollar los conectores: [LinkedIn Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api), [acceso a APIs LinkedIn](https://learn.microsoft.com/en-us/linkedin/shared/authentication/getting-access), [Meta Pages API](https://developers.facebook.com/docs/pages-api/), [Instagram Platform](https://developers.facebook.com/docs/instagram-platform/). Antes de implementar cada integración se deben verificar el flujo de acceso, permisos y tipos de cuenta admitidos por su documentación vigente.

## Extensión a otras aplicaciones

Una aplicación nueva necesita un conector específico, contrato de herramientas y permisos. No se implementa como acceso libre a cualquier URL o ejecución arbitraria. Clasificar cada operación en lectura, preparación, modificación o publicación; definir cuándo exige aprobación y cómo verificar el resultado real.

## Trabajo pendiente

- Conexión y pruebas con SQL Server real del usuario.
- Vigilante de Excel. La escritura SQL transaccional con aprobación y tablas autorizadas se implementó en la Etapa 3; véase CONFIGURACION_AGENTES.md.
- Conectores OAuth y publicación real LinkedIn/Meta.
- Interfaz de vista previa y aprobación específica de publicaciones.
- Referencias a conjuntos de datos persistentes para análisis generales grandes; hoy los nuevos exportadores evitan el contexto en los casos implementados.
- Evaluación reproducible de decisiones con criterios de negocio; no hay una garantía genérica de razonamiento correcto.

Las herramientas, instrucciones y borradores entregados son operativos. Los conectores y capacidades listados como pendientes no se presentan como terminados.
