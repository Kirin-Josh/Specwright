import { labelStyles } from "@/lib/ui";
import type { Task } from "@/lib/types";

interface Props {
  task: Task;
  flagged: boolean;
  onClick: () => void;
}

export function TaskCard({ task, flagged, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-lg border bg-white p-3 text-left shadow-sm transition hover:shadow dark:bg-zinc-900 ${
        flagged ? "border-amber-400" : "border-zinc-200 dark:border-zinc-800"
      }`}
    >
      <div className="flex items-center gap-2 text-xs">
        <span
          className={`rounded px-1.5 py-0.5 font-semibold ${labelStyles[task.label]}`}
        >
          {task.label}
        </span>
        <span className="font-mono text-zinc-500">{task.id}</span>
        <span className="ml-auto text-zinc-500">{task.estimate} pt</span>
      </div>
      <p className="mt-2 text-sm font-medium leading-snug">{task.title}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {task.requirement_ids.map((id) => (
          <span
            key={id}
            className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-[11px] text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
          >
            {id}
          </span>
        ))}
      </div>
    </button>
  );
}
