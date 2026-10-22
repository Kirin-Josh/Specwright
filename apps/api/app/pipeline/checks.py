"""Deterministic plan checks — run before any LLM critique. (M3)"""

from app.schemas import Issue, Plan, Requirement, ReviewReport


def run_checks(plan: Plan, requirements: list[Requirement]) -> ReviewReport:
    issues: list[Issue] = []
    req_ids = {r.req_id for r in requirements}
    task_ids = {t.id for t in plan.tasks}
    milestone_ids = {m.id for m in plan.milestones}

    covered = {rid for t in plan.tasks for rid in t.requirement_ids}
    for rid in sorted(req_ids - covered):
        issues.append(Issue(kind="uncovered", detail=f"{rid} has no task", requirement_ids=[rid]))

    for t in plan.tasks:
        unknown = [rid for rid in t.requirement_ids if rid not in req_ids]
        if unknown:
            issues.append(
                Issue(kind="orphan", detail=f"cites unknown {unknown}", task_ids=[t.id])
            )
        if t.milestone_id not in milestone_ids:
            issues.append(
                Issue(kind="orphan", detail=f"unknown milestone {t.milestone_id}", task_ids=[t.id])
            )
        missing = [d for d in t.depends_on if d not in task_ids]
        if missing:
            issues.append(
                Issue(kind="orphan", detail=f"depends on missing {missing}", task_ids=[t.id])
            )

    if cycle := find_cycle(plan):
        issues.append(Issue(kind="cycle", detail=" -> ".join(cycle), task_ids=cycle))

    return ReviewReport(issues=issues)


def find_cycle(plan: Plan) -> list[str] | None:
    graph = {t.id: t.depends_on for t in plan.tasks}
    state: dict[str, int] = {}  # 1 = visiting, 2 = done
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        stack.append(node)
        for nxt in graph.get(node, []):
            if state.get(nxt) == 1:
                return stack[stack.index(nxt):] + [nxt]
            if nxt in graph and not state.get(nxt):
                if found := visit(nxt):
                    return found
        stack.pop()
        state[node] = 2
        return None

    for node in graph:
        if not state.get(node):
            if found := visit(node):
                return found
    return None
