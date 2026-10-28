# Ollama

Proveedor inicial registrado automáticamente, sin agentes ni oficinas. URL 127.0.0.1:11434. Probar conexión consulta `/api/tags` y lista modelos instalados. Si falta Ollama, instala voluntariamente desde https://ollama.com/download/windows. La aplicación no descarga ni instala modelos silenciosamente.

Configure el nombre exacto de modelo en cada agente. El motor usa `/api/chat`, stream=false, format=json y opciones de temperatura/contexto. Se emplea un protocolo JSON de acciones, validado antes de ejecutar herramientas, que evita acoplar agentes al formato de tool calling de un proveedor.

Formato: `{"type":"tool","name":"csv.read","arguments":{...}}`, `{"type":"delegate","agent_id":"...","request":"..."}` o `{"type":"final","content":"..."}`. Si el modelo incumple formato, falla claramente y puede intentar fallback. No se detecta automáticamente calidad semántica ni se presupone éxito por recibir HTTP 200.

Uso mostrado LOCAL. Generación real verificada en este PC con qwen3:1.7b: saludo completado en 23,75 segundos, 347 tokens de entrada y 18 de salida. Protocolo y políticas también tienen pruebas con adaptadores explícitos de tests.

## Estado visible en oficina 2D

La sala consulta `/api/ollama/status`: comprueba `/api/tags` en los proveedores locales configurados y cuenta agentes cuyo modelo está instalado. Mostrar backend conectado o WebSocket conectado no significa que Ollama esté disponible. Usa Configurar IA para abrir Proveedores IA; asigna después el nombre exacto instalado en cada agente o en el modelo por defecto del proveedor.

Comprobación actual (2026-10-06): Ollama disponible, qwen3:4b y qwen3:1.7b instalados. El proveedor usa qwen3:1.7b como predeterminado; los tres agentes de la demo lo heredan y tienen contexto 2048. El equipo tiene 8 GB de RAM y la inferencia observada usa CPU (sin memoria GPU asignada).

## Error de tiempo de espera corregido

El error anterior podía quedar vacío porque algunas excepciones HTTP no tienen texto. Ahora las ejecuciones conservan mensajes específicos y el nombre del tipo si el texto está vacío. Ollama admite una espera de 300 s, conexión de 10 s y generación máxima de 2048 tokens. Para Qwen3 se envía think=false: las acciones del motor necesitan JSON breve. Los errores antiguos permanecen como historial.

Con qwen3:4b y contexto 8192 se observó agotamiento de espera de 300 s; había unos 350 MB de RAM libres. Se descargó qwen3:1.7b, se conservó 4b y se redujo el contexto de la demo a 2048. La tarea exacta 2d10c6d3-7e0e-4643-9dea-3c119a034764 terminó correctamente con resultado Hola, Ollama está funcionando. La prueba consulta ese ID específico; no acepta el estado de otras filas del historial.

## Límite de CPU local

Las llamadas a Ollama usan cuatro hilos de CPU por defecto (`num_thread`), configurables con `OFFICE_OLLAMA_THREADS` en el entorno o `.env`. Reinicie Oficina IA tras cambiarlo. Este ajuste limita la competencia con la interfaz y otros procesos; no garantiza terminar cualquier solicitud dentro de 300 segundos. Se conserva el máximo de 2048 tokens para no recortar prematuramente acciones que contienen filas de Excel.

Revisión de la tarea de 50 ventas (2026-10-06): Ollama estaba conectado y empezó a generar una acción `excel.create`. Una prueba de 512 tokens terminó por límite de longitud; la solicitud completa con 2048 tokens y cuatro hilos volvió a agotar los 300 s. El ajuste de hilos no resuelve por sí solo esta tarea. No se ejecutaron herramientas ni se crearon archivos en la carpeta del usuario durante este diagnóstico.

## Nombre de archivo Excel

La herramienta `excel.create` agrega `.xlsx` si falta la extensión y corrige el error de escritura `.xlxs` a `.xlsx`. Otras extensiones se rechazan. Los permisos, la existencia del archivo y el registro de artefactos se comprueban sobre el destino corregido; el contenido de un Excel existente nunca se sobrescribe por esta corrección. Reinicie Oficina IA para cargar el cambio y cree una tarea nueva: el error anterior permanece en el historial.
