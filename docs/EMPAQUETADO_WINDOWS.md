# Preparación del instalador Windows

## Tecnología y estado real

Conservar Tauri 2: ya existe ventana Rust, invocación de token, CSP y arranque del backend. Electron introduciría otra arquitectura sin necesidad. El frontend compilado ya se genera en dist. `bundle.active` sigue deshabilitado para evitar anunciar como portable el Tauri que depende de la ruta de checkout.

Se agregó `packaging/windows_backend.py`: entrada de sidecar con FastAPI/uvicorn, escucha loopback, token entregado por entorno, datos predeterminados `%LOCALAPPDATA%/OficinaIA`, SQLite persistente y rutas separadas de la aplicación. `packaging/backend.spec` prepara una receta PyInstaller onedir sin consola y sin incluir .env, SQLite de usuario, credenciales ni el checkout completo. Son preparación; no se construyó ni probó un binario.

La entrada sí se arrancó y reinició desde fuente mediante `scripts/verify_dual_startup.py`, con una base separada, agente/habilidad persistidos y trabajo nativo real. Ese ensayo valida el arranque Python; no sustituye la prueba del ejecutable ni de su integración con Tauri.

En este equipo no se encontró Cargo/Rust ni PyInstaller del proyecto. No se instaló software global. No existe un instalador funcional generado por esta fase. El worker venv actual referencia el Python de desarrollo y aún no es portable a otro equipo.

## Pasos pendientes para una distribución revisable

1. Instalar con autorización los prerrequisitos oficiales de Tauri: Rust MSVC, Microsoft C++ Build Tools y WebView2. Docker es opcional.
2. Agregar PyInstaller a un entorno local de compilación y construir el sidecar: `.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm packaging/backend.spec`. Revisar imports dinámicos, assets PDF y drivers SQL en una máquina limpia.
3. Empaquetar un runtime Python Windows revisado para el worker fijo, o un worker separado compilado, que no dependa del Python de Codex/desarrollo. El backend congelado no puede tratarse como intérprete para crear un venv.
4. Cambiar el arranque Tauri release para localizar y arrancar el sidecar incluido en recursos. Pasar token sólo mediante el entorno, comprobar health con el mismo token antes de presentar la aplicación, y supervisar salida/error. Mantener desarrollo usando el checkout.
5. Asignar al árbol backend un Job Object en la ventana, para cierre garantizado también ante caída de Tauri. Mantener el cierre del trabajador nativo. No depender solamente de taskkill al salir normalmente.
6. Habilitar bundle, recursos del sidecar y NSIS en una configuración release; generar `npm.cmd run desktop:build`. No habilitar bundle hasta resolver los pasos anteriores.
7. Probar abrir/cerrar, puerto ocupado, máquina sin Node/Python/Docker, carga de agentes/habilidades, Vault, creación de artefactos, cancelación, instalación/actualización/desinstalación y migraciones.
8. Definir firma de código y canal de actualizaciones firmado. No activar actualizaciones sin una clave y distribución controladas.

## Datos y actualización

Binarios y assets son archivos de programa; datos del usuario son `%LOCALAPPDATA%/OficinaIA`. El lanzador de desarrollo acepta `--local --user-data` para ejercitar esa separación; no migra ni elimina la base `data/office.db`. Para migrar: detener la aplicación, hacer copia de seguridad, copiar base y configuración al destino revisado y verificar permisos/rutas. Mantener referencias de Credential Manager sin exportar claves en texto.

Una actualización debe respaldar datos y aplicar migraciones compatibles antes de usar la base. Desinstalar conserva AppData y credenciales por defecto; borrar datos requiere una decisión explícita del usuario. Mantener backups fuera de la carpeta de instalación. No empaquetar recursos externos de agentes sin petición del usuario.

Referencias oficiales: [prerrequisitos Tauri](https://v2.tauri.app/start/prerequisites/), [instalador Windows Tauri](https://v2.tauri.app/distribute/windows-installer/).
