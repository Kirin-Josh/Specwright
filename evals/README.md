# Evals

- `specs/` — input specs (anonymise client specs before committing)
- `gold/<spec-name>.json` — hand-checked list of requirement IDs + texts for each spec

Metrics to track per run: requirement recall, coverage %, duplicate rate, schema validity, cost, latency.
Run after every prompt change and record the scores in the PR.
