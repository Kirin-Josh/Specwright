from enum import StrEnum

from pydantic import BaseModel, Field


class RequirementType(StrEnum):
    functional = "functional"
    security = "security"
    technical = "technical"
    acceptance = "acceptance"


class Requirement(BaseModel):
    req_id: str = Field(description="Spec's own ID (e.g. EF-01) or generated REQ-###")
    text: str
    type: RequirementType
    section: str


class SpecSection(BaseModel):
    heading: str
    markdown: str


class SpecDocument(BaseModel):
    title: str
    language: str = "en"
    sections: list[SpecSection]


class Label(StrEnum):
    BE = "BE"
    FE = "FE"
    QA = "QA"


class Task(BaseModel):
    id: str = Field(description="Stable local ID, e.g. T-001")
    milestone_id: str
    title: str
    description: str
    label: Label
    estimate: int = Field(ge=1, le=8, description="Points")
    priority: int = Field(ge=1, le=4, description="1 = urgent, 4 = low")
    requirement_ids: list[str] = Field(min_length=1)
    depends_on: list[str] = []


class Milestone(BaseModel):
    id: str = Field(description="e.g. M1")
    name: str
    goal: str


class Plan(BaseModel):
    milestones: list[Milestone]
    tasks: list[Task]


class Issue(BaseModel):
    kind: str = Field(description="uncovered | orphan | cycle | dependency | estimate | duplicate | vague")
    detail: str
    task_ids: list[str] = []
    requirement_ids: list[str] = []


class ReviewReport(BaseModel):
    issues: list[Issue]

    @property
    def ok(self) -> bool:
        return not self.issues


class SyncItem(BaseModel):
    kind: str = Field(description="label | project | milestone | issue | relation")
    title: str
    action: str = Field(description="create | update")


class SyncResult(BaseModel):
    created: int
    updated: int
    project_url: str


class SyncMap(BaseModel):
    """Linear IDs of everything already pushed for one run; looked up before any create."""

    team_id: str = ""
    project_id: str = ""
    project_url: str = ""
    labels: dict[str, str] = {}
    milestones: dict[str, str] = {}  # plan milestone ID -> Linear project milestone ID
    issues: dict[str, str] = {}  # task ID -> Linear issue ID
    relations: list[tuple[str, str]] = []  # (blocking task ID, blocked task ID)
