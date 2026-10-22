# Specwright

Turns a software spec (.docx/.pdf) into a reviewed, traceable plan (milestones + tasks) and pushes it to Linear.

## Layout
- `apps/web` — Next.js 16 (App Router, TypeScript, Tailwind). Upload, review, push UI.
- `apps/api` — FastAPI + Anthropic SDK. Pipeline lives in `app/pipeline/`.
- `evals/` — test specs + gold requirement lists; `python -m evals.run` scores the pipeline.
- `docs/` — source of truth. Read before non-trivial work:
  - `docs/architecture.md` — pipeline, data model, design decisions
  - `docs/milestones.md` — what each milestone delivers; work one milestone at a time

## Commands
All from the repo root (npm workspaces):
- Install: `npm install` then `npm run setup:api`
- Run both: `npm run dev` (web on 3000, api on 8000)
- One side: `npm run dev:web` / `npm run dev:api`
- API tests: `npm run test:api`
- Add a web dependency: `npm install <pkg> -w apps/web`

## Rules
- Every agent returns typed output via tool use + Pydantic models in `app/schemas.py`. Never parse free text.
- Requirement IDs are the backbone. Keep the spec's own IDs (e.g. EF-01); generate `REQ-###` only when missing.
- Reviewer runs deterministic checks (`app/pipeline/checks.py`) before any LLM critique.
- Each pipeline stage persists its output so a run can resume or re-run one stage.
- Linear sync must be idempotent: always look up the task→issue map before creating.
- Model names come from env (`SPECWRIGHT_MODEL_*`), never hard-coded in stage code.
- When you change a prompt, run the evals and note the score change in the PR.
