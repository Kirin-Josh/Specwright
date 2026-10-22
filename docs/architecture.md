# Architecture

```
Next.js 16 (upload · review · push)
        │  REST + SSE (progress)
        ▼
FastAPI ──► job runner (ARQ + Redis)
        │
        ├─ 1. Ingest      docx/pdf → markdown sections (tables included)
        ├─ 2. Extractor   → Requirement[]
        ├─ 3. Planner     → Plan (Milestone[] + Task[])
        ├─ 4. Reviewer    deterministic checks → LLM critique → fix loop (max 2)
        ├─ 5. Human review (web)
        └─ 6. Linear sync (GraphQL, idempotent)
        │
Appwrite: auth, file storage, DB (specs, runs, plans, sync map)
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
- `Spec(id, owner, file_id, title, language)`
- `Run(id, spec_id, stage, status, cost_usd, started_at, finished_at)`
- `Requirement(id, run_id, req_id, text, type, section)`
- `Plan(run_id, milestones[], tasks[])` — stored as JSON per revision
- `SyncMap(run_id, task_id, linear_issue_id)`
