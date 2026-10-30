"""Scores for one eval spec: pure functions over its gold file and the pipeline's output.

Gold requirements carry either `req_id` (the spec numbers its requirements) or `match`
(it doesn't): a list of keyword groups, each needing at least one hit in the requirement text.
"""

import re
from typing import Any

from app.schemas import Plan, Requirement, ReviewReport

GENERATED_ID = re.compile(r"^REQ-\d{3}$")


def matches(text: str, groups: list[list[str]]) -> bool:
    lowered = text.lower()
    return all(any(word in lowered for word in group) for group in groups)


def gold_name(g: dict[str, Any]) -> str:
    return g.get("req_id") or g["name"]


def match_gold(gold: list[dict[str, Any]], reqs: list[Requirement]) -> dict[int, int]:
    """Pair each gold requirement with at most one extracted one (gold index -> extracted
    index). Same-type pairs are tried first, so an acceptance criterion that repeats a feature's
    keywords doesn't take the feature's place."""
    paired: dict[int, int] = {}
    used: set[int] = set()
    for same_type_only in (True, False):
        for gi, g in enumerate(gold):
            if gi in paired:
                continue
            for ri, r in enumerate(reqs):
                if ri in used or (same_type_only and r.type != g["type"]):
                    continue
                hit = r.req_id == g["req_id"] if "req_id" in g else matches(r.text, g["match"])
                if hit:
                    paired[gi] = ri
                    used.add(ri)
                    break
    return paired


def score_extract(gold_file: dict[str, Any], reqs: list[Requirement]) -> dict[str, Any]:
    gold = gold_file["requirements"]
    paired = match_gold(gold, reqs)
    out_of_scope = set(gold_file.get("out_of_scope", []))
    spec_ids = {g["req_id"] for g in gold if "req_id" in g} | out_of_scope
    leaks = [r.req_id for r in reqs if r.req_id in out_of_scope] + [
        r.req_id for r in reqs
        for groups in gold_file.get("out_of_scope_match", []) if matches(r.text, groups)
    ]
    ids = [r.req_id for r in reqs]
    return {
        "requirements": len(reqs),
        "recall": round(len(paired) / len(gold), 3),
        "missed": [gold_name(g) for gi, g in enumerate(gold) if gi not in paired],
        "extra": [r.req_id for ri, r in enumerate(reqs) if ri not in paired.values()],
        "scope_leaks": leaks,
        "wrong_type": [
            f"{gold_name(gold[gi])}: {reqs[ri].type.value}"
            for gi, ri in paired.items() if reqs[ri].type != gold[gi]["type"]
        ],
        # A spec's own IDs must be kept; REQ-### only for requirements without one.
        "bad_ids": sorted({i for i in ids if i not in spec_ids and not GENERATED_ID.match(i)}),
        "duplicate_ids": sorted({i for i in ids if ids.count(i) > 1}),
    }


def normalize(title: str) -> str:
    return re.sub(r"[^\w]+", " ", title.lower()).strip()


def score_plan(plan: Plan, review: ReviewReport, reqs: list[Requirement]) -> dict[str, Any]:
    cited = {rid for t in plan.tasks for rid in t.requirement_ids}
    titles = [normalize(t.title) for t in plan.tasks]
    return {
        "milestones": len(plan.milestones),
        "tasks": len(plan.tasks),
        "points": sum(t.estimate for t in plan.tasks),
        "coverage": round(len(cited & {r.req_id for r in reqs}) / len(reqs), 3) if reqs else 0,
        "open_issues": len(review.issues),
        "duplicate_titles": sum(titles.count(t) > 1 for t in titles),
    }
