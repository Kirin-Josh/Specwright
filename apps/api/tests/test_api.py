from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main, runs
from app.appwrite_store import AppwriteRunStore
from app.config import settings
from app.pipeline.agents import Outline
from app.runs import LocalRunStore, RunStore
from app.schemas import (
    Label,
    Milestone,
    Plan,
    Requirement,
    RequirementType,
    ReviewReport,
    SpecDocument,
    SpecSection,
    Task,
)
from tests.fake_appwrite import FakeStorage, FakeTables
from tests.test_sync import FakeLinear

REQS = [Requirement(req_id="EF-01", text="Login", type=RequirementType.functional, section="s")]
PLAN = Plan(
    milestones=[Milestone(id="M1", name="Auth", goal="g")],
    tasks=[Task(id="T-001", milestone_id="M1", title="Login API", description="d", label=Label.BE,
                estimate=2, priority=2, requirement_ids=["EF-01"])],
)


@pytest.fixture(params=["local", "appwrite"])
def store(request: pytest.FixtureRequest, tmp_path: Path,
          monkeypatch: pytest.MonkeyPatch) -> Iterator[RunStore]:
    calls: list[str] = []
    monkeypatch.setattr(runs, "ingest", lambda path: calls.append("ingest") or SpecDocument(
        title=path.stem, sections=[SpecSection(heading="h", markdown="m")]))
    monkeypatch.setattr(runs.agents, "extract", lambda doc: calls.append("extract") or REQS)

    def fake_build_plan(requirements, language, log, on_review):
        calls.append("plan")
        on_review()
        return Outline(milestones=[]), PLAN, ReviewReport(issues=[])

    monkeypatch.setattr(runs, "build_plan", fake_build_plan)
    monkeypatch.setattr(settings, "linear_team_key", "ENG")
    s: RunStore = (LocalRunStore(tmp_path) if request.param == "local" else
                   AppwriteRunStore(FakeTables(), FakeStorage(), cache=tmp_path))  # type: ignore[arg-type]
    s.calls = calls  # type: ignore[attr-defined]
    main.app.dependency_overrides[main.get_store] = lambda: s
    main.app.dependency_overrides[main.get_linear] = FakeLinear
    yield s
    main.app.dependency_overrides.clear()


client = TestClient(main.app)


def upload(name: str = "My spec.pdf") -> str:
    res = client.post("/runs", files={"file": (name, b"%PDF")}, data={"language": "fr"})
    assert res.status_code == 201, res.text
    return res.json()["runId"]


def test_upload_runs_pipeline_to_reviewed(store: RunStore):
    run = client.get(f"/runs/{upload()}").json()
    assert run["stage"] == "reviewed"
    assert run["spec_title"] == "My spec"
    assert run["language"] == "fr"
    assert [r["req_id"] for r in run["requirements"]] == ["EF-01"]
    assert run["plan"]["tasks"][0]["id"] == "T-001"


def test_rejects_other_file_types(store: RunStore):
    res = client.post("/runs", files={"file": ("spec.txt", b"x")})
    assert res.status_code == 400


def test_unknown_or_malformed_run_is_404(store: RunStore):
    assert client.get("/runs/run_000000000000").status_code == 404
    assert client.get("/runs/..%2F..%2Fetc").status_code == 404


def test_failure_is_recorded_and_retry_resumes(store: RunStore, monkeypatch):
    def boom(doc):
        raise RuntimeError("model down")

    monkeypatch.setattr(runs.agents, "extract", boom)
    run_id = upload()
    run = client.get(f"/runs/{run_id}").json()
    assert (run["stage"], run["message"]) == ("failed", "RuntimeError: model down")

    monkeypatch.setattr(runs.agents, "extract", lambda doc: REQS)
    assert client.post(f"/runs/{run_id}/retry").status_code == 202
    assert client.get(f"/runs/{run_id}").json()["stage"] == "reviewed"
    assert store.calls.count("ingest") == 1  # type: ignore[attr-defined]


def test_events_stream_ends_with_final_stage(store: RunStore):
    run_id = upload()
    with client.stream("GET", f"/runs/{run_id}/events") as res:
        body = "".join(res.iter_text())
    assert body == 'data: {"stage": "reviewed", "message": ""}\n\n'


def test_save_plan(store: RunStore):
    run_id = upload()
    edited = PLAN.model_copy(deep=True)
    edited.tasks[0].title = "Renamed"
    assert client.put(f"/runs/{run_id}/plan", json=edited.model_dump()).status_code == 204
    assert client.get(f"/runs/{run_id}").json()["plan"]["tasks"][0]["title"] == "Renamed"


def test_save_plan_refused_before_review(store: RunStore):
    meta = store.create("s.pdf", b"x", "en")
    res = client.put(f"/runs/{meta.id}/plan", json=PLAN.model_dump())
    assert res.status_code == 409


def test_sync_preview_then_push_then_no_duplicates(store: RunStore):
    run_id = upload()
    preview = client.post(f"/runs/{run_id}/sync/preview").json()
    assert {i["kind"] for i in preview} == {"label", "project", "milestone", "issue"}
    assert all(i["action"] == "create" for i in preview)

    pushed = client.post(f"/runs/{run_id}/sync").json()
    assert pushed == {"created": 4, "updated": 0, "project_url": "https://linear.app/p"}
    again = client.post(f"/runs/{run_id}/sync").json()
    assert (again["created"], again["updated"]) == (0, 3)


def test_interrupted_runs_marked_failed(store: RunStore):
    meta = store.create("s.pdf", b"x", "en")
    store.update(meta, stage="planning")
    store.mark_interrupted()
    assert store.get(meta.id).stage == "failed"  # type: ignore[union-attr]
