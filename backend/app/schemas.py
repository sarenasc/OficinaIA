from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_max_length=2000000)


class OfficeInput(Input):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    icon: str = "building"
    active: bool = True
    visual: dict = Field(default_factory=dict)
    coordinator_id: str | None = None


class AreaInput(Input):
    name: str = Field(min_length=1, max_length=200)
    office_id: str
    description: str = ""


class AgentInput(Input):
    name: str = Field(min_length=1, max_length=200)
    office_id: str
    area_id: str | None = None
    description: str = ""
    role: str = ""
    goal: str = ""
    instructions: str = ""
    provider_id: str | None = None
    model: str = ""
    temperature: float = Field(default=0.2, ge=0, le=2)
    context_limit: int = Field(default=8192, ge=1024, le=262144)
    mode: Literal["safe", "trusted"] = "safe"
    external_policy: Literal["never", "ask", "auto"] = "never"
    fallbacks: list[dict] = Field(default_factory=list, max_length=5)
    permissions: list[str] = Field(default_factory=list)
    rules: str = ""
    memory_mode: Literal["off", "session", "persistent"] = "off"
    status: Literal["active", "disabled", "working", "waiting", "error"] = "active"
    position: dict[str, float] = Field(default_factory=lambda: {"x": 100, "y": 100})


class ProviderInput(Input):
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["ollama", "openai", "anthropic", "gemini"] = "ollama"
    url: str = "http://127.0.0.1:11434"
    default_model: str = ""
    active: bool = True
    pricing: dict = Field(default_factory=dict)


class ToolInput(Input):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]*$")
    description: str = ""
    kind: Literal[
        "custom.sql",
        "custom.python",
        "filesystem.read",
        "filesystem.write",
        "filesystem.create_directory",
        "csv.read",
        "data.summarize",
        "excel.create",
        "excel.read",
        "excel.chart",
        "filesystem.list",
        "excel.generate_sales",
        "excel.from_csv",
        "sql.export_excel",
        "sql.describe",
        "social.prepare_post",
        "python.execute",
        "sports.analyze",
        "sql.query",
        "sql.execute",
        "web.search",
        "web.fetch",
        "web.download",
        "api.request",
        "python.packages",
        "pdf.create",
        "pdf.read",
        "pdf.merge",
        "agents.list",
        "tasks.status",
    ]
    parameters: dict = Field(
        default_factory=lambda: {"type": "object", "properties": {}, "additionalProperties": False}
    )
    config: dict = Field(default_factory=dict)
    required_permissions: list[str] = Field(default_factory=list)
    timeout: int = Field(default=60, ge=1, le=300)
    active: bool = True


class ResourceInput(Input):
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["directory", "network_directory", "file", "application", "server", "url", "custom"] = "directory"
    path: str = Field(min_length=1, max_length=1000)
    description: str = ""
    active: bool = True


class ConnectionInput(Input):
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["sqlserver", "postgresql", "mysql", "sqlite", "http_api", "web_search"] = "sqlserver"
    config: dict = Field(default_factory=dict)
    active: bool = True


class SkillInput(Input):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    instructions: str = ""
    required_tools: list[str] = Field(default_factory=list)
    examples: str = ""
    output_format: str = ""


class ProcedureInput(Input):
    name: str = Field(min_length=1, max_length=200)
    office_id: str
    description: str = ""
    steps: list[dict] = Field(min_length=1, max_length=20)


class RelationInput(Input):
    source_id: str
    target_id: str


class AssignmentInput(Input):
    tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    resources: list[dict] = Field(default_factory=list)
    connections: list[dict] = Field(default_factory=list)


class TaskInput(Input):
    office_id: str
    agent_id: str
    request: str = Field(min_length=1, max_length=50000)
    priority: int = Field(default=0, ge=0, le=10)
    procedure_id: str | None = None
    inputs: dict = Field(default_factory=dict)


class ApprovalInput(Input):
    approved: bool


class SecretInput(Input):
    value: str = Field(min_length=1, max_length=10000)
