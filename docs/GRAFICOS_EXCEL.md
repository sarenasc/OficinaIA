# Gráficos de ventas sin sobrecargar el modelo

El error «Contexto excede el límite configurado» ocurría porque excel.read agregaba todas las filas a la conversación interna. Ahora la IA recibe cabeceras, cantidad de filas y una muestra; la respuesta completa queda en la ejecución de auditoría. Una muestra no sirve para calcular totales de todo el archivo.

La herramienta excel.chart lee y agrupa todas las filas directamente con Python. Recibe resource_id, path, category_column, value_column y, opcionalmente, sheet y chart_sheet. Suma la columna numérica por categoría y agrega una hoja con los valores agrupados y un gráfico de barras al mismo .xlsx. Requiere permisos read y modify. En modo safe pide aprobación vinculada al contenido del archivo. Si este cambia, pide revisar nuevamente. Una pestaña existente no se reemplaza: elija otro nombre.

## Ejecutar el procedimiento preparado

1. Reinicie Oficina IA para cargar el código actualizado.
2. Abra Nueva tarea y seleccione el modo Procedimiento.
3. Seleccione **Graficar ventas Excel con código** y el agente **Analista**.
4. En las entradas JSON escriba:

```json
{"path":"ventas.xlsx","chart_sheet":"GraficoVentas"}
```

5. Ejecute la tarea. En **Aprobaciones pendientes**, abra **Revisar aprobación** y apruebe agregar la pestaña al archivo.
6. Abra ventas.xlsx en Prueba Oficina y revise GraficoVentas. Cierre Excel antes de aprobar si tiene el archivo abierto.

El procedimiento no usa Ollama ni APIs externas. Está configurado para la hoja Datos, agrupando producto y sumando total. Para otro archivo con columnas distintas, adapte los argumentos del procedimiento. Límites: .xlsx de hasta 20 MB, 10000 filas, 100 columnas y 100 categorías. Las fórmulas necesitan valores calculados guardados por Excel. openpyxl puede no preservar funciones avanzadas de libros complejos; esta herramienta está orientada a libros de datos y gráficos compatibles.

También puede crear una tarea natural para el Analista: «Lee ventas.xlsx de Prueba Oficina y usa excel.chart para sumar total por producto, en una pestaña nueva GraficoVentas». El modo procedimiento evita depender del modelo para escoger la herramienta.
