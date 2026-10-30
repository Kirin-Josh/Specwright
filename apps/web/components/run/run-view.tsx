"use client";

import { useEffect, useMemo, useReducer, useState } from "react";
import {
  getRun,
  getRunResults,
  retryRun,
  savePlan,
  subscribeToRun,
} from "@/lib/api";
import { checkPlan } from "@/lib/checks";
import { emptyPlan, planReducer } from "@/lib/plan-reducer";
import type { Plan, Run } from "@/lib/types";
import { IssuesList } from "./issues-list";
import { PlanBoard } from "./plan-board";
import { RequirementsTable } from "./requirements-table";
import { StageStepper } from "./stage-stepper";
import { SyncDialog } from "./sync-dialog";
import { TaskEditor } from "./task-editor";

type Tab = "plan" | "requirements" | "issues";

export function RunView({ runId }: { runId: string }) {
  const [run, setRun] = useState<Run | null>(null);
  const [plan, dispatch] = useReducer(planReducer, emptyPlan);
  const [savedPlan, setSavedPlan] = useState<Plan>(emptyPlan);
  const [tab, setTab] = useState<Tab>("plan");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [syncOpen, setSyncOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  // Bumped by Retry to reload the run and listen again.
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // 1. Load the run, then listen for stage updates until it is reviewed.
  useEffect(() => {
    let cancelled = false;
    let unsubscribe = () => {};

    getRun(runId)
      .then((initial) => {
        if (cancelled) return;
        setRun(initial);
        unsubscribe = subscribeToRun(runId, async (event) => {
          setRun((r) =>
            r ? { ...r, stage: event.stage, message: event.message ?? "" } : r,
          );
          if (event.stage === "reviewed") {
            const results = await getRunResults(runId);
            if (cancelled) return;
            setRun((r) => (r ? { ...r, ...results } : r));
            if (results.plan) {
              dispatch({ type: "reset", plan: results.plan });
              setSavedPlan(results.plan);
            }
          }
        });
      })
      .catch((e: Error) => setError(e.message));

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [runId, attempt]);

  // 2. Re-check the plan on every edit. Server-only issues (dependency, duplicate, vague) are
  // kept as-is until the next run.
  const issues = useMemo(() => {
    if (!run) return [];
    const llmIssues = run.issues.filter(
      (i) =>
        i.kind === "dependency" || i.kind === "duplicate" || i.kind === "vague",
    );
    return [...checkPlan(plan, run.requirements), ...llmIssues];
  }, [plan, run]);

  const flaggedTaskIds = useMemo(
    () => new Set(issues.flatMap((i) => i.task_ids)),
    [issues],
  );
  const dirty = plan !== savedPlan;
  const editingTask = plan.tasks.find((t) => t.id === editingId);

  async function handleRetry() {
    try {
      await retryRun(runId);
      setAttempt((n) => n + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Retry failed");
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      await savePlan(runId, plan);
      setSavedPlan(plan);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!run) return <p className="text-sm text-zinc-500">Loading run…</p>;

  const ready = run.stage === "reviewed";

  return (
    <div className="space-y-6 pb-20">
      <header className="space-y-3">
        <div>
          <p className="font-mono text-xs text-zinc-500">{run.id}</p>
          <h1 className="text-2xl font-semibold tracking-tight">
            {run.spec_title}
          </h1>
        </div>
        <StageStepper
          stage={run.stage}
          message={run.message}
          onRetry={handleRetry}
        />
      </header>

      {ready && (
        <>
          <nav className="flex gap-1 border-b border-zinc-200 dark:border-zinc-800">
            {(
              [
                ["plan", `Plan (${plan.tasks.length})`],
                ["requirements", `Requirements (${run.requirements.length})`],
                ["issues", `Issues (${issues.length})`],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className={`-mb-px border-b-2 px-3 py-2 text-sm ${
                  tab === key
                    ? "border-indigo-600 font-medium text-indigo-700 dark:text-indigo-300"
                    : "border-transparent text-zinc-500 hover:text-zinc-800"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>

          {tab === "plan" && (
            <PlanBoard
              plan={plan}
              flaggedTaskIds={flaggedTaskIds}
              onEditTask={setEditingId}
              onAddTask={(milestoneId) =>
                dispatch({ type: "add_task", milestoneId })
              }
            />
          )}
          {tab === "requirements" && (
            <RequirementsTable
              requirements={run.requirements}
              plan={plan}
              onEditTask={setEditingId}
            />
          )}
          {tab === "issues" && (
            <IssuesList issues={issues} onEditTask={setEditingId} />
          )}

          <footer className="fixed inset-x-0 bottom-0 border-t border-zinc-200 bg-white/90 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/90">
            <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
              <span className="text-sm text-zinc-500">
                {dirty ? "Unsaved changes" : "All changes saved"}
              </span>
              <button
                type="button"
                onClick={handleSave}
                disabled={!dirty || saving}
                className="ml-auto rounded-md border border-zinc-300 px-3 py-1.5 text-sm disabled:opacity-40 dark:border-zinc-700"
              >
                {saving ? "Saving…" : "Save"}
              </button>
              <button
                type="button"
                onClick={() => setSyncOpen(true)}
                disabled={dirty}
                title={dirty ? "Save your changes first" : undefined}
                className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-40"
              >
                Push to Linear
              </button>
            </div>
          </footer>
        </>
      )}

      {editingTask && (
        <TaskEditor
          key={editingTask.id}
          task={editingTask}
          milestones={plan.milestones}
          requirements={run.requirements}
          onSave={(task) => {
            dispatch({ type: "update_task", task });
            setEditingId(null);
          }}
          onDelete={(id) => {
            dispatch({ type: "delete_task", id });
            setEditingId(null);
          }}
          onClose={() => setEditingId(null)}
        />
      )}

      {syncOpen && (
        <SyncDialog
          runId={runId}
          plan={plan}
          onClose={() => setSyncOpen(false)}
        />
      )}
    </div>
  );
}
