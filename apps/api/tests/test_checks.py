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


def test_qa_task_without_acceptance_criterion_flagged():
    qa = task("T2", ["ES-01"], ["T1"]).model_copy(update={"label": "QA"})
    acceptance = qa.model_copy(update={"id": "T3", "requirement_ids": ["CA-01"]})
    plan = Plan(milestones=M, tasks=[task("T1", ["ES-01"]), qa, acceptance])
    reqs = [req("ES-01"), Requirement(req_id="CA-01", text="x", type="acceptance", section="s")]
    assert [(i.kind, i.task_ids) for i in run_checks(plan, reqs).issues] == [("duplicate", ["T2"])]


def test_qa_tasks_allowed_when_spec_has_no_acceptance_criteria():
    qa = task("T2", ["EF-01"], ["T1"]).model_copy(update={"label": "QA"})
    assert run_checks(Plan(milestones=M, tasks=[task("T1", ["EF-01"]), qa]), [req("EF-01")]).ok


def test_cycle_flagged():
    plan = Plan(milestones=M, tasks=[task("T1", ["EF-01"], ["T2"]), task("T2", ["EF-01"], ["T1"])])
    assert any(i.kind == "cycle" for i in run_checks(plan, [req("EF-01")]).issues)


def test_qa_task_without_dependencies_flagged():
    qa = task("T2", ["EF-01"]).model_copy(update={"label": "QA"})
    plan = Plan(milestones=M, tasks=[task("T1", ["EF-01"]), qa])
    assert [(i.kind, i.task_ids) for i in run_checks(plan, [req("EF-01")]).issues] == [
        ("dependency", ["T2"]),
    ]


def test_fe_task_must_reach_backend_for_same_requirement():
    def fe(tid: str, deps: list[str]) -> Task:
        return task(tid, ["EF-01"], deps).model_copy(update={"label": "FE"})

    tasks = [task("T1", ["EF-01"]), fe("T2", []), fe("T3", ["T1"]), fe("T4", ["T3"])]
    issues = run_checks(Plan(milestones=M, tasks=tasks), [req("EF-01")]).issues
    assert [(i.kind, i.task_ids) for i in issues] == [("dependency", ["T2"])]
