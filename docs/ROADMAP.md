# Roadmap

1. Arquitectura, requisitos, modelo de datos y documentos.
2. FastAPI, PostgreSQL, Redis, migraciones y Compose.
3. React/TypeScript y shell Tauri.
4–6. CRUD oficinas/agentes/áreas, asignaciones y grafo sin ciclos.
7. Ollama, descubrimiento y llamadas a herramientas.
8–12. Registro, recursos filesystem, Python Docker, Excel y SQL de lectura.
13–15. Tareas persistentes, aprobaciones, delegación, eventos y artefactos.
16–18. Adaptadores externos, consumo y procedimientos.
19–20. Endurecimiento, pruebas, empaquetado Windows y verificación con servicios reales.

Una fase con código no equivale a una fase verificada en Windows. El estado enumera esa diferencia. Automatización visual y scheduler quedan fuera de la primera versión.

## Ampliación visual 2D

Implementado: sala SVG conectada a agentes y tareas, plano persistente independiente del organigrama, arrastre y teclado, WebSocket por oficina con respaldo REST y visitas con rutas entre estaciones según mensajes reales. Véase OFICINA_2D.md. La generación local básica ya está verificada; falta ampliar la validación de tareas complejas dirigidas por modelo.

## Ampliación 3D y Ollama

Implementados: sala 3D, cafetera/comedor/descanso, paseos ambientales ligados a disponibilidad, cámara, selección y alternativa 2D. Generación local de saludo verificada con qwen3:1.7b. La validación de herramientas dirigidas por modelo y del escritorio empaquetado mantiene su alcance separado.
