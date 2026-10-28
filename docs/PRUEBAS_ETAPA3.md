# Pruebas Etapa 3 — resultados ejecutados

Fecha local: 8 de octubre de 2026 (UTC de las verificaciones públicas: 9 de octubre). No se alteraron bases de datos personales/empresariales ni se publicaron servicios externos.

## Suite final

| Comprobación | Resultado real |
|---|---|
| pytest, suite completa tras integración | **94 passed, 2 skipped**, 65.13 s |
| npm test | **9 pruebas**, 4 archivos, todas pasaron |
| npm run build | TypeScript y Vite completados; 225 módulos |
| Ruff | Comprobaciones pasaron |
| Interfaz de conexiones HTTP/búsqueda | Playwright pasó: campos, autenticación Bearer, borrador inactivo, Brave, sin escrituras reales |
| PDF | Generado, leído, combinado y validado con pypdf. Renderizado con PDFium y revisado visualmente; tabla, barras, título, fuentes y paginación |

Avisos no bloqueantes: deprecación de integración Starlette/httpx en pruebas; chunk 3D de Vite superior a 500 KB, cargado bajo demanda. No hubo errores de compilación.

## Herramientas y seguridad con datos de prueba

- HTTP real contra un servidor local de prueba: JSON, timeout, límite de tamaño y denegación de redirección hacia metadatos. El destino privado se autoriza por aprobación explícita en api.request; no se permite implícitamente a web.fetch.
- web.download: CSV de servidor de prueba y ruta/hash comprobados. Ese caso usa una inyección de DNS solo en pytest para conectar al servidor local; la protección SSRF de producción no se modifica. Se probó también descarga pública real por separado.
- SSRF: loopback IPv4/IPv6, localhost, redes privadas y metadatos denegados por defecto; metadatos link-local siguen denegados incluso con allow_private.
- Rate limit y escapes codificados de URL rechazados.
- api.request: aprobación obligatoria para API privada incluso trusted; respuesta real de API local, guardado JSON y rechazo de escapes.
- SQL real en SQLite de prueba: SELECT con parámetros, DML pendiente hasta aprobación, modificación correcta tras aprobar, rollback al superar filas autorizadas, denegación de DDL/múltiples sentencias/escritura sin WHERE/conexión sin select.
- PDF real: creación con tabla y gráfico, lectura, combinación de dos documentos, ruta/hash/artefacto/auditoría; páginas sin texto identificadas sin OCR; lectura de recurso ajeno y escape de destino denegados.
- Dependencias de habilidades faltantes bloquean antes de llamar al modelo.
- Resultados API grandes se envían al modelo como muestras sin alterar los datos completos de ejecución.
- Límite de dos ejecuciones Python simultáneas comprobado como contrato.
- La delegación se probó con proveedor IA de contrato y herramientas de archivos reales: padre delega a hijo, el hijo crea un archivo, devuelve resultado, y quedan ejecución, mensajes y artefacto. No se cobró una llamada IA ni se reemplazó un proveedor de producción.
- Brave Search: parámetros, credencial en cabecera y estructura de resultados comprobados mediante contrato de prueba. No hubo llamada comercial real porque no hay clave Brave configurada.

## Verificación pública real

Ejecutado scripts/verify-stage3-public.py con registro de herramientas real, base SQLite aislada en memoria y recursos explícitos de prueba. Evidencia final: `data/verification/stage3-public-flow/run-18c30b11/verification.json`.

1. web.fetch: FIFA, HTTP 200.
2. web.download: dataset público StatsBomb competitions.json, HTTP 200, 34887 bytes, 80 registros; SHA-256 verificado.
3. web.download: CSV público de Football Data 2025/26, HTTP 200, 203438 bytes; SHA-256 verificado.
4. filesystem.read: lectura del JSON efectivamente descargado.
5. pdf.create: reporte PDF de verificación, 2014 bytes, una página, integridad y lectura comprobadas.
6. Se registraron cinco eventos de auditoría de herramientas.

Se usó el origen canónico `https://football-data.co.uk/mmz4281/2526/E0.csv`. La dirección con www redirige al dominio sin www: la primera prueba denegó esa redirección por no estar autorizada. Se corrigió el recurso de prueba; no se relajó la seguridad global.

Estos archivos contienen datos públicos y un reporte técnico, no predicciones ni recomendaciones deportivas. La estructura y la actualidad de cada proveedor pueden cambiar.

## Pendientes por servicios no disponibles

- **Dos pruebas Docker omitidas**: lectura CSV, pandas/agrupaciones, Poisson, PNG/resultados, versiones reales de paquetes; timeout real del contenedor. Docker no está instalado ni en PATH ni en su ruta habitual. No se ejecutó código de agente en el host para simular el resultado.
- Búsqueda Brave real: falta credencial y conexión activa asignada. El conector está implementado.
- API deportiva comercial: falta URL/base/configuración y credencial del servicio elegido. Se verificó API local de prueba; no se inventó conexión real.
- SQL Server/PostgreSQL externos: faltan servidores/configuración/credenciales, y SQL Server necesita driver ODBC/pyodbc. Solo SQLite se comprobó como integración de base real en este entorno.
- Contenedor del backend container-api: no se construyó ni inició porque falta Docker; no se montó Docker socket. La ejecución de agentes Python se soporta desde el backend nativo Windows con Docker Desktop.

## Repetir

```powershell
.venv\Scripts\python.exe -m pytest -q
npm.cmd test
npm.cmd run build
```

Con Docker instalado e iniciado:

```powershell
docker compose --profile sandbox-build build python-sandbox
.venv\Scripts\python.exe -m pytest tests/test_stage3_docker.py -q
```

Prueba pública opcional (internet, sin API comercial): `.venv\Scripts\python.exe scripts/verify-stage3-public.py`. Crea una nueva subcarpeta de verificación al repetir y no sobrescribe datos del usuario. Si un servicio cambia o deniega acceso, devuelve el error real.
