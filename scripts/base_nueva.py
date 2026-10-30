"""Start from zero: keep the current SQLite database aside (nothing is deleted)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT)

from app.core.storage import database_path, reset  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
data_dir = (ROOT / os.environ.get("OFFICE_DATA_DIR", "data")).resolve()
database = database_path(data_dir)
kept = reset(database)
print(f"Base anterior apartada como {kept}" if kept else "No había base anterior.")
print(f"La próxima apertura crea una base vacía en {database}")
