from typing import Literal

from fastapi import Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.db import get_session
from app.execution.service import diagnostics
from app.http.common import router
from app.models import Setting


class BackendPreference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["auto", "docker", "native"]


@router.get("/execution/status")
@router.post("/execution/diagnostics")
def execution_status(session: Session = Depends(get_session)):
    return diagnostics(session)


@router.put("/execution/preference")
def execution_preference(data: BackendPreference, session: Session = Depends(get_session)):
    row = session.get(Setting, "execution_backend")
    if not row:
        row = Setting(key="execution_backend")
        session.add(row)
    row.value = {"mode": data.mode}
    session.commit()
    audit(session, "execution.preference", {"mode": data.mode})
    return {"mode": data.mode}
