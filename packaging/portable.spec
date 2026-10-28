from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

root = Path(SPECPATH).parent
a = Analysis([str(root / 'packaging/portable.py')], pathex=[str(root / 'backend')],
    datas=[(str(root / 'dist'), 'dist'),
           (str(root / 'backend/app/execution/sports_worker.py'), 'app/execution')]
          + collect_data_files('jsonschema_specifications'),
    hiddenimports=collect_submodules('app') + collect_submodules('uvicorn')
                  + collect_submodules('keyring.backends') + ['pymysql', 'pyodbc'],
    excludes=['pytest', 'ruff'], noarchive=False)
# Some embedded Python distributions require this certificate policy file in ssl.py.
ssl_policy = Path(sys.base_prefix) / 'Lib' / 'codex-rejected-cas.pem'
if ssl_policy.is_file():
    a.datas += [('codex-rejected-cas.pem', str(ssl_policy), 'DATA')]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='Oficina IA', console=True)
