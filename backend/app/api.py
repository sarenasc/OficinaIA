"""Route registration order keeps concrete routes before generic CRUD."""

from importlib import import_module

from app.http.common import authorize as authorize
from app.http.common import router as router
from app.http.common import serialize as serialize
from app.http.common import ws_router as ws_router

for _module in (
    "overview",
    "assignments",
    "configuration",
    "execution",
    "tasks",
    "offices",
    "runtime",
    "consumption",
    "backups",
    "progress",
    "scene",
    "agent_import",
    "skill_import",
    "crud",
):
    import_module("app.http." + _module)
