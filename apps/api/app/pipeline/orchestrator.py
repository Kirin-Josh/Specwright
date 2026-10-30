"""Hand-written pipeline state machine. Persistence and job queue are wired in M0/M1."""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.pipeline import agents
from app.pipeline.agents import MilestoneOutline, Outline
from app.pipeline.checks import run_checks
from app.pipeline.ingest import ingest, to_prompt_text
from app.schemas import Issue, Milestone, Plan, Requirement, ReviewReport, Task

MAX_FIX_ROUNDS = 2

Log = Callable[[str], None]


@dataclass
class RunState:
    spec_text: str = ""
    requirements: list[Requirement] = field(default_factory=list)
    outline: Outline | None = None
    plan: Plan | None = None
    review: ReviewReport | None = None
    stage: str = "created"


def run_pipeline(path: Path, language: str = "en") -> RunState:
    state = RunState()

    doc = ingest(path)
    state.spec_text = to_prompt_text(doc)
    state.stage = "ingested"

    state.requirements = agents.extract(doc)
    state.stage = "extracted"

    state.outline, state.plan, state.review = build_plan(state.requirements, language)
    state.stage = "reviewed"  # next: human review in the web app, then Linear sync (M5)
    return state


def build_plan(
    requirements: list[Requirement], language: str, log: Log = lambda _: None
) -> tuple[Outline, Plan, ReviewReport]:
    """Outline → tasks per milestone → checks → critique; re-plan only milestones with issues."""
    by_id = {r.req_id: r for r in requirements}
    outline = make_outline(requirements, language, log)
    milestones = outline.milestones

    def reqs_of(m: MilestoneOutline) -> list[Requirement]:
        return [by_id[rid] for rid in m.requirement_ids]

    drafts: dict[str, list[Task]] = {}

    def draft(i: int, feedback: str = "") -> list[Task]:
        m = milestones[i]
        log(f"plan: {m.id} {m.name} ({len(m.requirement_ids)} requirements)"
            + (" — fixing" if feedback else ""))
        earlier_tasks = [t for e in milestones[:i] for t in drafts.get(e.id, [])]
        tasks = agents.plan_milestone(m, reqs_of(m), milestones[:i], language, feedback,
                                      earlier_tasks)
        return drop_foreign(m, tasks, log)

    # In order, so each milestone sees the tasks planned before it.
    for i, m in enumerate(milestones):
        drafts[m.id] = draft(i)

    owner = {rid: m.id for m in milestones for rid in m.requirement_ids}
    for round_no in range(MAX_FIX_ROUNDS + 1):
        plan, origin = assemble(outline, drafts)
        review = run_checks(plan, requirements)
        review.issues += ownership_issues(plan, owner)
        log(f"checks: {len(review.issues)} issues")
        if review.ok:
            issues: list[Issue] = []
            for m in milestones:
                tasks = [t for t in plan.tasks if t.milestone_id == m.id]
                issues += agents.critique_milestone(m, reqs_of(m), tasks)
            review = ReviewReport(issues=issues)
            log(f"critique: {len(review.issues)} issues")
        if review.ok or round_no == MAX_FIX_ROUNDS:
            return outline, plan, review

        for i, m in enumerate(milestones):
            notes = feedback_for(m.id, review.issues, origin, owner, drafts[m.id])
            if notes:
                drafts[m.id] = draft(i, notes)

    raise AssertionError("unreachable")


def drop_foreign(m: MilestoneOutline, tasks: list[Task], log: Log) -> list[Task]:
    """Strip other milestones' requirement IDs from a draft and delete tasks left with none:
    their work belongs to another milestone. The model tends to ignore feedback asking this."""
    own = set(m.requirement_ids)
    kept: list[Task] = []
    for t in tasks:
        reqs = [rid for rid in t.requirement_ids if rid in own]
        if reqs:
            kept.append(t.model_copy(update={"requirement_ids": reqs}))
    dropped = {t.id for t in tasks} - {t.id for t in kept}
    if dropped:
        log(f"repair: {m.id} dropped {len(dropped)} tasks citing only other milestones' requirements")
    return [t.model_copy(update={"depends_on": [d for d in t.depends_on if d not in dropped]})
            for t in kept]


def ownership_issues(plan: Plan, owner: dict[str, str]) -> list[Issue]:
    """Tasks must only cite requirements of their own milestone, and each milestone must cover
    its own requirements; otherwise a later milestone skips work it thinks is already done."""
    issues = []
    covered_in = {(t.milestone_id, rid) for t in plan.tasks for rid in t.requirement_ids}
    for t in plan.tasks:
        foreign = [rid for rid in t.requirement_ids if owner.get(rid, t.milestone_id) != t.milestone_id]
        if foreign:
            issues.append(Issue(
                kind="orphan", task_ids=[t.id],
                detail=f"cites {', '.join(foreign)}, which belong to "
                       f"{', '.join(sorted({owner[r] for r in foreign}))}; remove them",
            ))
    # Requirements with no task at all are already reported by run_checks as uncovered.
    cited_anywhere = {rid for t in plan.tasks for rid in t.requirement_ids}
    for rid, mid in owner.items():
        if rid in cited_anywhere and (mid, rid) not in covered_in:
            issues.append(Issue(
                kind="uncovered", requirement_ids=[rid],
                detail=f"{rid} has no task in {mid}, the milestone it belongs to",
            ))
    return issues


def make_outline(requirements: list[Requirement], language: str, log: Log) -> Outline:
    """Ask for an outline until every requirement is assigned exactly once and every acceptance
    criterion comes after what it verifies; repair whatever is still wrong after that."""
    known = [r.req_id for r in requirements]
    known_set = set(known)
    verifies = {r.req_id: agents.verified_ids(r, requirements)
                for r in requirements if r.type == "acceptance"}
    feedback = ""
    result = agents.outline(requirements, language)
    for round_no in range(MAX_FIX_ROUNDS + 1):
        if round_no:
            result = agents.outline(requirements, language, feedback)
        assigned = [rid for m in result.milestones for rid in m.requirement_ids]
        missing = [rid for rid in known if rid not in assigned]
        unknown = sorted({rid for rid in assigned if rid not in known_set})
        repeated = sorted({rid for rid in assigned if assigned.count(rid) > 1})
        early = too_early(result, verifies)
        log(f"outline: {len(result.milestones)} milestones, {len(missing)} missing, "
            f"{len(unknown)} unknown, {len(repeated)} repeated, {len(early)} acceptance too early")
        if not (missing or unknown or repeated or early):
            return result
        feedback = "\n".join(
            line for line in (
                f"- Not assigned to any milestone: {', '.join(missing)}" if missing else "",
                f"- Not in the requirement list: {', '.join(unknown)}" if unknown else "",
                f"- Assigned more than once: {', '.join(repeated)}" if repeated else "",
                *(f"- {a} is in {m} but verifies {', '.join(later)}, which come later"
                  for a, (m, later) in early.items()),
            ) if line
        )

    # Still imperfect: drop unknown and repeated IDs, put missing ones in the last milestone.
    seen: set[str] = set()
    for m in result.milestones:
        kept = []
        for rid in m.requirement_ids:
            if rid in known_set and rid not in seen:
                kept.append(rid)
                seen.add(rid)
        m.requirement_ids = kept
    result.milestones = [m for m in result.milestones if m.requirement_ids]
    result.milestones[-1].requirement_ids += [rid for rid in known if rid not in seen]
    # Move acceptance criteria that are still too early to the milestone of their last dependency.
    for criterion in too_early(result, verifies):
        index = milestone_index(result)
        target = max(index[rid] for rid in verifies[criterion] if rid in index)
        for m in result.milestones:
            if criterion in m.requirement_ids:
                m.requirement_ids.remove(criterion)
        result.milestones[target].requirement_ids.append(criterion)
    result.milestones = [m for m in result.milestones if m.requirement_ids]
    return result


def milestone_index(outline: Outline) -> dict[str, int]:
    return {rid: i for i, m in enumerate(outline.milestones) for rid in m.requirement_ids}


def too_early(
    outline: Outline, verifies: dict[str, list[str]]
) -> dict[str, tuple[str, list[str]]]:
    """Acceptance criteria placed before something they verify: criterion → (milestone, later)."""
    index = milestone_index(outline)
    early = {}
    for criterion, verified in verifies.items():
        if criterion not in index:
            continue
        at = index[criterion]
        later = [rid for rid in verified if index.get(rid, -1) > at]
        if later:
            early[criterion] = (outline.milestones[at].id, later)
    return early


def assemble(
    outline: Outline, drafts: dict[str, list[Task]]
) -> tuple[Plan, dict[str, tuple[str, str]]]:
    """Number tasks T-001… across milestones; return the plan and global id → (milestone, local id)."""
    tasks: list[Task] = []
    origin: dict[str, tuple[str, str]] = {}
    n = 0
    for m in outline.milestones:
        local_to_global: dict[str, str] = {}
        for t in drafts[m.id]:
            n += 1
            local_to_global[t.id] = f"T-{n:03d}"
        def to_global(text: str) -> str:
            return re.sub(r"\bT\d+\b", lambda x: local_to_global.get(x.group(0), x.group(0)), text)

        for t in drafts[m.id]:
            gid = local_to_global[t.id]
            origin[gid] = (m.id, t.id)
            # Unknown dependencies are kept as written so checks report them.
            deps = [local_to_global.get(d, d) for d in t.depends_on]
            tasks.append(t.model_copy(update={
                "id": gid, "milestone_id": m.id, "depends_on": deps,
                "title": to_global(t.title), "description": to_global(t.description),
            }))
    milestones = [Milestone(id=m.id, name=m.name, goal=m.goal) for m in outline.milestones]
    return Plan(milestones=milestones, tasks=tasks), origin


def feedback_for(
    milestone_id: str,
    issues: list[Issue],
    origin: dict[str, tuple[str, str]],
    owner: dict[str, str],
    previous: list[Task],
) -> str:
    """Issues that concern one milestone, in its local task ids, plus its previous draft."""
    to_local = {gid: local for gid, (mid, local) in origin.items() if mid == milestone_id}
    notes = []
    for issue in issues:
        mine = [to_local[t] for t in issue.task_ids if t in to_local]
        reqs = [r for r in issue.requirement_ids if owner.get(r) == milestone_id]
        if not (mine or reqs):
            continue
        detail = issue.detail
        for gid, local in to_local.items():
            detail = detail.replace(gid, local)
        where = ", ".join(mine + reqs)
        notes.append(f"- [{issue.kind}] {where}: {detail}")
    if not notes:
        return ""
    draft = "\n".join(f"- {t.id} {t.title} (requirements: {', '.join(t.requirement_ids)})"
                      for t in previous)
    return "Your previous tasks:\n" + draft + "\n\nProblems:\n" + "\n".join(notes)
