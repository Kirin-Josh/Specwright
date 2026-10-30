# Evals

Scores the Extractor and Planner prompts on small specs with hand-checked gold lists.
Run them after every prompt change and paste the table into the PR.

```
npm run evals                                                   # extract + plan, all specs (~5–15 min)
apps/api/.venv/Scripts/python -m evals.run --stage extract      # extractor only (~1 min)
apps/api/.venv/Scripts/python -m evals.run --spec room-booking  # one spec
apps/api/.venv/Scripts/python -m evals.run --save-baseline      # make this run the new baseline
apps/api/.venv/Scripts/python -m pytest evals                   # tests for the scorers
```

Uses the provider and models in `apps/api/.env`. Specs are markdown split into sections
directly (no docling), so only the prompts are measured.

**Runs vary even at temperature 0.** On 2026-10-30, expense-tracker recall was 100% in 4 of
5 extract runs and 87% once: the model merged two requirements and dropped one. Before
calling a recall change real, rerun `--stage extract` two or three times. Tokens, cost and time
are only marked ▲/▼ when they move more than 20%.

## Files
- `specs/` — input specs (anonymise client specs before committing)
- `gold/<spec>.json` — what the extractor should return for each spec:
  - `requirements`: each with its `type` and either the spec's `req_id`, or `match` keyword
    groups for specs without IDs (every group needs one hit in the requirement text)
  - `out_of_scope` IDs or `out_of_scope_match` keyword groups that must not be extracted
- `baseline.json` — scores the table compares against (▲ better, ▼ worse)
- `results/` — latest outputs per spec, for inspection (not committed)

## Specs
| spec | tests |
|---|---|
| `room-booking` | 18 numbered requirements (FR/SEC/TECH/AC) in tables and lists, cross-references, an out-of-scope section with IDs |
| `expense-tracker` | 15 requirements in prose with no IDs (REQ-### must be generated), "later, not now" ideas that must not leak |

## Metrics
| column | meaning |
|---|---|
| recall | gold requirements found (same type matched first) |
| extra | extracted items that match no gold requirement |
| leaks | out-of-scope items extracted |
| wrong type | found, but with a different type |
| bad IDs | IDs that are neither the spec's own nor `REQ-###` |
| tasks / coverage | plan size; share of extracted requirements cited by at least one task |
| open issues | review issues left after the fix loop |
| dup titles | tasks sharing a title with another task |
| tokens / cost $ / time s | both stages; cost only when the provider reports it (OpenRouter) |
