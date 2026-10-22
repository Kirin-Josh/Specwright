from app.pipeline.checks import run_checks
from app.schemas import Milestone, Plan, Requirement, Task


def req(rid: str) -> Requirement:
    return Requirement(req_id=rid, text="x", type="functional", section="s")


def task(tid: str, reqs: list[str], deps: list[str] | None = None) -> Task:
    return Task(
        id=tid, milestone_id="M1", title=tid, description="d", label="BE",
        estimate=2, priority=2, requirement_ids=reqs, depends_on=deps or [],
    )


M = [Milestone(id="M1", name="m", goal="g")]


def test_clean_plan_passes():
    plan = Plan(milestones=M, tasks=[task("T1", ["EF-01"]), task("T2", ["EF-02"], ["T1"])])
    assert run_checks(plan, [req("EF-01"), req("EF-02")]).ok


def test_uncovered_requirement_flagged():
    plan = Plan(milestones=M, tasks=[task("T1", ["EF-01"])])
    kinds = [i.kind for i in run_checks(plan, [req("EF-01"), req("EF-02")]).issues]
    assert kinds == ["uncovered"]


def test_cycle_flagged():
    plan = Plan(milestones=M, tasks=[task("T1", ["EF-01"], ["T2"]), task("T2", ["EF-01"], ["T1"])])
    assert any(i.kind == "cycle" for i in run_checks(plan, [req("EF-01")]).issues)
