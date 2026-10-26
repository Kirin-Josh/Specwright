import type { Plan, Requirement, ReviewIssue } from "./types";

// Client-side mirror of apps/api/app/pipeline/checks.py, so the UI flags problems
// immediately while the user edits the plan. The server stays the source of truth.

export function coverageMap(plan: Plan): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const task of plan.tasks) {
    for (const reqId of task.requirement_ids) {
      map.set(reqId, [...(map.get(reqId) ?? []), task.id]);
    }
  }
  return map;
}

export function checkPlan(plan: Plan, requirements: Requirement[]): ReviewIssue[] {
  const issues: ReviewIssue[] = [];
  const reqIds = new Set(requirements.map((r) => r.req_id));
  const taskIds = new Set(plan.tasks.map((t) => t.id));
  const milestoneIds = new Set(plan.milestones.map((m) => m.id));
  const covered = coverageMap(plan);

  for (const r of requirements) {
    if (!covered.has(r.req_id)) {
      issues.push({ kind: "uncovered", detail: `${r.req_id} has no task`, task_ids: [], requirement_ids: [r.req_id] });
    }
  }

  for (const t of plan.tasks) {
    const unknownReqs = t.requirement_ids.filter((id) => !reqIds.has(id));
    if (t.requirement_ids.length === 0) {
      issues.push({ kind: "orphan", detail: `${t.id} cites no requirement`, task_ids: [t.id], requirement_ids: [] });
    }
    if (unknownReqs.length) {
      issues.push({ kind: "orphan", detail: `${t.id} cites unknown ${unknownReqs.join(", ")}`, task_ids: [t.id], requirement_ids: [] });
    }
    if (!milestoneIds.has(t.milestone_id)) {
      issues.push({ kind: "orphan", detail: `${t.id} is in unknown milestone ${t.milestone_id}`, task_ids: [t.id], requirement_ids: [] });
    }
    const missingDeps = t.depends_on.filter((id) => !taskIds.has(id));
    if (missingDeps.length) {
      issues.push({ kind: "orphan", detail: `${t.id} depends on missing ${missingDeps.join(", ")}`, task_ids: [t.id], requirement_ids: [] });
    }
  }

  return issues;
}