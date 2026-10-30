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

Los datos se guardan en `data`, junto al ejecutable. La base SQLite es
`data/office.db`, salvo que la carpeta esté en OneDrive, Dropbox u otra carpeta
sincronizada: entonces la base vive en `%LOCALAPPDATA%\OficinaIA\bases\<id>\office.db`
(la consola y el log muestran la ruta). OneDrive sincroniza `office.db`, `-wal` y `-shm`
por separado y, sobre todo entre dos equipos, deja la base dañada
(`database disk image is malformed`). La primera vez se copia la base anterior
si está sana; el archivo original no se modifica. Cada equipo tiene su propia base:
para llevar datos a otro equipo use un backup, no la carpeta sincronizada.

En cada arranque se comprueba la integridad de la base y se guarda una copia en
`data/backups/auto` (últimas 10). Si la base está dañada, se aparta como
`office.db.danada-<fecha>` y se restaura el backup sano más reciente. No migra
bases PostgreSQL. Si copias el EXE
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
