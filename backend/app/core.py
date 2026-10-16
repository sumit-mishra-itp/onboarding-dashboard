"""Pure domain logic and input models: no DB, no HTTP."""
from datetime import date, timedelta
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

Category = Literal["TECHNICAL_SETUP", "ACCESS_AND_TOOLS", "COMPLIANCE", "TEAM_AND_PROCESS", "ROLE_RAMP_UP", "ADMIN"]
Priority = Literal["HIGH", "MEDIUM", "LOW"]
TaskStatus = Literal["TO_DO", "IN_PROGRESS", "DONE", "BLOCKED"]
ConnectionStatus = Literal["PENDING", "SCHEDULED", "MET"]
Role = Literal["ADMIN", "HR", "MANAGER", "JOINEE"]

# Shared field types. Emails are normalised to lower case; URLs must be http(s) because they are rendered
# as links (a javascript: URL would run in the viewer's browser).
Email = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=254,
                                         pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
WebUrl = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000, pattern=r"^https?://\S+$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Password = Annotated[str, StringConstraints(min_length=10, max_length=128)]


class TaskIn(BaseModel):
    """One grid row. Same constraints as the AI output contract (BRD §12), so AI and manual tasks validate alike."""
    id: UUID | None = None
    title: str = Field(min_length=5, max_length=100)
    description: str = Field(default="", max_length=500)
    category: Category
    week_no: int = Field(ge=1, le=4)
    day_offset: int = Field(ge=0, le=30)
    priority: Priority = "MEDIUM"
    subtasks: list[str] = Field(default_factory=list, max_length=6)
    is_ai_generated: bool = False
    is_modified_by_manager: bool = False


class CertIn(BaseModel):
    id: UUID | None = None
    name: Name
    provider: Name
    url: WebUrl
    deadline: date
    is_mandatory: bool = True


class ConnIn(BaseModel):
    id: UUID | None = None
    contact_name: Name
    contact_email: Email
    contact_title: Name
    reason: str = Field(min_length=1, max_length=500)


def due_date(start: date, day_offset: int) -> date:
    return start + timedelta(days=day_offset)


def current_week(start: date, today: date) -> int:
    return max(1, min(4, (today - start).days // 7 + 1))


def metrics(tasks: list[dict], certs: list[dict], conns: list[dict], today: date) -> dict:
    """TSD §7.2. Completion % is None (not 0) when a plan has no tasks."""
    done = sum(t["status"] == "DONE" for t in tasks)
    overdue_tasks = sum(t["status"] != "DONE" and t["due_date"] is not None and today > t["due_date"] for t in tasks)
    overdue_certs = sum(not c["is_completed"] and today > c["deadline"] for c in certs)
    mandatory = [c for c in certs if c["is_mandatory"]]
    return {
        "task_completion_percentage": round(done / len(tasks) * 100) if tasks else None,
        "completed_tasks": done,
        "total_tasks": len(tasks),
        "completed_mandatory_certs": sum(c["is_completed"] for c in mandatory),
        "total_mandatory_certs": len(mandatory),
        "met_connections": sum(c["status"] == "MET" for c in conns),
        "total_connections": len(conns),
        "total_overdue_items": overdue_tasks + overdue_certs,
    }
