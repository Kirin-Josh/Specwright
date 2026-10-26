import type { Plan, Task } from "./types";

export type PlanAction =
  | { type: "reset"; plan: Plan }
  | { type: "update_task"; task: Task }
  | { type: "delete_task"; id: string }
  | { type: "add_task"; milestoneId: string };

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
  }
}

function nextTaskId(tasks: Task[]): string {
  const max = Math.max(0, ...tasks.map((t) => Number(t.id.replace(/\D/g, "")) || 0));
  return `T-${String(max + 1).padStart(3, "0")}`;
}