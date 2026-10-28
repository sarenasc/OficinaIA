# Oficina IA Local

Plataforma Windows para configurar oficinas, agentes y herramientas desde la interfaz. El backend, la persistencia y la ejecución son locales; Ollama es el proveedor predeterminado. Las APIs externas son opcionales.

Proyecto en desarrollo. Consulte [estado real](docs/ESTADO_PROYECTO.md), [instalación Windows](docs/INSTALACION_WINDOWS.md) y [arquitectura](docs/ARQUITECTURA.md). No se incluyen oficinas ni roles de producción predefinidos.

## Abrir sin Docker con un clic

Ejecuta **Oficina IA.exe** en esta carpeta. Incluye el backend, la interfaz y el
trabajador nativo; abre el navegador y conserva los datos en `data`. Mantén la
ventana del lanzador abierta; ciérrala para detener el sistema. Ollama y sus
modelos se requieren para IA local. [Instrucciones y compilación](docs/INICIO_SIN_DOCKER.md).

## Manual de uso

[Manual completo de Oficina IA](docs/MANUAL_USUARIO.md): configuración de agentes, herramientas, permisos, tareas y procedimientos; ejemplos de reportes y diseño de sincronización Excel → SQL con detección de cambios. Distingue funciones disponibles de desarrollos pendientes.

[Gráficos de ventas en Excel sin sobrecargar la IA](docs/GRAFICOS_EXCEL.md): procedimiento directo, permisos y aprobación para agregar una pestaña al mismo archivo.

[Importar agentes desde JSON](docs/IMPORTAR_AGENTES.md): crear un equipo, coordinador, herramientas y delegaciones en un solo lote.

[Corrección de delegación deportiva](docs/CORRECCION_DELEGACION.md): dirección de relaciones, pruebas reales, conservación de permisos y bloqueos de ejecución separados.

[Diagnóstico del timeout del Investigador](docs/DIAGNOSTICO_INVESTIGADOR_TIMEOUT.md): auditoría real, fuentes y permisos, latencia Ollama, previews de datasets y operaciones explícitas sin inferencias innecesarias. El análisis de Colo-Colo sigue pendiente de una fuente con cobertura verificada.

[Importar habilidades desde JSON](docs/IMPORTAR_HABILIDADES.md): plantilla y creación de habilidades con instrucciones y herramientas requeridas.

## Etapa 3: herramientas reales

Internet autorizado, Brave Search, APIs configurables, Python aislado con bibliotecas estadísticas, SQL parametrizado y escritura aprobada, PDF y seguimiento de agentes/tareas. Los perfiles de herramientas se aplicaron únicamente a la oficina deportiva; los recursos y conexiones se autorizan por separado.

- [Auditoría y arquitectura](docs/ETAPA3_AUDITORIA.md)
- [Herramientas y parámetros](docs/HERRAMIENTAS_IMPLEMENTADAS.md)
- [Configuración paso a paso](docs/CONFIGURACION_AGENTES.md)
- [Seguridad y límites](docs/SEGURIDAD_HERRAMIENTAS.md)
- [Pruebas ejecutadas y pendientes](docs/PRUEBAS_ETAPA3.md)

Reinicia el lanzador para cargar el registro actualizado. Construye el entorno de análisis con `docker compose --profile sandbox-build build python-sandbox` después de instalar/iniciar Docker Desktop. Esta implementación no instala Docker ni agrega un socket Docker al perfil container-api. Las bibliotecas PDF forman parte de las dependencias del backend; `pip install -e ".[dev]"` actualiza una instalación nueva. Ninguna tarea instala paquetes automáticamente.

## Motor dual Windows / Docker

Operaciones Python fijas sin Docker: `.venv\Scripts\python.exe scripts/setup_native_worker.py`, reiniciar el lanzador y elegir motor en Configuración → Motor de ejecución. La misma herramienta `python.execute` admite `operation/parameters`: statistics.mean, sports.group, csv.read y csv.create. Conserva asignación/capacidad `python.execute`; no se cambian permisos automáticamente. El contrato `code/resources` continúa requiriendo Docker. `sports.analyze` conserva compatibilidad para configuraciones anteriores.

[Arquitectura dual](docs/ARQUITECTURA_DUAL.md) · [Windows](docs/EJECUCION_WINDOWS.md) · [Docker](docs/EJECUCION_DOCKER.md) · [Seguridad](docs/SEGURIDAD_EJECUCION.md) · [Preparación del instalador](docs/EMPAQUETADO_WINDOWS.md) · [Pruebas](docs/PRUEBAS_ARQUITECTURA_DUAL.md).

## Desarrollo

1. Python 3.11+, Node 22+, Docker Desktop, Ollama, Rust y herramientas C++ de Visual Studio.
2. `python -m venv .venv` y `.venv\Scripts\python -m pip install -e ".[dev]"`.
3. `npm.cmd install`.
4. Copiar `.env.example` a `.env`, cambiar la contraseña y ejecutar `docker compose up -d postgres redis`.
5. `docker compose build python-sandbox`.
6. Ejecutar `npm.cmd run desktop`. La ventana Tauri inicia el backend nativo.

Para desarrollo sin Docker: `npm.cmd run dev:local`. Usa SQLite persistente; Excel/PDF/SQL y el análisis deportivo predefinido funcionan sin Docker. Los scripts Python libres requieren Docker.

Pruebas: `.venv\Scripts\python -m pytest` y `npm.cmd run build`.

No instale ni descargue modelos silenciosamente. Seleccione un modelo instalado en Ollama. El procedimiento CSV → Excel no necesita un modelo y sirve para verificar herramientas reales; las tareas en lenguaje natural sí lo necesitan.

## Oficina 2D

Abre una oficina y entra en Agentes. La sala muestra personas en sus escritorios, estados reales y acceso a sus tareas. Selecciona una persona; con Editar distribución arrastra escritorios, usa las flechas o cambia X/Y y guarda el plano. Las visitas siguen mensajes reales y el estado se actualiza por WebSocket con respaldo REST. El indicador de Ollama distingue conexión y modelos asignados. El organigrama y la configuración de agentes siguen debajo. [Arquitectura 2D](docs/OFICINA_2D.md).

## Oficina 3D

En Agentes, la sala 3D muestra puestos, cafetera, comedor y descanso. Los agentes disponibles pasean; los que trabajan vuelven a su escritorio. Arrastra para girar, usa la rueda para acercar y selecciona una persona para ver su tarea. Plano 2D conserva la edición de escritorios. Arquitectura: [OFICINA_3D.md](docs/OFICINA_3D.md).

Ollama local está probado con qwen3:1.7b, modelo predeterminado del proveedor, y contexto 2048 en la demo. Se conserva qwen3:4b instalado. Véase [OLLAMA.md](docs/OLLAMA.md) para rendimiento y errores.

## Ampliación de herramientas

Generación de ventas Excel con código, listado de carpetas, CSV → Excel, estructura SQL y SELECT → Excel; borradores locales de publicaciones. [Uso, límites y siguiente integración SQL Server](docs/AMPLIACION_AGENTES.md). Publicación por API y sincronización automática Excel → SQL todavía pendientes.
