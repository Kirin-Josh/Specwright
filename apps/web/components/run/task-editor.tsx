"use client";

import { useEffect, useRef, useState } from "react";
import { priorityLabels } from "@/lib/ui";
import type { Label, Milestone, Requirement, Task } from "@/lib/types";

interface Props {
  task: Task;
  tasks: Task[];
  milestones: Milestone[];
  requirements: Requirement[];
  onSave: (task: Task) => void;
  onDelete: (id: string) => void;
  // Split and merge apply the draft first, so unsaved edits are kept.
  onSplit: (task: Task) => void;
  onMerge: (task: Task, removeId: string) => void;
  onClose: () => void;
}

const input =
  "w-full rounded-md border border-zinc-300 bg-white px-2.5 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-950";

export function TaskEditor({
  task,
  tasks,
  milestones,
  requirements,
  onSave,
  onDelete,
  onSplit,
  onMerge,
  onClose,
}: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  // Edit a local copy; the plan only changes when the user clicks Save.
  const [draft, setDraft] = useState<Task>(task);
  const [depsText, setDepsText] = useState(task.depends_on.join(", "));
  const [mergeId, setMergeId] = useState("");

  useEffect(() => {
    dialogRef.current?.showModal();
  }, []);

  function set<K extends keyof Task>(key: K, value: Task[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  function toggleRequirement(id: string) {
    set(
      "requirement_ids",
      draft.requirement_ids.includes(id)
        ? draft.requirement_ids.filter((r) => r !== id)
        : [...draft.requirement_ids, id],
    );
  }

  function current(): Task {
    const depends_on = depsText
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    return { ...draft, depends_on };
  }

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    onSave(current());
  }

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      className="m-auto w-full max-w-lg rounded-xl bg-white p-0 text-zinc-900 shadow-xl backdrop:bg-black/40 dark:bg-zinc-900 dark:text-zinc-100"
    >
      <form onSubmit={handleSave} className="space-y-4 p-5">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">
            Edit task{" "}
            <span className="font-mono text-sm text-zinc-500">{task.id}</span>
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-800"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <label className="block space-y-1 text-sm">
          <span className="font-medium">Title</span>
          <input
            className={input}
            value={draft.title}
            onChange={(e) => set("title", e.target.value)}
            required
          />
        </label>

        <label className="block space-y-1 text-sm">
          <span className="font-medium">Description</span>
          <textarea
            className={`${input} min-h-20`}
            value={draft.description}
            onChange={(e) => set("description", e.target.value)}
          />
        </label>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <label className="space-y-1 text-sm">
            <span className="font-medium">Label</span>
            <select
              className={input}
              value={draft.label}
              onChange={(e) => set("label", e.target.value as Label)}
            >
              <option value="BE">BE</option>
              <option value="FE">FE</option>
              <option value="QA">QA</option>
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium">Points</span>
            <input
              type="number"
              min={1}
              max={8}
              className={input}
              value={draft.estimate}
              onChange={(e) => set("estimate", Number(e.target.value))}
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium">Priority</span>
            <select
              className={input}
              value={draft.priority}
              onChange={(e) => set("priority", Number(e.target.value))}
            >
              {[1, 2, 3, 4].map((p) => (
                <option key={p} value={p}>
                  {priorityLabels[p]}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium">Milestone</span>
            <select
              className={input}
              value={draft.milestone_id}
              onChange={(e) => set("milestone_id", e.target.value)}
            >
              {milestones.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id}
                </option>
              ))}
            </select>
          </label>
        </div>

        <fieldset className="space-y-1 text-sm">
          <legend className="font-medium">Covers requirements</legend>
          <div className="max-h-40 space-y-1 overflow-y-auto rounded-md border border-zinc-200 p-2 dark:border-zinc-800">
            {requirements.map((r) => (
              <label key={r.req_id} className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={draft.requirement_ids.includes(r.req_id)}
                  onChange={() => toggleRequirement(r.req_id)}
                />
                <span>
                  <span className="font-mono text-xs">{r.req_id}</span>{" "}
                  <span className="text-zinc-600 dark:text-zinc-400">
                    {r.text}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <label className="block space-y-1 text-sm">
          <span className="font-medium">Depends on</span>
          <input
            className={input}
            placeholder="T-001, T-004"
            value={depsText}
            onChange={(e) => setDepsText(e.target.value)}
          />
        </label>

        <div className="flex flex-wrap items-center gap-2 rounded-md bg-zinc-50 p-2 text-sm dark:bg-zinc-950">
          <button
            type="button"
            onClick={() => onSplit(current())}
            title="Make a second task with the same requirements; points are shared between the two"
            className="rounded-md border border-zinc-300 px-2.5 py-1 dark:border-zinc-700"
          >
            Split in two
          </button>
          <span className="ml-auto text-zinc-500">Merge into this:</span>
          <select
            className="rounded-md border border-zinc-300 bg-white px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900"
            value={mergeId}
            onChange={(e) => setMergeId(e.target.value)}
            aria-label="Task to merge into this one"
          >
            <option value="">Choose a task…</option>
            {tasks
              .filter((t) => t.id !== task.id)
              .map((t) => (
                <option key={t.id} value={t.id}>
                  {t.id} · {t.title}
                </option>
              ))}
          </select>
          <button
            type="button"
            disabled={!mergeId}
            onClick={() => onMerge(current(), mergeId)}
            title="Adds its requirements, dependencies, points and description to this task, then removes it"
            className="rounded-md border border-zinc-300 px-2.5 py-1 disabled:opacity-40 dark:border-zinc-700"
          >
            Merge
          </button>
        </div>

        <div className="flex items-center gap-2 pt-2">
          <button
            type="button"
            onClick={() => onDelete(task.id)}
            className="rounded-md px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40"
          >
            Delete
          </button>
          <button
            type="button"
            onClick={onClose}
            className="ml-auto rounded-md px-3 py-1.5 text-sm"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500"
          >
            Save task
          </button>
        </div>
      </form>
    </dialog>
  );
}
