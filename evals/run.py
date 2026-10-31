"""Run the Extractor and Planner on every eval spec and score them against the gold lists.

From the repo root, with the API's environment (or `npm run evals`):

    uv run --project apps/api python -m evals.run                   # extract + plan, all specs
    uv run --project apps/api python -m evals.run --stage extract   # extractor only (fast)
    uv run --project apps/api python -m evals.run --spec room-booking
    uv run --project apps/api python -m evals.run --save-baseline   # make these the new baseline

Specs are markdown, split into sections without docling: ingest is deterministic and slow,
so the evals measure the prompts. Prints a markdown table to paste into the PR, plus the change
against evals/baseline.json. Each spec's outputs are kept in evals/results/ for inspection.
"""

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

EVALS = Path(__file__).resolve().parent
API = EVALS.parent / "apps" / "api"
# The pipeline reads its settings from apps/api/.env, relative to the working directory.
os.chdir(API)
sys.path.insert(0, str(API))
sys.path.insert(0, str(EVALS.parent))

from app.config import settings
from app.pipeline import agents, llm
from app.pipeline.ingest import split_sections
from app.pipeline.orchestrator import build_plan
from app.schemas import SpecDocument

from evals.score import score_extract, score_plan

BASELINE = EVALS / "baseline.json"
RESULTS = EVALS / "results"

COLUMNS = [  # (key, header, higher is better)
    ("recall", "recall", True),
    ("extra", "extra", False),
    ("scope_leaks", "leaks", False),
    ("wrong_type", "wrong type", False),
    ("bad_ids", "bad IDs", False),
    ("tasks", "tasks", None),
    ("coverage", "coverage", True),
    ("open_issues", "open issues", False),
    ("duplicate_titles", "dup titles", False),
    ("english_titles", "EN titles", False),
    ("tokens", "tokens", False),
    ("cost_usd", "cost $", False),
    ("seconds", "time s", False),
]


def measure(fn):
    """Run fn and return its result with the model usage and time it took."""
    llm.usage = llm.Usage()
    started = time.perf_counter()
    result = fn()
    u = llm.usage
    return result, {
        "tokens": u.input_tokens + u.output_tokens,
        "cost_usd": round(u.cost_usd, 4),
        "invalid_answers": u.invalid,
        "seconds": round(time.perf_counter() - started, 1),
    }


def run_spec(gold_path: Path, stage: str) -> dict[str, Any]:
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    name = gold_path.stem
    markdown = (EVALS / "specs" / gold["spec"]).read_text(encoding="utf-8")
    doc = SpecDocument(title=name, sections=split_sections(markdown))
    out = RESULTS / name
    out.mkdir(parents=True, exist_ok=True)

    print(f"{name}: extracting…", flush=True)
    reqs, cost = measure(lambda: agents.extract(doc))
    (out / "requirements.json").write_text(
        json.dumps([r.model_dump() for r in reqs], indent=2, ensure_ascii=False), encoding="utf-8")
    scores: dict[str, Any] = {**score_extract(gold, reqs), "extract": cost}
    if stage == "extract":
        return scores

    language = gold.get("language", "en")
    print(f"{name}: planning {len(reqs)} requirements in {language}…", flush=True)
    (_, plan, review), cost = measure(
        lambda: build_plan(reqs, language, log=lambda msg: print(f"  {msg}", flush=True)))
    (out / "plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    (out / "review.json").write_text(review.model_dump_json(indent=2), encoding="utf-8")
    return {**scores, **score_plan(plan, review, reqs, language), "plan": cost}


USAGE = ("tokens", "cost_usd", "seconds")


def cell(scores: dict[str, Any], key: str, stages: tuple[str, ...]) -> Any:
    """A column's value: list-valued scores count their items; usage sums the given stages."""
    if key in USAGE:
        total = sum(scores.get(s, {}).get(key, 0) for s in stages)
        return round(total, 4) if key == "cost_usd" else round(total, 1)
    value = scores.get(key)
    return len(value) if isinstance(value, list) else value


def fmt(value: Any, key: str) -> str:
    if value is None:
        return "–"
    if key in ("recall", "coverage"):
        return f"{value:.0%}"
    return f"{value:g}" if isinstance(value, float) else str(value)


def table(results: dict[str, Any], baseline: dict[str, Any]) -> str:
    lines = ["| spec | " + " | ".join(h for _, h, _ in COLUMNS) + " |",
             "|---" * (len(COLUMNS) + 1) + "|"]
    for name, scores in results.items():
        stages = tuple(s for s in ("extract", "plan") if s in scores)  # compare like with like
        row = []
        for key, _, better in COLUMNS:
            now = cell(scores, key, stages)
            text = fmt(now, key)
            before = cell(baseline[name], key, stages) if name in baseline else None
            # Usage varies 10–30% between identical runs; only flag bigger changes.
            noise = 0.2 * before if key in USAGE and before else 0
            if (before is not None and now is not None and better is not None
                    and abs(now - before) > noise):
                arrow = "▲" if (now > before) == better else "▼"
                text += f" ({fmt(before, key)} {arrow})"
            row.append(text)
        lines.append(f"| {name} | " + " | ".join(row) + " |")
    return "\n".join(lines)


def details(results: dict[str, Any]) -> str:
    lines = []
    for name, s in results.items():
        for key in ("missed", "extra", "scope_leaks", "wrong_type", "bad_ids", "duplicate_ids",
                    "english_titles"):
            if s.get(key):
                lines.append(f"- {name} {key}: {', '.join(s[key])}")
        invalid = sum(s.get(st, {}).get("invalid_answers", 0) for st in ("extract", "plan"))
        if invalid:
            lines.append(f"- {name}: {invalid} invalid model answers were retried")
    return "\n".join(lines)


def main() -> None:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    parser = argparse.ArgumentParser(prog="python -m evals.run")
    parser.add_argument("--stage", choices=["extract", "plan"], default="plan",
                        help="stop after this stage (default: plan, i.e. both)")
    parser.add_argument("--spec", help="only this spec (name of its gold file)")
    parser.add_argument("--save-baseline", action="store_true",
                        help="store these scores as the baseline to compare against")
    args = parser.parse_args()

    golds = sorted((EVALS / "gold").glob("*.json"))
    if args.spec:
        golds = [g for g in golds if g.stem == args.spec]
    results = {g.stem: run_spec(g, args.stage) for g in golds}
    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    baseline = baseline.get("results", {})

    model = (f"{settings.llm_provider} · extract {settings.specwright_model_extract} · "
             f"plan {settings.specwright_model_plan}")
    print(f"\n{model}\n\n{table(results, baseline)}\n\n{details(results)}")
    (RESULTS / "latest.json").write_text(json.dumps({"model": model, "results": results},
                                                    indent=2), encoding="utf-8")
    if args.save_baseline:
        # Replace only the specs that ran, so `--spec X --save-baseline` keeps the others.
        BASELINE.write_text(json.dumps({"model": model, "results": {**baseline, **results}},
                                       indent=2) + "\n", encoding="utf-8")
        print(f"\nsaved baseline: {BASELINE}")


if __name__ == "__main__":
    main()
