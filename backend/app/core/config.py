"""Local configuration. Secrets are supplied by environment or Windows vault."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
DATA_DIR = Path(os.getenv("OFFICE_DATA_DIR", "data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("OFFICE_DATABASE_URL", f"sqlite:///{DATA_DIR / 'office.db'}")
OLLAMA_URL = os.getenv("OFFICE_OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_THREADS = max(1, int(os.getenv("OFFICE_OLLAMA_THREADS", "4")))
SANDBOX_IMAGE = os.getenv("OFFICE_SANDBOX_IMAGE", "oficina-python-sandbox:local")
TOKEN = os.getenv("OFFICE_SESSION_TOKEN", "")
MAX_STEPS = 20
