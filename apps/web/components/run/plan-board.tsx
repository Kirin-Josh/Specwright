"use client";

import { useState } from "react";
import type { Plan } from "@/lib/types";
import { TaskCard } from "./task-card";

interface Props {
  plan: Plan;
  flaggedTaskIds: Set<string>;
  onEditTask: (id: string) => void;
  onAddTask: (milestoneId: string) => void;
  onMoveTask: (id: string, milestoneId: string) => void;
}

export function PlanBoard({
  plan,
  flaggedTaskIds,
  onEditTask,
  onAddTask,
  onMoveTask,
}: Props) {
  // The milestone a task is being dragged over, to highlight the drop target.
  const [dropTarget, setDropTarget] = useState<string | null>(null);

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {plan.milestones.map((m) => {
        const tasks = plan.tasks.filter((t) => t.milestone_id === m.id);
        const points = tasks.reduce((sum, t) => sum + t.estimate, 0);
        return (
          <section
            key={m.id}
            onDragOver={(e) => {
              e.preventDefault(); // allows dropping here
              setDropTarget(m.id);
            }}
            onDragLeave={(e) => {
              if (!e.currentTarget.contains(e.relatedTarget as Node)) {
                setDropTarget(null);
              }
            }}
            onDrop={(e) => {
              e.preventDefault();
              setDropTarget(null);
              const id = e.dataTransfer.getData("text/plain");
              if (id) onMoveTask(id, m.id);
            }}
            className={`rounded-xl bg-zinc-100 p-3 ring-2 transition dark:bg-zinc-900/60 ${
              dropTarget === m.id ? "ring-indigo-400" : "ring-transparent"
            }`}
          >
            <header className="mb-3 px-1">
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-xs text-zinc-500">{m.id}</span>
                <h3 className="font-semibold">{m.name}</h3>
                <span className="ml-auto text-xs text-zinc-500">
                  {tasks.length} tasks · {points} pt
                </span>
              </div>
              <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">
                {m.goal}
              </p>
            </header>
            <div className="space-y-2">
              {tasks.map((t) => (
                <TaskCard
                  key={t.id}
                  task={t}
                  flagged={flaggedTaskIds.has(t.id)}
                  onClick={() => onEditTask(t.id)}
                />
              ))}
            </div>
            <button
              type="button"
              onClick={() => onAddTask(m.id)}
              className="mt-2 w-full rounded-lg border border-dashed border-zinc-300 py-2 text-sm text-zinc-500 hover:border-zinc-400 hover:text-zinc-700 dark:border-zinc-700"
            >
              + Add task
            </button>
          </section>
        );
      })}
    </div>
  );
}
