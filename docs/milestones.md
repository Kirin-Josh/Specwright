# Milestones

Work one milestone at a time. Commit and clear context between milestones.

## M0 — Setup (2–3 days)
- [x] Monorepo, Next.js app, FastAPI app, CLAUDE.md, docs
- [ ] Appwrite project: auth, `specs` bucket, collections from the data model
- [ ] ARQ worker + Redis via docker-compose
- [ ] `.env` filled, `/health` green

## M1 — Ingest + Extractor
- [ ] Upload endpoint → Appwrite storage
- [ ] `ingest.py` with docling (docx + pdf, tables kept)
- [ ] `extractor.py` returns `list[Requirement]` via forced tool use
- [ ] Web: upload page + requirements table
- Done when: upload a spec → see clean requirements with IDs

## M2 — Planner
- [ ] `planner.py` → `Plan` (labels BE/FE/QA, estimates, priority, depends_on, requirement_ids)
- [ ] Per-milestone fan-out for large specs
- Done when: requirements → full plan in one run

## M3 — Reviewer + coverage
- [ ] `checks.py`: coverage, orphan tasks, dependency cycles, estimate bounds
- [ ] LLM critique: duplicates, vague tasks
- [ ] Fix loop (max 2 rounds)
- Done when: checks pass; a deliberately weak plan gets fixed

## M4 — Review UI
- [ ] Plan board grouped by milestone; edit / merge / split / move tasks
- [ ] Coverage matrix (requirement × task)
- [ ] SSE progress per stage

## M5 — Linear sync
- [ ] Dry run (diff of what would be created/updated)
- [ ] Push in order: labels → project → milestones → issues → relations
- [ ] Re-run produces no duplicates

## M6 — Evals + demo
- [ ] 3–5 specs in `evals/specs` with gold lists in `evals/gold`
- [ ] Metrics: requirement recall, coverage %, duplicate rate, schema validity, cost, latency
- [ ] Evals in CI, README, 2-minute demo video
