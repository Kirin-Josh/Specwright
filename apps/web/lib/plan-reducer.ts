import type { Plan, Task } from "./types";

export type PlanAction =
  | { type: "reset"; plan: Plan }
  | { type: "update_task"; task: Task }
  | { type: "delete_task"; id: string }
  | { type: "add_task"; milestoneId: string }
  | { type: "move_task"; id: string; milestoneId: string }
  | { type: "merge_tasks"; keepId: string; removeId: string }
  | { type: "split_task"; id: string };

export const emptyPlan: Plan = { milestones: [], tasks: [] };

export function planReducer(plan: Plan, action: PlanAction): Plan {
  switch (action.type) {
    case "reset":
      return action.plan;

    case "update_task":
      return {
        ...plan,
        tasks: plan.tasks.map((t) => (t.id === action.task.id ? action.task : t)),
      };

    case "delete_task":
      return {
        ...plan,
        tasks: plan.tasks
          .filter((t) => t.id !== action.id)
          // Remove the deleted task from other tasks' dependencies.
          .map((t) => ({ ...t, depends_on: t.depends_on.filter((d) => d !== action.id) })),
      };

    case "add_task":
      return {
        ...plan,
        tasks: [
          ...plan.tasks,
          {
            id: nextTaskId(plan.tasks),
            milestone_id: action.milestoneId,
            title: "New task",
            description: "",
            label: "BE",
            estimate: 2,
            priority: 3,
            requirement_ids: [],
            depends_on: [],
          },
        ],
      };

    case "move_task": {
      const task = plan.tasks.find((t) => t.id === action.id);
      if (!task || task.milestone_id === action.milestoneId) return plan;
      // Move to the end of the new milestone, so the board shows where it landed.
      return {
        ...plan,
        tasks: [
          ...plan.tasks.filter((t) => t.id !== action.id),
          { ...task, milestone_id: action.milestoneId },
        ],
      };
    }

    case "merge_tasks": {
      const { keepId, removeId } = action;
      const keep = plan.tasks.find((t) => t.id === keepId);
      const remove = plan.tasks.find((t) => t.id === removeId);
      if (!keep || !remove || keepId === removeId) return plan;
      const merged: Task = {
        ...keep,
        description: [keep.description, remove.description].filter(Boolean).join("\n\n"),
        estimate: Math.min(8, keep.estimate + remove.estimate),
        priority: Math.min(keep.priority, remove.priority),
        requirement_ids: union(keep.requirement_ids, remove.requirement_ids),
        depends_on: union(keep.depends_on, remove.depends_on).filter(
          (d) => d !== keepId && d !== removeId,
        ),
      };
      return {
        ...plan,
        tasks: plan.tasks
          .filter((t) => t.id !== removeId)
          .map((t) => {
            if (t.id === keepId) return merged;
            // Tasks that waited on the removed task now wait on the merged one.
            return t.depends_on.includes(removeId)
              ? { ...t, depends_on: union(t.depends_on.filter((d) => d !== removeId), [keepId]) }
              : t;
          }),
      };
    }

    case "split_task": {
      const index = plan.tasks.findIndex((t) => t.id === action.id);
      if (index === -1) return plan;
      const task = plan.tasks[index];
      const second: Task = {
        ...task,
        id: nextTaskId(plan.tasks),
        title: `${task.title} (part 2)`,
        estimate: Math.max(1, Math.floor(task.estimate / 2)),
      };
      const first: Task = { ...task, estimate: Math.max(1, Math.ceil(task.estimate / 2)) };
      const tasks = plan.tasks.map((t) => {
        if (t.id === task.id) return first;
        // Work that needed the whole task now needs both parts.
        return t.depends_on.includes(task.id)
          ? { ...t, depends_on: [...t.depends_on, second.id] }
          : t;
      });
      tasks.splice(index + 1, 0, second);
      return { ...plan, tasks };
    }
  }
}

export function nextTaskId(tasks: Task[]): string {
  const max = Math.max(0, ...tasks.map((t) => Number(t.id.replace(/\D/g, "")) || 0));
  return `T-${String(max + 1).padStart(3, "0")}`;
}

function union(a: string[], b: string[]): string[] {
  return [...new Set([...a, ...b])];
}
