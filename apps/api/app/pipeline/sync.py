"""Linear sync (M5): push an approved plan as labels → project → milestones → issues → relations.

Idempotent: every Linear ID created is recorded in the SyncMap and saved right away, so a re-run
(or a run resumed after a crash) updates what exists instead of creating duplicates.
A dry run walks the same path with writes switched off and returns what it would do.
Tasks removed from the plan after a push are left alone in Linear.
"""

from collections.abc import Callable
from typing import Any, Protocol

from app.linear import Team
from app.schemas import Label, Plan, Requirement, SyncItem, SyncMap, SyncResult, Task

LABEL_COLORS = {Label.BE: "#4ea7fc", Label.FE: "#bb87fc", Label.QA: "#4cb782"}

# Point values each Linear estimation scale accepts (t-shirt sizes are stored as numbers too).
ESTIMATE_SCALES = {
    "exponential": [1, 2, 4, 8, 16],
    "fibonacci": [1, 2, 3, 5, 8],
    "linear": [1, 2, 3, 4, 5],
    "tShirt": [1, 2, 3, 5, 8],
}


class SyncError(Exception):
    pass


class Linear(Protocol):
    def find_team(self, key: str) -> Team | None: ...
    def find_label(self, team_id: str, name: str) -> str | None: ...
    def create_label(self, team_id: str, name: str, color: str) -> str: ...
    def create_project(self, team_id: str, name: str, description: str) -> tuple[str, str]: ...
    def update_project(self, project_id: str, name: str, description: str) -> str: ...
    def create_milestone(self, project_id: str, name: str, description: str) -> str: ...
    def update_milestone(self, milestone_id: str, name: str, description: str) -> None: ...
    def create_issue(self, fields: dict[str, Any]) -> str: ...
    def update_issue(self, issue_id: str, fields: dict[str, Any]) -> None: ...
    def create_relation(self, blocking_issue_id: str, blocked_issue_id: str) -> None: ...


def linear_estimate(points: int, estimation_type: str) -> int | None:
    """Nearest value on the team's scale (rounding up on ties); None if estimates are off."""
    scale = ESTIMATE_SCALES.get(estimation_type)
    if scale is None:
        return None
    return min(scale, key=lambda v: (abs(v - points), -v))


def issue_description(task: Task, requirements: dict[str, Requirement]) -> str:
    lines = [task.description, "", "**Requirements**"]
    for rid in task.requirement_ids:
        r = requirements.get(rid)
        lines.append(f"- **{rid}** — {r.text}" if r else f"- **{rid}**")
    lines += ["", f"_Specwright task {task.id} · {task.estimate} pts_"]
    return "\n".join(lines)


def summarize(items: list[SyncItem], sync_map: SyncMap) -> SyncResult:
    return SyncResult(
        created=sum(i.action == "create" for i in items),
        updated=sum(i.action == "update" for i in items),
        project_url=sync_map.project_url,
    )


def sync_plan(
    plan: Plan,
    requirements: list[Requirement],
    title: str,
    team_key: str,
    client: Linear,
    sync_map: SyncMap,
    save: Callable[[SyncMap], None] = lambda _: None,
    dry_run: bool = False,
) -> list[SyncItem]:
    team = client.find_team(team_key)
    if team is None:
        raise SyncError(f"no Linear team with key {team_key!r}")
    if sync_map.team_id and sync_map.team_id != team.id:
        raise SyncError("this plan was already pushed to another team; delete its sync map "
                        "to push a fresh copy")
    if dry_run:
        sync_map, save = sync_map.model_copy(deep=True), lambda _: None
    sync_map.team_id = team.id
    items: list[SyncItem] = []

    def plan_step(kind: str, name: str, exists: bool) -> bool:
        """Record the step; True when it should actually run."""
        items.append(SyncItem(kind=kind, title=name, action="update" if exists else "create"))
        return not dry_run

    for label in sorted({t.label for t in plan.tasks}):
        if label in sync_map.labels:
            continue
        existing = client.find_label(team.id, label)
        if existing:
            sync_map.labels[label] = existing
        elif plan_step("label", label, exists=False):
            sync_map.labels[label] = client.create_label(team.id, label, LABEL_COLORS[label])
        save(sync_map)

    description = f"Planned by Specwright: {len(plan.milestones)} milestones, " \
                  f"{len(plan.tasks)} tasks."
    if plan_step("project", title, exists=bool(sync_map.project_id)):
        if sync_map.project_id:
            sync_map.project_url = client.update_project(sync_map.project_id, title, description)
        else:
            sync_map.project_id, sync_map.project_url = client.create_project(
                team.id, title, description)
        save(sync_map)

    for m in plan.milestones:
        name = f"{m.id} — {m.name}"
        existing = sync_map.milestones.get(m.id)
        if plan_step("milestone", name, exists=bool(existing)):
            if existing:
                client.update_milestone(existing, name, m.goal)
            else:
                sync_map.milestones[m.id] = client.create_milestone(
                    sync_map.project_id, name, m.goal)
                save(sync_map)

    by_id = {r.req_id: r for r in requirements}
    for t in plan.tasks:
        existing = sync_map.issues.get(t.id)
        if not plan_step("issue", t.title, exists=bool(existing)):
            continue
        fields: dict[str, Any] = {
            "title": t.title,
            "description": issue_description(t, by_id),
            "priority": t.priority,
            "labelIds": [sync_map.labels[t.label]],
            "projectId": sync_map.project_id,
            "projectMilestoneId": sync_map.milestones[t.milestone_id],
        }
        estimate = linear_estimate(t.estimate, team.estimation_type)
        if estimate is not None:
            fields["estimate"] = estimate
        if existing:
            client.update_issue(existing, fields)
        else:
            sync_map.issues[t.id] = client.create_issue({**fields, "teamId": team.id})
            save(sync_map)

    for t in plan.tasks:
        for dep in t.depends_on:
            pair = (dep, t.id)
            if pair in sync_map.relations:
                continue
            if plan_step("relation", f"{dep} blocks {t.id}", exists=False):
                client.create_relation(sync_map.issues[dep], sync_map.issues[t.id])
                sync_map.relations.append(pair)
                save(sync_map)

    return items
