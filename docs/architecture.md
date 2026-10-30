# Architecture

```
Next.js 16 (upload · review · push)
        │  REST + SSE (progress)
        ▼
FastAPI ──► background tasks (ARQ + Redis later, if runs need to outlive the API)
        │
        ├─ 1. Ingest      docx/pdf → markdown sections (tables included)
        ├─ 2. Extractor   → Requirement[]
        ├─ 3. Planner     → Plan (Milestone[] + Task[])
        ├─ 4. Reviewer    deterministic checks → LLM critique → fix loop (max 2)
        ├─ 5. Human review (web)
        └─ 6. Linear sync (GraphQL, idempotent)
        │
Runs: local files (RUN_STORE=local) or Appwrite Cloud (RUN_STORE=appwrite)
```

## Stages

| Stage | Input | Output | Notes |
|---|---|---|---|
| Ingest | uploaded file | `SpecDocument` (sections) | `docling` for pdf/docx; keep tables |
| Extractor | `SpecDocument` | `list[Requirement]` | keep spec IDs; cheaper model is fine |
| Planner | requirements | `Plan` | stronger model; per-milestone fan-out for big specs |
| Reviewer | plan + requirements | `ReviewReport` | `checks.py` first, then LLM for duplicates/vagueness |
| Sync | approved plan | `SyncResult` | labels → project → milestones → issues → relations |

## Decisions
- **Hand-written orchestrator** (`pipeline/orchestrator.py`): a plain state machine. No agent framework.
- **Typed outputs**: each agent is forced to call one tool whose input schema is a Pydantic model.
- **Prompt caching**: the spec text is the shared cached prefix across Extractor, Planner and Reviewer.
- **Resumable runs**: `Run.stage` + per-stage outputs persisted; re-run any single stage.
- **Output language** is a run option (`fr` / `en`), independent of the spec language.

## Data model
A run is its uploaded spec, its metadata and one JSON output per stage (`spec`, `requirements`,
`outline`, `review`, `plan`, `linear` = the sync map). `app/runs.py` defines the `RunStore`
interface and the local version; `app/appwrite_store.py` the Appwrite one:
- bucket `specs`: the uploaded file, ID = run ID
- table `runs`: `spec_title, language, spec_file, stage, message, created_at`, row ID = run ID
- table `outputs`: `run_id, name, json` (JSON text), row ID = `<run id>.<stage>`

Create them once with `uv run python -m app.appwrite_store` (safe to re-run).
Auth (one owner per run) comes with the web sign-in.
