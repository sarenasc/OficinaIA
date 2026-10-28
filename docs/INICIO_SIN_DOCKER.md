# Inicio con un clic sin Docker

Ejecuta **Oficina IA.exe**, en la raíz del sistema. Incluye Python, el backend,
SQLite, la interfaz compilada y el trabajador de operaciones fijas. No necesita
Python, Node, Rust ni Docker instalados para arrancar. Se abre el navegador
predeterminado cuando el backend responde. La primera apertura puede tardar
mientras se extraen los componentes en la carpeta temporal de Windows.

Conserva abierta la consola del lanzador durante el uso. Para detener el sistema,
pulsa Ctrl+C en ella o ciérrala. Cerrar solamente la pestaña del navegador no
detiene el backend. El puerto local 38080 debe estar libre: detén el otro lanzador
antes de abrir este ejecutable.

Los datos se guardan en `data`, junto al ejecutable. En la carpeta actual utiliza
la misma base SQLite `data/office.db`; no migra bases PostgreSQL. Si copias el EXE
a una carpeta nueva, crea una oficina de datos nueva. La carpeta debe permitir
escritura. No copies ni muevas bases de datos mientras el sistema esté abierto.
El ejecutable no contiene datos, credenciales ni archivos `.env` del usuario.

Para usar IA local necesitas Ollama iniciado y un modelo instalado. Este EXE no
descarga modelos. Las conexiones externas y SQL Server conservan sus requisitos
de red y drivers. El Python de código libre sigue requiriendo Docker; las
operaciones fijas estadísticas y CSV usan el trabajador incluido. El modo de
ejecución existente se conserva: selecciona Automático o Windows nativo en
Configuración si antes tenías seleccionado Docker.

## Reconstruir después de modificar el código

Desde un Python Windows 3.12+ con pip y Node/npm disponibles, ejecuta:

```powershell
python scripts/build_portable.py
```

La compilación descarga dependencias a `build/packages`, compila la interfaz y
genera `Oficina IA.exe` en la raíz. No instala paquetes globales. El EXE no está
firmado digitalmente. La receta está en `packaging/portable.spec` y es independiente
de la futura distribución Tauri descrita en `EMPAQUETADO_WINDOWS.md`.
