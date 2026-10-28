# Instalación Windows

## Requisitos
Windows 10/11, Python 3.11+ (probado con 3.12), Node 22+, Docker Desktop con contenedores Linux, Ollama, Rust estable, Microsoft C++ Build Tools y WebView2. La aplicación no instala herramientas ni descarga modelos por sí sola.

## Preparar el proyecto
Abra PowerShell en la raíz:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev,sql]'
npm.cmd install
Copy-Item .env.example .env
```

Edite `.env`. Cambie POSTGRES_PASSWORD y use la misma contraseña en OFFICE_DATABASE_URL, codificando caracteres especiales de la URL. Para SQL Server instale Microsoft ODBC Driver 18 y utilice una cuenta de lectura. No incluya contraseñas de conexiones SQL en JSON ni en el repositorio.

```powershell
docker compose up -d --wait postgres redis
docker compose build python-sandbox
ollama list
npm.cmd run desktop
```

Tauri inicia Python y abre una ventana de escritorio. El backend aplica migraciones PostgreSQL. Cerrar la ventana termina el proceso local. PostgreSQL/Redis permanecen bajo administración de Docker Desktop. También puede usar `Iniciar Oficina IA.cmd` después de preparar requisitos.

## Desarrollo sin Docker/Rust

```powershell
npm.cmd run dev:local
```

Backend en 127.0.0.1:38080; Vite en 127.0.0.1:1420. SQLite persiste en `data/office.db`. Este modo permite CSV, Excel y pruebas, pero los scripts Python requieren Docker. No es el instalador final. No abra Vite independientemente: el lanzador entrega un token por sesión.

## Primer resultado real
1. Configuración → Demo opcional.
2. Seleccione una carpeta existente y autorice la creación de archivos demo.
3. Nueva tarea → Oficina Demo Analítica → modo Procedimiento: CSV demo → Excel.
4. Entradas: `{"output_name":"reporte-demo.xlsx"}`.
5. Ejecute; revise tres pasos completados, el resultado `validated:true` y abra el Excel en la carpeta seleccionada.

Para IA real cree agentes, elija un modelo Ollama instalado y asigne herramientas y recursos. Las relaciones del organigrama limitan a quién puede delegar un coordinador. Tener un modelo configurado no concede permisos a archivos.

## Problemas frecuentes
- Puerto 38080/1420 ocupado: cierre otro proceso Oficina IA; no inicie múltiples instancias.
- Docker ausente: CSV y Excel siguen disponibles; Python falla explícitamente.
- Ollama sin modelos: instale voluntariamente un modelo usando Ollama y repita Probar conexión.
- Python del sistema falla: utilice la ruta de un intérprete real para crear `.venv`.
- SQL Server falla: compruebe driver ODBC, autenticación, certificado y acceso con el usuario Windows.

## Distribución
Fuente Tauri preparada para desarrollo. Un instalador `.exe` autónomo requiere empaquetar Python/backend como sidecar y sustituir la ruta de checkout del runtime. `bundle.active=false` evita presentar un paquete incompleto como instalador listo. Esa fase está pendiente.
