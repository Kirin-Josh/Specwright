"""Stages 2–4 — Extractor, Planner, Reviewer agents. (M1–M3)"""

import re
from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field

from app.config import settings
from app.pipeline.ingest import chunk_sections, to_prompt_text
from app.pipeline.llm import structured_call
from app.schemas import Issue, Requirement, SpecDocument, Task


class RequirementList(BaseModel):
    requirements: list[Requirement]


SYSTEM = "You are a senior tech lead turning software specifications into delivery plans."


EXTRACT_RULES = """\
Rules:
1. Numbered requirements. Return exactly one item per requirement ID and keep the ID exactly. \
Fold everything under that ID into its text: rules, lettered sub-points (a, b, c), tables, and \
for acceptance criteria the whole scenario (given / when / then) and its expected outcomes. \
Never split one ID into several items and never invent sub-IDs such as EF-01-a.
2. Not requirements, skip them: purpose and background; descriptions of how the software works \
today (wording like "currently", "existing", "already built", "in service", "actuel", \
"déjà", "en service"); lists of current limitations or constraints the new product must remove \
(they describe the starting point, often the opposite of the target); objectives; glossary; \
version history; tables of contents; traceability matrices; and every item in an out-of-scope \
section or stating that something is not required ("not in scope", "is not requested", \
"hors périmètre", "n'est pas demandé"), with or without an ID.
3. {numbering}
4. Type: use the family the spec files the requirement under (its chapter or ID prefix): \
functional → functional, security → security, technical or architecture → technical, \
acceptance criteria → acceptance. Prefixes usually encode the family, e.g. EF / FR = \
functional, ES / SEC = security, ET / TR / NFR = technical, CA / AC = acceptance.
5. Text: one or two sentences, written in the same language as the spec itself. For an \
acceptance criterion, end its text with the requirement IDs the spec says it covers, every ID \
written out (expand ranges such as "EF-05 to EF-08"), e.g. "Covers: EF-03, EF-05, ES-04".
Return an empty list if this part of the spec contains no requirements."""

NUMBERED = (
    "This spec numbers its requirements (ID prefixes: {prefixes}), so everything the product "
    "must do already has an ID. Unnumbered text is context, a definition or a detail of a "
    "numbered requirement: skip it. Expect few or no REQ-### items; add one (REQ-001, REQ-002, …) "
    "only for an explicit obligation on the new product that no numbered requirement covers."
)
UNNUMBERED = (
    "This spec does not number its requirements: give each requirement an ID REQ-001, REQ-002, …"
)


def spec_id_prefixes(doc: SpecDocument) -> list[str]:
    """Prefixes the spec uses for its own requirement IDs, e.g. ['CA', 'EF', 'ES'].

    Only IDs that open a heading, a line or a table row count, so references like
    "UT-CDC-SAAS-001" don't.
    """
    text = "\n".join(f"{s.heading}\n{s.markdown}" for s in doc.sections)
    counts = Counter(re.findall(r"^[-*|\s]*([A-Z]{2,4})-\d{2,3}\b", text, re.MULTILINE))
    return sorted(p for p, n in counts.items() if n >= 2 and p != "REQ")


def extract(doc: SpecDocument) -> list[Requirement]:
    chunks = chunk_sections(doc, settings.specwright_extract_chunk_chars)
    prefixes = spec_id_prefixes(doc)
    numbering = NUMBERED.format(prefixes=", ".join(prefixes)) if prefixes else UNNUMBERED
    instruction = (
        "List the requirements this part of the spec defines.\n\n"
        + EXTRACT_RULES.format(numbering=numbering)
    )
    found: dict[str, Requirement] = {}
    generated: list[Requirement] = []
    for chunk in chunks:
        result = structured_call(
            model=settings.specwright_model_extract,
            system=SYSTEM,
            spec_text=to_prompt_text(chunk),
            instruction=instruction,
            output=RequirementList,
            max_tokens=16000,
        )
        for r in result.requirements:
            if r.req_id.startswith("REQ-"):
                generated.append(r)
            else:
                # A spec ID seen again in a later chunk (e.g. a traceability table) keeps its
                # first, defining occurrence.
                found.setdefault(r.req_id, r)
    # Generated IDs restart at REQ-001 in every chunk; renumber them across the whole spec.
    for i, r in enumerate(generated, start=1):
        r.req_id = f"REQ-{i:03d}"
    return [*found.values(), *generated]


# --- Planner -------------------------------------------------------------------------------
# Planning runs in two steps so every call stays small: an outline that assigns requirements
# to milestones, then one call per milestone that writes its tasks.


class MilestoneOutline(BaseModel):
    id: str = Field(description="M1, M2, … in delivery order")
    name: str
    goal: str = Field(description="One sentence: what works at the end of this milestone")
    requirement_ids: list[str] = Field(min_length=1)


class Outline(BaseModel):
    milestones: list[MilestoneOutline]


class TaskList(BaseModel):
    tasks: list[Task]


class CritiqueIssue(BaseModel):
    kind: Literal["duplicate", "vague"]
    task_ids: list[str] = Field(min_length=1)
    detail: str = Field(description="One sentence: what is duplicated or missing")


class CritiqueList(BaseModel):
    issues: list[CritiqueIssue] = Field(description="Empty when there are no problems")


OUTLINE_RULES = """\
Group these requirements into delivery milestones. Rules:
1. Between 3 and 8 milestones, in delivery order (M1 first), each with at most 12 requirements. \
A milestone only relies on earlier milestones.
2. Foundations first: what most features build on, such as the data model, tenancy, \
authentication, roles and permissions, and background-job infrastructure.
3. Each milestone has one coherent theme and delivers something that can be demonstrated or \
tested end to end. Don't mix unrelated features to balance sizes.
4. Assign every requirement ID exactly once. A requirement of type acceptance lists the \
requirements it verifies ("verifies: …"): put it in the milestone that delivers the last of \
them, never earlier.
5. Put a technical or security requirement in the milestone that builds what it constrains \
(e.g. cash-recording rules with the cash features, file storage rules with attachments), or in \
the foundations if it applies everywhere. No catch-all milestone at the end.
6. Write names and goals in {language}."""

TASK_RULES = """\
Write the tasks for milestone {id} "{name}": {goal}
{earlier}
Rules:
1. Cover every requirement listed above. Each task lists in requirement_ids the requirements it \
implements or verifies, using only the IDs listed above, even when a requirement's text refers \
to other IDs (e.g. "verified by CA-05"): those belong to other milestones.
2. Plan deliverables, not the requirement list. A task is one coherent piece of work a \
developer can finish in 2 to 8 points (1 point ≈ half a day): for example a data model with its \
API and rules, or one screen. Group requirements that are built together; split work bigger \
than 8 points. Merge anything under 2 points into a related task. Don't redo a task that an \
earlier milestone already planned; build on it.
3. Every feature that users operate or see gets its FE screen task in the same milestone as \
its API, unless an earlier milestone already planned that screen.
4. Tests are part of the work: the task that builds a feature includes its unit and API tests \
in its description. Do not create separate test tasks for individual requirements, including \
security and technical ones: their tests live in the task that implements them.
5. Requirements of type acceptance are verified, not built. Each one gets exactly one QA task \
that automates its scenario end to end, and nothing else: the features it exercises are \
delivered by other tasks, in this or earlier milestones. Never re-implement them.
6. Label: BE for API, data, background jobs and infrastructure; FE for user-facing screens; \
QA only for the acceptance tasks of rule 5.
7. Title: an imperative phrase naming the deliverable. Description: what to build and how to \
know it is done, with the concrete rules, fields and edge cases from the requirements; do not \
just restate the title, and do not refer to other tasks by id.
8. Use ids T1, T2, … for these tasks and milestone_id "{id}". Set depends_on for every task \
that needs another task of this milestone first: a screen depends on its API, an API on its \
data model, a QA task on everything it verifies. In a typical milestone most tasks have at \
least one dependency. Only list tasks of this milestone; no cycles.
9. Priority: 1 = blocks other work or is security-critical, 2 = core feature, 3 = normal, \
4 = nice to have.
10. Write titles and descriptions in {language}."""

CRITIQUE_RULES = """\
Review these tasks of milestone {id} "{name}" against the requirements above. Report only:
- duplicate: two or more tasks that build the same thing (list all their task_ids).
- vague: a task whose description does not say what to build or how to check it is done.
Do not report estimates, coverage, labels or style; they are checked elsewhere. Use the task \
ids exactly as given. Every issue names at least one task and says in one sentence what is \
duplicated or missing. When there are no such problems, return an empty issues list; never add \
an item saying that nothing was found."""


def verified_ids(criterion: Requirement, requirements: list[Requirement]) -> list[str]:
    """Requirement IDs an acceptance criterion cites, i.e. what it verifies."""
    # Acceptance criteria mentioning each other is context, not something they verify.
    known = {r.req_id for r in requirements if r.type != "acceptance"}
    cited = dict.fromkeys(re.findall(r"\b[A-Z]{2,4}-\d{2,3}\b", criterion.text))
    return [rid for rid in cited if rid in known]


def format_requirements(requirements: list[Requirement], max_chars: int | None = None) -> str:
    lines = []
    for r in requirements:
        flat = " ".join(r.text.split())  # one requirement per line
        text = flat if max_chars is None else flat[:max_chars]
        line = f"- {r.req_id} [{r.type}] {text}"
        # Keep what an acceptance criterion verifies even when its text is shortened.
        if r.type == "acceptance" and (cited := verified_ids(r, requirements)):
            line += f" (verifies: {', '.join(cited)})"
        lines.append(line)
    return "\n".join(lines)


def outline(requirements: list[Requirement], language: str, feedback: str = "") -> Outline:
    instruction = OUTLINE_RULES.format(language=language)
    if feedback:
        instruction += f"\n\nFix these problems from the previous attempt:\n{feedback}"
    return structured_call(
        model=settings.specwright_model_plan,
        system=SYSTEM,
        # A short excerpt per requirement keeps the whole list within small context limits.
        spec_text=f"Requirements:\n{format_requirements(requirements, max_chars=140)}",
        instruction=instruction,
        output=Outline,
        max_tokens=8000,
    )


def plan_milestone(
    milestone: MilestoneOutline,
    requirements: list[Requirement],
    earlier: list[MilestoneOutline],
    language: str,
    feedback: str = "",
    earlier_tasks: list[Task] | None = None,
) -> list[Task]:
    done = "\n".join(f"- {m.id} {m.name}: {m.goal}" for m in earlier)
    planned = "\n".join(f"- [{t.label}] {t.title}" for t in earlier_tasks or [])
    context = ""
    if done:
        context += f"Already delivered by earlier milestones:\n{done}\n"
    if planned:
        context += f"Tasks already planned in earlier milestones (don't redo them):\n{planned}\n"
    instruction = TASK_RULES.format(
        id=milestone.id,
        name=milestone.name,
        goal=milestone.goal,
        earlier=context,
        language=language,
    )
    if feedback:
        instruction += f"\n\nFix these problems from the previous attempt:\n{feedback}"
    result = structured_call(
        model=settings.specwright_model_plan,
        system=SYSTEM,
        spec_text=f"Requirements for this milestone:\n{format_requirements(requirements)}",
        instruction=instruction,
        output=TaskList,
        max_tokens=12000,
    )
    return result.tasks


def critique_milestone(
    milestone: MilestoneOutline, requirements: list[Requirement], tasks: list[Task]
) -> list[Issue]:
    listing = "\n".join(
        f"- {t.id} [{t.label}] {t.title}: {t.description} (requirements: "
        f"{', '.join(t.requirement_ids)})"
        for t in tasks
    )
    result = structured_call(
        model=settings.specwright_model_review,
        system=SYSTEM,
        spec_text=f"Requirements:\n{format_requirements(requirements)}\n\nTasks:\n{listing}",
        instruction=CRITIQUE_RULES.format(id=milestone.id, name=milestone.name),
        output=CritiqueList,
        max_tokens=6000,
    )
    # Drop references to tasks outside this milestone; an issue left without tasks is noise.
    ids = {t.id for t in tasks}
    issues = []
    for i in result.issues:
        task_ids = [t for t in i.task_ids if t in ids]
        if task_ids:
            issues.append(Issue(kind=i.kind, detail=i.detail, task_ids=task_ids))
    return issues
