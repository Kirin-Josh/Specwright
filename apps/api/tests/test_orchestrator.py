from app.pipeline import orchestrator
from app.pipeline.agents import MilestoneOutline, Outline
from app.schemas import Requirement, Task


def req(rid: str) -> Requirement:
    return Requirement(req_id=rid, text="x", type="functional", section="s")


def task(tid: str, reqs: list[str], deps: list[str] | None = None) -> Task:
    return Task(
        id=tid, milestone_id="?", title=tid, description="d", label="BE",
        estimate=2, priority=2, requirement_ids=reqs, depends_on=deps or [],
    )


def milestone(mid: str, reqs: list[str]) -> MilestoneOutline:
    return MilestoneOutline(id=mid, name=mid, goal="g", requirement_ids=reqs)


def test_assemble_numbers_tasks_and_maps_dependencies():
    outline = Outline(milestones=[milestone("M1", ["A"]), milestone("M2", ["B"])])
    drafts = {"M1": [task("T1", ["A"]), task("T2", ["A"], ["T1"]).model_copy(
                  update={"description": "Extends T1."})],
              "M2": [task("T1", ["B"]), task("T2", ["B"], ["T1", "T9"])]}
    plan, origin = orchestrator.assemble(outline, drafts)
    assert [t.id for t in plan.tasks] == ["T-001", "T-002", "T-003", "T-004"]
    assert [t.milestone_id for t in plan.tasks] == ["M1", "M1", "M2", "M2"]
    assert plan.tasks[1].depends_on == ["T-001"]
    assert plan.tasks[1].description == "Extends T-001."
    assert plan.tasks[3].depends_on == ["T-003", "T9"]  # unknown kept so checks report it
    assert origin["T-003"] == ("M2", "T1")


def test_outline_is_repaired_when_model_keeps_missing_requirements(monkeypatch):
    bad = Outline(milestones=[milestone("M1", ["A", "A", "ZZ"]), milestone("M2", ["B"])])
    monkeypatch.setattr(orchestrator.agents, "outline", lambda *a: bad.model_copy(deep=True))
    result = orchestrator.make_outline([req("A"), req("B"), req("C")], "en", log=lambda _: None)
    assert [m.requirement_ids for m in result.milestones] == [["A"], ["B", "C"]]


def test_only_milestones_with_issues_are_replanned(monkeypatch):
    outline = Outline(milestones=[milestone("M1", ["A"]), milestone("M2", ["B", "C"])])
    calls = []

    def plan_milestone(m, reqs, earlier, language, feedback="", earlier_tasks=None):
        calls.append((m.id, feedback))
        if m.id == "M2" and not feedback:
            return [task("T1", ["B"])]  # C uncovered on the first draft
        return [task("T1", m.requirement_ids)]

    monkeypatch.setattr(orchestrator.agents, "outline", lambda *a: outline)
    monkeypatch.setattr(orchestrator.agents, "plan_milestone", plan_milestone)
    monkeypatch.setattr(orchestrator.agents, "critique_milestone", lambda *a: [])

    _, plan, review = orchestrator.build_plan([req("A"), req("B"), req("C")], "en")
    assert review.ok
    assert [m for m, _ in calls] == ["M1", "M2", "M2"]
    assert "[uncovered] C" in calls[-1][1]
    assert {rid for t in plan.tasks for rid in t.requirement_ids} == {"A", "B", "C"}


def test_acceptance_criterion_is_moved_after_what_it_verifies(monkeypatch):
    early = Outline(milestones=[milestone("M1", ["EF-01", "CA-01"]), milestone("M2", ["EF-02"])])
    monkeypatch.setattr(orchestrator.agents, "outline", lambda *a: early.model_copy(deep=True))
    criterion = Requirement(req_id="CA-01", text="Covers: EF-01, EF-02.", type="acceptance",
                            section="s")
    result = orchestrator.make_outline([req("EF-01"), req("EF-02"), criterion], "en",
                                       log=lambda _: None)
    assert [m.requirement_ids for m in result.milestones] == [["EF-01"], ["EF-02", "CA-01"]]


def test_foreign_requirements_are_stripped_and_emptied_tasks_dropped():
    tasks = [task("T1", ["A", "B"]), task("T2", ["B"]), task("T3", ["A"], ["T1", "T2"])]
    kept = orchestrator.drop_foreign(milestone("M1", ["A"]), tasks, lambda _: None)
    assert [(t.id, t.requirement_ids, t.depends_on) for t in kept] == [
        ("T1", ["A"], []), ("T3", ["A"], ["T1"]),
    ]


def test_tasks_citing_another_milestones_requirement_are_flagged():
    outline = Outline(milestones=[milestone("M1", ["A"]), milestone("M2", ["B"])])
    drafts = {"M1": [task("T1", ["A", "B"])], "M2": [task("T1", ["A"])]}
    plan, _ = orchestrator.assemble(outline, drafts)
    issues = orchestrator.ownership_issues(plan, {"A": "M1", "B": "M2"})
    assert sorted((i.kind, *i.task_ids, *i.requirement_ids) for i in issues) == [
        ("orphan", "T-001"), ("orphan", "T-002"), ("uncovered", "B"),
    ]
