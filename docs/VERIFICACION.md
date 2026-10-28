# Verificación — 2026-10-06

## Historia comprobada
Interfaz React → API autenticada → procedimiento persistido → lectura CSV → resumen numérico → escritura Excel en recurso autorizado → validación de workbook → resultado y artefacto visibles.

| Frontera | Evidencia | Estado |
|---|---|---|
| UI | Chromium real muestra oficinas, formularios, tareas y organigrama | Verificado en desarrollo |
| UI → API | Demo instalada y tarea creada desde formularios reales | Verificado |
| API → persistencia | SQLite, relaciones, UUIDs, pasos y eventos guardados | Verificado |
| Datos → archivo | Excel con hojas Datos/Resumen, 4 registros y suma kilos=6600 | Verificado por reapertura openpyxl |
| API → UI | Estado completada, tres pasos y nombre del archivo | Verificado |
| Eventos | WebSocket autenticado cubierto por prueba y soporte servidor instalado | Verificado |
| Credenciales | Windows vault: escritura/lectura/eliminación de referencia temporal | Verificado |
| Producción Windows | Tauri + PostgreSQL/Docker + Ollama real | Pendiente por requisitos ausentes |

## Comandos reproducibles
```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend scripts tests
.\.venv\Scripts\python.exe -m alembic check
npm.cmd run build
npm.cmd test
npm.cmd audit
```

Para prueba de navegador: inicie `npm run dev:local`, instale Playwright por separado o defina OFFICE_PLAYWRIGHT_MODULE apuntando a un paquete existente; `node scripts/verify-browser.mjs`. OFFICE_BROWSER_EXECUTABLE permite seleccionar Chromium de pruebas instalado. No descarga navegadores automáticamente.

El script guarda Excel/capturas dentro de data/verification. La demo solo se instala por la acción explícita de este script o del usuario, nunca al iniciar. Los tests pytest usan otra base temporal y no alteran oficinas del usuario.

31 pruebas backend: CRUD/persistencia, ciclos y oficinas, permisos/path escapes, SQL no destructivo y SQL → Excel, CSV → Excel, sobrescritura/aprobación/reanudación, redacción, inyección de fórmula, delegación, memoria aislada, políticas API externas, cancelación, contrato HTTP de cuatro proveedores, contrato Docker/staging y ausencia de ejecución nativa Python, backups, costos desconocidos, Windows Runtime, WebSocket y limpieza de estados al fallar procedimientos.

Las pruebas de proveedores/Docker utilizan fixtures exclusivamente de test. No sustituyen Ollama, Docker ni SQL Server reales. Ninguna generación con API paga se ejecutó.

## Oficina 2D

33 pruebas backend y 2 frontend aprobadas. Compilación aprobada. Playwright comprobó selección, edición y persistencia del escritorio tras recargar. El flujo existente CSV → Excel también pasó sin errores de navegador. Captura local: data/verification/oficina-2d.png.

## Oficina 2D: cierre de pendientes

- 36 pruebas backend y 5 frontend aprobadas.
- Playwright `scripts/verify-office2d-live.mjs`: WebSocket real, arrastre, teclado, persistencia y respaldo REST correctos, sin errores de página.
- Caminata visual verificada con mensaje exclusivo del navegador de prueba; no se fabrican eventos en la base de producción. El test del motor valida mensajes de delegación y su representación en el snapshot.
- `scripts/verify-browser.mjs`: procedimiento CSV → Excel real aprobado tras la integración.
- Ollama en la etapa anterior a su instalación: conexión local rechazada y modelos de agentes vacíos. El estado posterior y la generación real están documentados debajo. Las pruebas de estado usan transportes HTTP explícitos de tests; no constituyen una generación real.

## Oficina 3D y generación local real

- 39 pruebas backend y 7 frontend aprobadas; compilación TypeScript/Vite aprobada.
- scripts/verify-office3d.mjs: WebGL, paseos disponibles, selección, giro/zoom, movimiento reducido y cambio 2D/3D aprobados sin errores JavaScript. Usa renderizado software de prueba; no prueba la aceleración de WebView2 empaquetado.
- scripts/verify-ollama-real.mjs consulta el ID exacto creado. Tarea 2d10c6d3-7e0e-4643-9dea-3c119a034764: completed, proveedor ollama, modelo qwen3:1.7b, 23750 ms, 347/18 tokens, resultado Hola, Ollama está funcionando.
- Una comprobación inicial de texto genérico Completada fue descartada: correspondía a otra fila. La tarea previa con 4b agotó la espera. No se presenta esa comprobación como éxito.
- Capturas: data/verification/oficina-3d.png y ollama-generacion-real.png.

Verificación final tras los ajustes 3D: los scripts de oficina 3D, oficina 2D en vivo y CSV → Excel pasaron sin errores JavaScript. El canvas limita renderizado a aproximadamente 30 FPS para reducir carga local; Three.js se carga bajo demanda.
