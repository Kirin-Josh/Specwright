"""Hand-written pipeline state machine. Persistence and job queue are wired in M0/M1."""

from dataclasses import dataclass, field
from pathlib import Path

from app.pipeline import agents
from app.pipeline.checks import run_checks
from app.pipeline.ingest import ingest, to_prompt_text
from app.schemas import Plan, Requirement, ReviewReport

MAX_FIX_ROUNDS = 2


@dataclass
class RunState:
    spec_text: str = ""
    requirements: list[Requirement] = field(default_factory=list)
    plan: Plan | None = None
    review: ReviewReport | None = None
    stage: str = "created"


def run_pipeline(path: Path, language: str = "en") -> RunState:
    state = RunState()

    state.spec_text = to_prompt_text(ingest(path))
    state.stage = "ingested"

    state.requirements = agents.extract(state.spec_text)
    state.stage = "extracted"

    feedback = ""
    for _ in range(MAX_FIX_ROUNDS + 1):
        state.plan = agents.plan(state.spec_text, state.requirements, language, feedback)
        state.review = run_checks(state.plan, state.requirements)
        if state.review.ok:
            state.review = agents.critique(state.spec_text, state.plan)
        if state.review.ok:
            break
        feedback = "\n".join(f"- [{i.kind}] {i.detail}" for i in state.review.issues)

    state.stage = "reviewed"  # next: human review in the web app, then Linear sync (M5)
    return state
