"""Build the standalone Windows launcher in the repository root."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


if __name__ == "__main__":
    os.chdir(ROOT)
    temporary = ROOT / 'build' / 'temp'
    temporary.mkdir(parents=True, exist_ok=True)
    os.environ['TEMP'] = os.environ['TMP'] = str(temporary)
    packages = ROOT / 'build' / 'packages'
    os.environ.pop('PYTHONPATH', None)
    if '--skip-install' not in sys.argv:
        run(sys.executable, "-m", "pip", "install", "--upgrade", "--target", str(packages), ".[sql]", "pyinstaller==6.16.0")
    os.environ['PYTHONPATH'] = os.pathsep.join([str(ROOT / 'backend'), str(packages)])
    os.environ['PYINSTALLER_CONFIG_DIR'] = str(ROOT / 'build' / 'pyinstaller-cache')
    os.environ['VITE_OFFICE_TOKEN'] = ''
    if '--skip-frontend' not in sys.argv:
        run("npm.cmd", "run", "build")
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", str(ROOT),
        "--workpath", str(ROOT / "build" / "portable"), "packaging/portable.spec")
