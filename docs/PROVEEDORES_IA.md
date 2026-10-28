# Proveedores IA

Interfaz AIProvider completa una lista normalizada de mensajes y devuelve una acción JSON con conteo de tokens. Registro de adaptadores: Ollama, OpenAI Chat Completions, Anthropic Messages y Gemini generateContent.

URLs externas oficiales:
- OpenAI: https://api.openai.com/v1
- Anthropic: https://api.anthropic.com/v1
- Gemini: https://generativelanguage.googleapis.com/v1beta

Modelo predeterminado configurable. Botón Probar conexión lista modelos sin realizar generación. Credenciales con botón separado y formulario password; almacenamiento solo en Windows vault. No se permite un endpoint externo arbitrario para evitar enviar secretos a otro host.

Fallback es una lista ordenada `[{"provider_id":"UUID","model":"nombre"}]`. never descarta todos los externos; ask pausa antes de enviar contexto; auto permite. Una aprobación vale solo para agente/proveedor/modelo de esa tarea. Fallback reacciona a errores de conexión, protocolo o proveedor, no a una evaluación automática de calidad.

Tarifas USD/millón de tokens configurables por modelo en pricing. Sin tarifa, costo desconocido, no cero. Ollama costo API=0 (LOCAL, no estima electricidad/hardware). Desglose por día/mes/oficina/agente/tarea disponible en Resumen.

Adaptadores externos tienen implementación y pruebas de contrato con respuestas de prueba; todavía no validados con credenciales reales. Compatibilidad de parámetros depende del modelo elegido.

Referencias oficiales consultadas: https://platform.openai.com/docs/api-reference/chat, https://platform.claude.com/docs/en/api/messages/create, https://ai.google.dev/api/generate-content.
