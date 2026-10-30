"""Deterministic plan checks — run before any LLM critique. (M3)"""

from app.schemas import Issue, Label, Plan, Requirement, RequirementType, ReviewReport


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

    # When the spec has acceptance criteria, QA tasks automate those; testing anything else
    # belongs inside the implementation tasks, otherwise it duplicates the acceptance tests.
    acceptance = {r.req_id for r in requirements if r.type == RequirementType.acceptance}
    if acceptance:
        for t in plan.tasks:
            if t.label == Label.QA and not acceptance & set(t.requirement_ids):
                issues.append(Issue(
                    kind="duplicate", task_ids=[t.id],
                    detail="QA task that verifies no acceptance criterion; remove it and keep "
                           "its testing inside the implementation tasks",
                ))

    if cycle := find_cycle(plan):
        issues.append(Issue(kind="cycle", detail=" -> ".join(cycle), task_ids=cycle))
    issues += dependency_issues(plan)

    return ReviewReport(issues=issues)


def dependency_issues(plan: Plan) -> list[Issue]:
    """A QA task needs something to test; a FE task needs the BE task of its own milestone that
    serves the same requirement (directly or through other dependencies)."""
    issues: list[Issue] = []
    graph = {t.id: t.depends_on for t in plan.tasks}
    for t in plan.tasks:
        if t.label == Label.QA and not t.depends_on:
            issues.append(Issue(
                kind="dependency", task_ids=[t.id],
                detail="QA task depends on nothing; add the tasks it verifies to depends_on",
            ))
        if t.label != Label.FE:
            continue
        backends = sorted(b.id for b in plan.tasks if b.label == Label.BE
                          and b.milestone_id == t.milestone_id
                          and set(b.requirement_ids) & set(t.requirement_ids))
        if backends and not set(backends) & ancestors(graph, t.id):
            issues.append(Issue(
                kind="dependency", task_ids=[t.id],
                detail=f"FE task doesn't depend on {', '.join(backends)}, the BE work for the "
                       "same requirement; add the one it calls to depends_on",
            ))
    return issues


def ancestors(graph: dict[str, list[str]], node: str) -> set[str]:
    seen: set[str] = set()
    todo = list(graph.get(node, []))
    while todo:
        d = todo.pop()
        if d not in seen:
            seen.add(d)
            todo += graph.get(d, [])
    return seen


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
