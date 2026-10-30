# Milestones

Work one milestone at a time. Commit and clear context between milestones.

## M0 — Setup (2–3 days)
- [x] Monorepo, Next.js app, FastAPI app, CLAUDE.md, docs
- [x] Appwrite project: `specs` bucket, `runs` and `outputs` tables (`RUN_STORE=appwrite`)
- [ ] Sign-in and run ownership — later, once other people use the app
- [ ] ARQ worker + Redis — deferred (needs Docker); runs use FastAPI background tasks
- [x] `.env` filled, `/health` green

## M1 — Ingest + Extractor
- [x] Upload endpoint → Appwrite storage (or local files)
- [x] `ingest.py` with docling (docx + pdf, tables kept)
- [x] `extractor.py` returns `list[Requirement]` via forced tool use
- [x] Web: upload page + requirements table
- Done when: upload a spec → see clean requirements with IDs

## M2 — Planner
- [x] `planner.py` → `Plan` (labels BE/FE/QA, estimates, priority, depends_on, requirement_ids)
- [x] Per-milestone fan-out for large specs
- Done when: requirements → full plan in one run

## M3 — Reviewer + coverage
- [x] `checks.py`: coverage, orphan tasks, dependency cycles, estimate bounds
- [x] LLM critique: duplicates, vague tasks
- [x] Fix loop (max 2 rounds)
- Done when: checks pass; a deliberately weak plan gets fixed

## M4 — Review UI
- [x] Plan board grouped by milestone; edit / merge / split / move tasks
- [x] Coverage matrix (requirement × task)
- [x] SSE progress per stage

## M5 — Linear sync
- [x] Dry run (diff of what would be created/updated)
- [x] Push in order: labels → project → milestones → issues → relations
- [x] Re-run produces no duplicates

## M6 — Evals + demo
- [ ] 3–5 specs in `evals/specs` with gold lists in `evals/gold` (2 so far)
- [x] Metrics: requirement recall, coverage %, duplicate rate, schema validity, cost, latency
- [x] Evals README
- [ ] Evals in CI
- [ ] 2-minute demo video
