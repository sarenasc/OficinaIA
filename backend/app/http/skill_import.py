"""Import skill definitions atomically, without granting agent permissions."""
from fastapi import Depends
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app import schemas as s
from app.core.audit import audit
from app.core.db import get_session
from app.http.common import router


class SkillBatch(s.Input):
    version: int = Field(default=1, ge=1, le=1)
    skills: list[s.SkillInput] = Field(min_length=1, max_length=100)


@router.post("/skills/import")
def import_skills(batch: SkillBatch, preview: bool = True, session: Session = Depends(get_session)):
    names = {name.strip().casefold() for name in session.scalars(select(m.Skill.name))}
    parsed, summaries = [], []
    for entry in batch.skills:
        name = entry.name.strip()
        if not name or name.casefold() in names:
            raise ValueError(f"Nombre vacío o habilidad duplicada: {name}")
        if not entry.instructions.strip():
            raise ValueError(f"La habilidad {name} necesita instructions (procedimiento / conocimiento)")
        names.add(name.casefold())
        tools, tool_names = [], []
        for reference in entry.required_tools:
            tool = session.get(m.Tool, reference) or session.scalar(select(m.Tool).where(m.Tool.name == reference))
            if not tool or not tool.active:
                raise ValueError(f"Herramienta inexistente o inactiva: {reference}")
            if tool.id not in tools:
                tools.append(tool.id)
                tool_names.append(tool.name)
        data = entry.model_dump()
        data.update(name=name, required_tools=tools)
        parsed.append(data)
        summaries.append({**data, "required_tools": tool_names})
    result = {"count": len(parsed), "skills": summaries, "created": False}
    if preview:
        return result
    try:
        created = [m.Skill(**data) for data in parsed]
        session.add_all(created)
        session.commit()
    except Exception:
        session.rollback()
        raise
    audit(session, "skills.imported", {"count": len(created), "ids": [skill.id for skill in created]})
    return {**result, "created": True, "ids": [skill.id for skill in created]}
