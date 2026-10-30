"""Command-line runner for single pipeline stages. Run from apps/api:

    python -m app.cli extract path/to/spec.pdf
    python -m app.cli plan path/to/spec.pdf      # reuses runs/<spec-name>/requirements.json
    python -m app.cli sync path/to/spec.pdf --team ENG [--dry-run]   # pushes plan.json to Linear

Each stage writes its output to runs/<spec-name>/ so it can be inspected or re-used.
"""

import argparse
import io
import json
import sys
import time
from pathlib import Path

from app.config import settings
from app.linear import LinearClient
from app.pipeline import agents
from app.pipeline.ingest import ingest, to_prompt_text
from app.pipeline.orchestrator import build_plan
from app.pipeline.sync import summarize, sync_plan
from app.schemas import Plan, Requirement, SpecDocument, SyncMap

RUNS_DIR = Path("runs")


def cmd_extract(args: argparse.Namespace) -> None:
    path = Path(args.file)
    out = RUNS_DIR / path.stem
    out.mkdir(parents=True, exist_ok=True)

    spec_file = out / "spec.json"
    if spec_file.exists() and not args.reingest:
        doc = SpecDocument.model_validate_json(spec_file.read_text(encoding="utf-8"))
        print(f"ingest: reused {spec_file}")
    else:
        started = time.perf_counter()
        doc = ingest(path)
        spec_file.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
        print(f"ingest: {len(doc.sections)} sections in {time.perf_counter() - started:.1f}s")

    spec_text = to_prompt_text(doc)
    (out / "spec.md").write_text(spec_text, encoding="utf-8")

    started = time.perf_counter()
    requirements = agents.extract(doc)
    elapsed = time.perf_counter() - started
    req_file = out / "requirements.json"
    req_file.write_text(
        "[\n" + ",\n".join(r.model_dump_json(indent=2) for r in requirements) + "\n]",
        encoding="utf-8",
    )

    print(f"extract: {len(requirements)} requirements in {elapsed:.1f}s "
          f"({settings.llm_provider}/{settings.specwright_model_extract})")
    for r in requirements:
        print(f"  {r.req_id:<10} {r.type.value:<11} {r.text}")
    print(f"saved: {req_file}")


def cmd_plan(args: argparse.Namespace) -> None:
    out = RUNS_DIR / Path(args.file).stem
    req_file = out / "requirements.json"
    if not req_file.exists():
        sys.exit(f"{req_file} not found; run `extract` first")
    rows = json.loads(req_file.read_text(encoding="utf-8"))
    requirements = [Requirement.model_validate(row) for row in rows]

    started = time.perf_counter()
    outline, plan, review = build_plan(requirements, args.language, log=print)
    elapsed = time.perf_counter() - started
    (out / "outline.json").write_text(outline.model_dump_json(indent=2), encoding="utf-8")
    (out / "plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    (out / "review.json").write_text(review.model_dump_json(indent=2), encoding="utf-8")

    print(f"\nplan: {len(plan.milestones)} milestones, {len(plan.tasks)} tasks, "
          f"{sum(t.estimate for t in plan.tasks)} points in {elapsed:.1f}s "
          f"({settings.llm_provider}/{settings.specwright_model_plan})")
    for m in plan.milestones:
        print(f"\n{m.id} {m.name}: {m.goal}")
        for t in (t for t in plan.tasks if t.milestone_id == m.id):
            deps = f" after {', '.join(t.depends_on)}" if t.depends_on else ""
            print(f"  {t.id} [{t.label.value} {t.estimate}pt P{t.priority}] {t.title} "
                  f"<{', '.join(t.requirement_ids)}>{deps}")
    print(f"\nreview: {'clean' if review.ok else f'{len(review.issues)} open issues'}")
    for i in review.issues:
        print(f"  [{i.kind}] {', '.join(i.task_ids + i.requirement_ids)}: {i.detail}")
    print(f"saved: {out / 'plan.json'}")


def cmd_sync(args: argparse.Namespace) -> None:
    out = RUNS_DIR / Path(args.file).stem
    plan_file, map_file = out / "plan.json", out / "linear.json"
    if not plan_file.exists():
        sys.exit(f"{plan_file} not found; run `plan` first")
    plan = Plan.model_validate_json(plan_file.read_text(encoding="utf-8"))
    rows = json.loads((out / "requirements.json").read_text(encoding="utf-8"))
    requirements = [Requirement.model_validate(row) for row in rows]
    sync_map = (SyncMap.model_validate_json(map_file.read_text(encoding="utf-8"))
                if map_file.exists() else SyncMap())
    title = args.title or SpecDocument.model_validate_json(
        (out / "spec.json").read_text(encoding="utf-8")).title

    def save(m: SyncMap) -> None:
        map_file.write_text(m.model_dump_json(indent=2), encoding="utf-8")

    items = sync_plan(plan, requirements, title, args.team, LinearClient(settings.linear_api_key),
                      sync_map, save, dry_run=args.dry_run)
    for i in items:
        print(f"  {i.action:<6} {i.kind:<9} {i.title}")
    result = summarize(items, sync_map)
    verb = "would create" if args.dry_run else "created"
    print(f"\nsync: {verb} {result.created}, updated {result.updated}"
          + ("" if args.dry_run else f" — {result.project_url}"))


def main() -> None:
    # Windows consoles default to cp1252, which can't print some characters models emit.
    # Line buffering shows progress live even when output is redirected to a file.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(required=True)

    extract = sub.add_parser("extract", help="ingest a .docx/.pdf and extract requirements")
    extract.add_argument("file")
    extract.add_argument("--reingest", action="store_true", help="ignore a saved spec.json")
    extract.set_defaults(func=cmd_extract)

    plan = sub.add_parser("plan", help="plan milestones and tasks from saved requirements")
    plan.add_argument("file")
    plan.add_argument("--language", default="en", help="language of titles and descriptions")
    plan.set_defaults(func=cmd_plan)

    sync = sub.add_parser("sync", help="push the saved plan to Linear (idempotent)")
    sync.add_argument("file")
    sync.add_argument("--team", required=True, help="Linear team key, e.g. ENG")
    sync.add_argument("--title", help="project name (default: the spec's title)")
    sync.add_argument("--dry-run", action="store_true", help="list changes without writing")
    sync.set_defaults(func=cmd_sync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
