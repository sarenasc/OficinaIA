# Development packaging recipe; requires project-local PyInstaller, not installed automatically.
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).parent
analysis = Analysis([str(root / 'packaging/windows_backend.py')], pathex=[str(root / 'backend')],
    datas=[(str(root / 'backend/app/execution/sports_worker.py'), 'app/execution')],
    hiddenimports=collect_submodules('app') + collect_submodules('uvicorn'),
    excludes=['pytest', 'ruff'], noarchive=False)
archive = PYZ(analysis.pure)
executable = EXE(archive, analysis.scripts, [], exclude_binaries=True, name='oficina-backend', console=False)
collection = COLLECT(executable, analysis.binaries, analysis.datas, name='oficina-backend')
