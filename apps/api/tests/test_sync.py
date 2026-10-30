from typing import Any

import pytest

from app.linear import Team
from app.pipeline.sync import SyncError, linear_estimate, summarize, sync_plan
from app.schemas import Label, Milestone, Plan, Requirement, RequirementType, SyncMap, Task


class FakeLinear:
    """Records every write and hands out sequential IDs."""

    def __init__(self, labels: dict[str, str] | None = None, fail_on_issue: int = 0):
        self.labels = labels or {}
        self.fail_on_issue = fail_on_issue
        self.calls: list[str] = []
        self.issues_created = 0

    def _id(self, kind: str) -> str:
        self.calls.append(kind)
        return f"{kind}-{len(self.calls)}"

    def find_team(self, key: str) -> Team | None:
        return Team(id="team-1", name="Eng", estimation_type="fibonacci") if key == "ENG" else None

    def find_label(self, team_id: str, name: str) -> str | None:
        return self.labels.get(name)

    def create_label(self, team_id: str, name: str, color: str) -> str:
        return self._id("create_label")

    def create_project(self, team_id: str, name: str, description: str) -> tuple[str, str]:
        return self._id("create_project"), "https://linear.app/p"

    def update_project(self, project_id: str, name: str, description: str) -> str:
        self._id("update_project")
        return "https://linear.app/p"

    def create_milestone(self, project_id: str, name: str, description: str) -> str:
        return self._id("create_milestone")

    def update_milestone(self, milestone_id: str, name: str, description: str) -> None:
        self._id("update_milestone")

    def create_issue(self, fields: dict[str, Any]) -> str:
        self.issues_created += 1
        if self.issues_created == self.fail_on_issue:
            raise ConnectionError("network down")
        return self._id("create_issue")

    def update_issue(self, issue_id: str, fields: dict[str, Any]) -> None:
        self._id("update_issue")

    def create_relation(self, blocking_issue_id: str, blocked_issue_id: str) -> None:
        self._id("create_relation")


def task(tid: str, label: Label, deps: list[str] | None = None) -> Task:
    return Task(
        id=tid, milestone_id="M1", title=f"Task {tid}", description="d", label=label,
        estimate=4, priority=2, requirement_ids=["EF-01"], depends_on=deps or [],
    )


PLAN = Plan(
    milestones=[Milestone(id="M1", name="Auth", goal="Users can log in")],
    tasks=[task("T1", Label.BE), task("T2", Label.FE, ["T1"]), task("T3", Label.QA, ["T2"])],
)
REQS = [Requirement(req_id="EF-01", text="Login", type=RequirementType.functional, section="s")]


def push(client: FakeLinear, sync_map: SyncMap, dry_run: bool = False):
    return sync_plan(PLAN, REQS, "Spec", "ENG", client, sync_map, dry_run=dry_run)


def counts(client: FakeLinear) -> dict[str, int]:
    return {c: client.calls.count(c) for c in sorted(set(client.calls))}


def test_first_push_creates_everything_in_order():
    client, sync_map = FakeLinear(), SyncMap()
    items = push(client, sync_map)
    assert counts(client) == {"create_issue": 3, "create_label": 3, "create_milestone": 1,
                              "create_project": 1, "create_relation": 2}
    assert [i.kind for i in items][:5] == ["label", "label", "label", "project", "milestone"]
    assert set(sync_map.issues) == {"T1", "T2", "T3"}
    assert summarize(items, sync_map).created == 10


def test_second_push_updates_and_creates_nothing():
    sync_map = SyncMap()
    push(FakeLinear(), sync_map)
    client = FakeLinear()
    items = push(client, sync_map)
    assert counts(client) == {"update_issue": 3, "update_milestone": 1, "update_project": 1}
    assert summarize(items, sync_map).created == 0


def test_dry_run_writes_nothing():
    client, sync_map = FakeLinear(), SyncMap()
    items = push(client, sync_map, dry_run=True)
    assert client.calls == []
    assert sync_map == SyncMap()
    assert len(items) == 10


def test_resume_after_crash_does_not_duplicate():
    sync_map = SyncMap()
    with pytest.raises(ConnectionError):
        push(FakeLinear(fail_on_issue=2), sync_map)
    assert set(sync_map.issues) == {"T1"}  # saved before the crash
    client = FakeLinear()
    push(client, sync_map)
    assert counts(client)["create_issue"] == 2
    assert counts(client)["update_issue"] == 1


def test_existing_label_is_reused():
    client = FakeLinear(labels={"BE": "label-be"})
    sync_map = SyncMap()
    push(client, sync_map)
    assert counts(client)["create_label"] == 2
    assert sync_map.labels["BE"] == "label-be"


def test_other_team_refused():
    with pytest.raises(SyncError):
        push(FakeLinear(), SyncMap(team_id="team-2"))


def test_unknown_team_refused():
    with pytest.raises(SyncError):
        sync_plan(PLAN, REQS, "Spec", "NOPE", FakeLinear(), SyncMap())


def test_estimate_maps_to_team_scale():
    assert linear_estimate(4, "fibonacci") == 5  # tie between 3 and 5 rounds up
    assert linear_estimate(8, "linear") == 5
    assert linear_estimate(3, "exponential") == 4
    assert linear_estimate(3, "notUsed") is None
