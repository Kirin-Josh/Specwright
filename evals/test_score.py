from app.schemas import Label, Milestone, Plan, Requirement, RequirementType, ReviewReport, Task

from evals.score import match_gold, score_extract, score_plan

F, A = RequirementType.functional, RequirementType.acceptance


def req(rid: str, text: str = "x", type_: RequirementType = F) -> Requirement:
    return Requirement(req_id=rid, text=text, type=type_, section="s")


NUMBERED = {
    "requirements": [{"req_id": "FR-01", "type": "functional"},
                     {"req_id": "AC-01", "type": "acceptance"}],
    "out_of_scope": ["OOS-01"],
}


def test_numbered_spec_scores_ids_types_and_leaks():
    reqs = [req("FR-01"), req("AC-01"), req("OOS-01"), req("REQ-001"), req("FR-1")]
    s = score_extract(NUMBERED, reqs)
    assert s["recall"] == 1.0
    assert s["extra"] == ["OOS-01", "REQ-001", "FR-1"]
    assert s["scope_leaks"] == ["OOS-01"]
    assert s["bad_ids"] == ["FR-1"]
    assert s["wrong_type"] == ["AC-01: functional"]


def test_keyword_match_prefers_same_type():
    gold = [{"name": "export", "type": "functional", "match": [["export"]]},
            {"name": "export works", "type": "acceptance", "match": [["export"], ["paid"]]}]
    reqs = [req("REQ-001", "The Friday export opens and claims show as paid", A),
            req("REQ-002", "Finance exports approved claims as CSV")]
    assert match_gold(gold, reqs) == {0: 1, 1: 0}


def test_unnumbered_spec_reports_missed_and_keyword_leaks():
    gold = {"requirements": [{"name": "draft", "type": "functional", "match": [["draft"]]}],
            "out_of_scope_match": [[["ocr"]]]}
    s = score_extract(gold, [req("REQ-001", "Read receipts with OCR"), req("REQ-001", "y")])
    assert (s["recall"], s["missed"]) == (0.0, ["draft"])
    assert s["scope_leaks"] == ["REQ-001"]
    assert s["duplicate_ids"] == ["REQ-001"]


def test_plan_scores():
    def task(tid: str, title: str, rid: str) -> Task:
        return Task(id=tid, milestone_id="M1", title=title, description="d", label=Label.BE,
                    estimate=3, priority=2, requirement_ids=[rid])

    plan = Plan(milestones=[Milestone(id="M1", name="m", goal="g")],
                tasks=[task("T1", "Login API", "FR-01"), task("T2", "login api!", "FR-01")])
    s = score_plan(plan, ReviewReport(issues=[]), [req("FR-01"), req("FR-02")])
    assert (s["tasks"], s["points"], s["coverage"], s["duplicate_titles"]) == (2, 6, 0.5, 2)
