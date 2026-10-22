"""Stages 2–4 — Extractor, Planner, Reviewer agents. (M1–M3)"""

from pydantic import BaseModel

from app.config import settings
from app.pipeline.llm import structured_call
from app.schemas import Issue, Plan, Requirement, ReviewReport


class RequirementList(BaseModel):
    requirements: list[Requirement]


class IssueList(BaseModel):
    issues: list[Issue]


SYSTEM = "You are a senior tech lead turning software specifications into delivery plans."


def extract(spec_text: str) -> list[Requirement]:
    result = structured_call(
        model=settings.specwright_model_extract,
        system=SYSTEM,
        spec_text=spec_text,
        instruction=(
            "List every requirement in the spec, including those inside tables. "
            "Keep the spec's own IDs exactly; only when a requirement has none, assign REQ-001, "
            "REQ-002, … One requirement per item; do not merge or invent."
        ),
        output=RequirementList,
    )
    return result.requirements


def plan(spec_text: str, requirements: list[Requirement], language: str, feedback: str = "") -> Plan:
    reqs = "\n".join(f"- {r.req_id} [{r.type}] {r.text}" for r in requirements)
    instruction = (
        f"Requirements:\n{reqs}\n\n"
        "Produce milestones and tasks. Every requirement must be covered by at least one task; "
        "every task cites its requirement_ids. Label tasks BE, FE or QA. Estimates 1–8 points; "
        f"split anything bigger. Write titles and descriptions in '{language}'."
    )
    if feedback:
        instruction += f"\n\nFix these review issues from the previous attempt:\n{feedback}"
    return structured_call(
        model=settings.specwright_model_plan,
        system=SYSTEM,
        spec_text=spec_text,
        instruction=instruction,
        output=Plan,
    )


def critique(spec_text: str, draft: Plan) -> ReviewReport:
    result = structured_call(
        model=settings.specwright_model_review,
        system=SYSTEM,
        spec_text=spec_text,
        instruction=(
            f"Draft plan JSON:\n{draft.model_dump_json()}\n\n"
            "Report only duplicate tasks (kind=duplicate) and tasks too vague to start "
            "(kind=vague). Return an empty list if there are none."
        ),
        output=IssueList,
    )
    return ReviewReport(issues=result.issues)
