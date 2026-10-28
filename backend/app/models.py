"""Relational domain model; names and roles are user-owned data."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Entity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Office(Entity, Base):
    __tablename__ = "offices"
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(50), default="building")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    visual: Mapped[dict] = mapped_column(JSON, default=dict)
    coordinator_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Area(Entity, Base):
    __tablename__ = "areas"
    office_id: Mapped[str] = mapped_column(ForeignKey("offices.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")


class Provider(Entity, Base):
    __tablename__ = "providers"
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30), default="ollama")
    url: Mapped[str] = mapped_column(String(500), default="http://127.0.0.1:11434")
    default_model: Mapped[str] = mapped_column(String(200), default="")
    credential_ref: Mapped[str | None] = mapped_column(String(36), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    pricing: Mapped[dict] = mapped_column(JSON, default=dict)


class Agent(Entity, Base):
    __tablename__ = "agents"
    office_id: Mapped[str] = mapped_column(ForeignKey("offices.id", ondelete="CASCADE"))
    area_id: Mapped[str | None] = mapped_column(ForeignKey("areas.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    role: Mapped[str] = mapped_column(String(200), default="")
    goal: Mapped[str] = mapped_column(Text, default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id", ondelete="SET NULL"), nullable=True)
    model: Mapped[str] = mapped_column(String(200), default="")
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    context_limit: Mapped[int] = mapped_column(Integer, default=8192)
    mode: Mapped[str] = mapped_column(String(20), default="safe")
    external_policy: Mapped[str] = mapped_column(String(20), default="never")
    fallbacks: Mapped[list] = mapped_column(JSON, default=list)
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    rules: Mapped[str] = mapped_column(Text, default="")
    memory_mode: Mapped[str] = mapped_column(String(20), default="off")
    status: Mapped[str] = mapped_column(String(30), default="active")
    position: Mapped[dict] = mapped_column(JSON, default=lambda: {"x": 100, "y": 100})


class AgentRelation(Entity, Base):
    __tablename__ = "agent_relations"
    __table_args__ = (UniqueConstraint("source_id", "target_id"),)
    source_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    target_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))


class Tool(Entity, Base):
    __tablename__ = "tools"
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(50))
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    required_permissions: Mapped[list] = mapped_column(JSON, default=list)
    timeout: Mapped[int] = mapped_column(Integer, default=60)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    builtin: Mapped[bool] = mapped_column(Boolean, default=False)


class Resource(Entity, Base):
    __tablename__ = "resources"
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(50), default="directory")
    path: Mapped[str] = mapped_column(String(1000))
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Connection(Entity, Base):
    __tablename__ = "connections"
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30), default="sqlserver")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    credential_ref: Mapped[str | None] = mapped_column(String(36), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Skill(Entity, Base):
    __tablename__ = "skills"
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    required_tools: Mapped[list] = mapped_column(JSON, default=list)
    examples: Mapped[str] = mapped_column(Text, default="")
    output_format: Mapped[str] = mapped_column(Text, default="")


class AgentTool(Base):
    __tablename__ = "agent_tools"
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    tool_id: Mapped[str] = mapped_column(ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True)


class AgentResource(Base):
    __tablename__ = "agent_resources"
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True)
    permissions: Mapped[list] = mapped_column(JSON, default=list)


class AgentConnection(Base):
    __tablename__ = "agent_connections"
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("connections.id", ondelete="CASCADE"), primary_key=True)
    permissions: Mapped[list] = mapped_column(JSON, default=list)


class AgentSkill(Base):
    __tablename__ = "agent_skills"
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)


class Procedure(Entity, Base):
    __tablename__ = "procedures"
    office_id: Mapped[str] = mapped_column(ForeignKey("offices.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    steps: Mapped[list] = mapped_column(JSON, default=list)


class Task(Entity, Base):
    __tablename__ = "tasks"
    number: Mapped[str] = mapped_column(String(100), unique=True)
    office_id: Mapped[str] = mapped_column(ForeignKey("offices.id"))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    request: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)


class Execution(Entity, Base):
    __tablename__ = "executions"
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    tool_name: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(30), default="running")
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    provider: Mapped[str] = mapped_column(String(100), default="")
    model: Mapped[str] = mapped_column(String(200), default="")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)


class Message(Entity, Base):
    __tablename__ = "messages"
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    source_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    target_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="sent")


class AuditEvent(Entity, Base):
    __tablename__ = "audit_events"
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class Artifact(Entity, Base):
    __tablename__ = "artifacts"
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id"))
    path: Mapped[str] = mapped_column(String(1000))
    name: Mapped[str] = mapped_column(String(300))


class Memory(Entity, Base):
    __tablename__ = "memories"
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    content: Mapped[str] = mapped_column(Text)


class Approval(Entity, Base):
    __tablename__ = "approvals"
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    reason: Mapped[str] = mapped_column(Text)
    key: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
