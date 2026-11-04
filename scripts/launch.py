"""Windows application bootstrap, no global dependencies or silent installs."""

import argparse
import os
import secrets
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-only", action="store_true")
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--token")
    parser.add_argument("--services", action="store_true")
    parser.add_argument("--user-data", action="store_true", help="Datos independientes del checkout en AppData Local")
    parser.add_argument("--base-nueva", action="store_true",
                        help="Empieza con una base SQLite vacía; la actual se conserva apartada, no se borra")
    args = parser.parse_args()
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    token = args.token or secrets.token_urlsafe(32)
    env = dict(os.environ, OFFICE_SESSION_TOKEN=token, PYTHONPATH=str(ROOT / "backend"))
    if args.user_data:
        data_root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "OficinaIA"
        data_root.mkdir(parents=True, exist_ok=True)
        env["OFFICE_DATA_DIR"] = str(data_root)
    sys.path.insert(0, str(ROOT / "backend"))
    from app.core.storage import database_path, reset

    data_dir = (ROOT / env.get("OFFICE_DATA_DIR", "data")).resolve()
    if args.local:
        env["OFFICE_DATABASE_URL"] = "sqlite:///" + str(database_path(data_dir))
    if args.base_nueva:
        url = env.get("OFFICE_DATABASE_URL") or "sqlite:///" + str(database_path(data_dir))
        if not url.startswith("sqlite:///"):
            raise RuntimeError("--base-nueva solo se aplica a SQLite")
        kept = reset(Path(url.removeprefix("sqlite:///")))
        print("Base nueva. " + (f"Base anterior apartada como {kept}" if kept else "No había base anterior."))
    if args.services:
        result = subprocess.run(["docker", "compose", "up", "-d", "--wait", "postgres", "redis"], env=env)
        if result.returncode:
            raise RuntimeError("Docker/PostgreSQL/Redis no pudieron iniciarse")
    if env.get("OFFICE_DATABASE_URL", "").startswith("postgresql"):
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=True)
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "38080", "--no-access-log"],
        env=env,
    )
    frontend = None
    try:
        for _ in range(60):
            if backend.poll() is not None:
                raise RuntimeError("Backend no pudo iniciar. Revise configuración y puerto 38080")
            try:
                req = urllib.request.Request(
                    "http://127.0.0.1:38080/api/health", headers={"Authorization": "Bearer " + token}
                )
                with urllib.request.urlopen(req, timeout=1) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("Backend no respondió dentro del plazo")
        if args.backend_only:
            backend.wait()
        else:
            env["VITE_OFFICE_TOKEN"] = token
            npm = "npm.cmd" if sys.platform == "win32" else "npm"
            frontend = subprocess.Popen([npm, "run", "dev"], env=env)
            frontend.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for child in [frontend, backend]:
            if child and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()


if __name__ == "__main__":
    main()
