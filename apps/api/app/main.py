import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.linear import LinearClient, LinearError
from app.pipeline.sync import Linear, SyncError, summarize, sync_plan
from app.runs import SUFFIXES, LocalRunStore, RunMeta, RunStore, execute_run, review_of
from app.schemas import Issue, Plan, Requirement, SyncItem, SyncMap, SyncResult


def make_store() -> RunStore:
    if settings.run_store == "appwrite":
        from appwrite.services.storage import Storage
        from appwrite.services.tables_db import TablesDB

        from app.appwrite_store import AppwriteRunStore, client

        c = client()
        return AppwriteRunStore(TablesDB(c), Storage(c))
    return LocalRunStore()


store = make_store()


def get_store() -> RunStore:
    return store


def get_linear() -> Linear:
    try:
        return LinearClient(settings.linear_api_key)
    except LinearError as e:
        raise HTTPException(500, str(e)) from e


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    store.mark_interrupted()
    yield


app = FastAPI(title="Specwright API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

Store = Annotated[RunStore, Depends(get_store)]


class RunView(BaseModel):
    id: str
    spec_title: str
    language: str
    stage: str
    message: str
    requirements: list[Requirement]
    plan: Plan | None
    issues: list[Issue]


class RunCreated(BaseModel):
    runId: str


def find_run(store: RunStore, run_id: str) -> RunMeta:
    meta = store.get(run_id)
    if meta is None:
        raise HTTPException(404, f"run {run_id} not found")
    return meta


def reviewed_plan(store: RunStore, meta: RunMeta) -> Plan:
    plan = store.load(meta.id, "plan", Plan)
    if meta.stage != "reviewed" or plan is None:
        raise HTTPException(409, f"run is {meta.stage}, not reviewed")
    return plan


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/runs", status_code=201)
async def create_run(
    store: Store,
    background: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    language: Annotated[Literal["en", "fr"], Form()] = "en",
) -> RunCreated:
    name = file.filename or ""
    if Path(name).suffix.lower() not in SUFFIXES:
        raise HTTPException(400, "upload a .pdf or .docx spec")
    meta = store.create(name, await file.read(), language)
    background.add_task(execute_run, store, meta.id)
    return RunCreated(runId=meta.id)


@app.get("/runs/{run_id}")
def get_run(run_id: str, store: Store) -> RunView:
    meta = find_run(store, run_id)
    return RunView(
        **meta.model_dump(include={"id", "spec_title", "language", "stage", "message"}),
        requirements=store.load(run_id, "requirements", list[Requirement]) or [],
        plan=store.load(run_id, "plan", Plan),
        issues=review_of(store, run_id).issues,
    )


@app.post("/runs/{run_id}/retry", status_code=202)
def retry_run(run_id: str, store: Store, background: BackgroundTasks) -> None:
    """Resume a failed run from its first stage without saved output."""
    meta = find_run(store, run_id)
    if meta.stage != "failed":
        raise HTTPException(409, f"run is {meta.stage}, not failed")
    store.update(meta, stage="ingesting", message="")
    background.add_task(execute_run, store, run_id)


@app.get("/runs/{run_id}/events")
async def run_events(run_id: str, store: Store, request: Request) -> StreamingResponse:
    """Server-sent events: {stage, message} on every change, until the run ends."""
    find_run(store, run_id)

    async def stream() -> AsyncIterator[str]:
        last = None
        while not await request.is_disconnected():
            meta = find_run(store, run_id)
            event = {"stage": meta.stage, "message": meta.message}
            if event != last:
                yield f"data: {json.dumps(event)}\n\n"
                last = event
            if meta.stage in ("reviewed", "failed"):
                return
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


@app.put("/runs/{run_id}/plan", status_code=204)
def save_plan(run_id: str, plan: Plan, store: Store) -> None:
    meta = find_run(store, run_id)
    reviewed_plan(store, meta)
    store.save(run_id, "plan", plan)


def run_sync(store: RunStore, meta: RunMeta, client: Linear, dry_run: bool) -> list[SyncItem]:
    if not settings.linear_team_key:
        raise HTTPException(500, "LINEAR_TEAM_KEY is not set")
    plan = reviewed_plan(store, meta)
    requirements = store.load(meta.id, "requirements", list[Requirement]) or []
    sync_map = store.load(meta.id, "linear", SyncMap) or SyncMap()
    try:
        items = sync_plan(plan, requirements, meta.spec_title, settings.linear_team_key, client,
                          sync_map, lambda m: store.save(meta.id, "linear", m), dry_run=dry_run)
    except SyncError as e:
        raise HTTPException(400, str(e)) from e
    except LinearError as e:
        raise HTTPException(502, f"Linear: {e}") from e
    return items


@app.post("/runs/{run_id}/sync/preview")
def preview_sync(run_id: str, store: Store,
                 client: Annotated[Linear, Depends(get_linear)]) -> list[SyncItem]:
    return run_sync(store, find_run(store, run_id), client, dry_run=True)


@app.post("/runs/{run_id}/sync")
def push_sync(run_id: str, store: Store,
              client: Annotated[Linear, Depends(get_linear)]) -> SyncResult:
    meta = find_run(store, run_id)
    items = run_sync(store, meta, client, dry_run=False)
    return summarize(items, store.load(run_id, "linear", SyncMap) or SyncMap())
