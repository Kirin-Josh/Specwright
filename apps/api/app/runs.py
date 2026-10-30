"""Run storage and the stage runner.

A run has its uploaded spec, its metadata (stage and progress) and one JSON output per stage.
A stage whose output already exists is skipped, so a run interrupted by a crash or a server
restart resumes from where it stopped. `LocalRunStore` keeps runs in folders under runs/;
`AppwriteRunStore` (app/appwrite_store.py) keeps them in Appwrite. RUN_STORE picks one.
"""

import logging
import re
import secrets
import threading
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter
from pydantic_core import to_json

from app.pipeline import agents
from app.pipeline.ingest import ingest
from app.pipeline.orchestrator import build_plan
from app.schemas import Plan, Requirement, ReviewReport, SpecDocument

log = logging.getLogger(__name__)

RUNS_DIR = Path("runs")
RUN_ID = re.compile(r"^run_[0-9a-f]{12}$")
SUFFIXES = {".pdf", ".docx"}
ACTIVE_STAGES = {"ingesting", "extracting", "planning", "reviewing"}


class RunMeta(BaseModel):
    id: str
    spec_title: str
    language: str
    spec_file: str
    stage: str = "ingesting"  # ingesting | extracting | planning | reviewing | reviewed | failed
    message: str = ""
    created_at: datetime


def new_run(file_name: str, language: str) -> RunMeta:
    return RunMeta(id=f"run_{secrets.token_hex(6)}", spec_title=Path(file_name).stem,
                   language=language, spec_file=f"spec{Path(file_name).suffix.lower()}",
                   created_at=datetime.now(UTC))


class RunStore(ABC):
    @abstractmethod
    def create(self, file_name: str, data: bytes, language: str) -> RunMeta: ...

    @abstractmethod
    def get(self, run_id: str) -> RunMeta | None: ...

    @abstractmethod
    def write_meta(self, meta: RunMeta) -> None: ...

    @abstractmethod
    def spec_path(self, meta: RunMeta) -> Path:
        """A local copy of the uploaded spec, for ingest."""

    @abstractmethod
    def save(self, run_id: str, name: str, value: Any) -> None: ...

    @abstractmethod
    def load[T](self, run_id: str, name: str, tp: type[T]) -> T | None: ...

    @abstractmethod
    def active_runs(self) -> Iterable[RunMeta]:
        """Runs whose stage is one of ACTIVE_STAGES."""

    def update(self, meta: RunMeta, **changes: Any) -> None:
        for key, value in changes.items():
            setattr(meta, key, value)
        self.write_meta(meta)

    def mark_interrupted(self) -> None:
        """Runs left mid-stage by a server restart have no worker any more."""
        for meta in list(self.active_runs()):
            self.update(meta, stage="failed",
                        message="Interrupted by a server restart; retry to resume.")


class LocalRunStore(RunStore):
    def __init__(self, root: Path = RUNS_DIR):
        self.root = root
        # run.json is written by the pipeline thread and read by the progress stream.
        self._lock = threading.Lock()

    def _dir(self, run_id: str) -> Path:
        return self.root / run_id

    def create(self, file_name: str, data: bytes, language: str) -> RunMeta:
        meta = new_run(file_name, language)
        self._dir(meta.id).mkdir(parents=True)
        (self._dir(meta.id) / meta.spec_file).write_bytes(data)
        self.write_meta(meta)
        return meta

    def get(self, run_id: str) -> RunMeta | None:
        path = self._dir(run_id) / "run.json"
        if not RUN_ID.match(run_id) or not path.exists():
            return None
        with self._lock:
            return RunMeta.model_validate_json(path.read_text(encoding="utf-8"))

    def write_meta(self, meta: RunMeta) -> None:
        with self._lock:
            (self._dir(meta.id) / "run.json").write_text(meta.model_dump_json(indent=2),
                                                         encoding="utf-8")

    def spec_path(self, meta: RunMeta) -> Path:
        return self._dir(meta.id) / meta.spec_file

    def save(self, run_id: str, name: str, value: Any) -> None:
        (self._dir(run_id) / f"{name}.json").write_bytes(to_json(value, indent=2))

    def load[T](self, run_id: str, name: str, tp: type[T]) -> T | None:
        path = self._dir(run_id) / f"{name}.json"
        if not path.exists():
            return None
        return TypeAdapter(tp).validate_json(path.read_bytes())

    def active_runs(self) -> Iterable[RunMeta]:
        if not self.root.exists():
            return
        for folder in self.root.iterdir():
            meta = self.get(folder.name)
            if meta and meta.stage in ACTIVE_STAGES:
                yield meta


def execute_run(store: RunStore, run_id: str) -> None:
    """Run every stage that has no saved output yet; record failures on the run."""
    meta = store.get(run_id)
    if meta is None:
        return
    try:
        doc = store.load(run_id, "spec", SpecDocument)
        if doc is None:
            store.update(meta, stage="ingesting", message="")
            doc = ingest(store.spec_path(meta))
            store.save(run_id, "spec", doc)

        requirements = store.load(run_id, "requirements", list[Requirement])
        if requirements is None:
            store.update(meta, stage="extracting", message="")
            requirements = agents.extract(doc)
            store.save(run_id, "requirements", requirements)

        if store.load(run_id, "plan", Plan) is None:
            store.update(meta, stage="planning", message="")
            outline, plan, review = build_plan(
                requirements, meta.language,
                log=lambda msg: store.update(meta, message=msg),
                on_review=lambda: store.update(meta, stage="reviewing"),
            )
            store.save(run_id, "outline", outline)
            store.save(run_id, "review", review)
            store.save(run_id, "plan", plan)  # last: its presence marks planning as done

        store.update(meta, stage="reviewed", message="")
    except Exception as e:
        log.exception("run %s failed", run_id)
        store.update(meta, stage="failed", message=f"{type(e).__name__}: {e}")


def review_of(store: RunStore, run_id: str) -> ReviewReport:
    return store.load(run_id, "review", ReviewReport) or ReviewReport(issues=[])
