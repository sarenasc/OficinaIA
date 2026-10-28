"""Future sidecar entry. Source-testable; no credentials or user data embedded."""
import argparse
import multiprocessing
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--port", type=int, default=38080)
    args = parser.parse_args()
    if not os.environ.get("OFFICE_SESSION_TOKEN"):
        raise RuntimeError("La ventana Tauri debe entregar OFFICE_SESSION_TOKEN mediante el entorno")
    directory = args.data_dir or Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "OficinaIA"
    directory.mkdir(parents=True, exist_ok=True)
    os.environ["OFFICE_DATA_DIR"] = str(directory.resolve())
    os.environ.setdefault("OFFICE_DATABASE_URL", "sqlite:///" + str(directory.resolve() / "office.db"))
    if not getattr(sys, "frozen", False):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    import uvicorn
    from app.main import app
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
