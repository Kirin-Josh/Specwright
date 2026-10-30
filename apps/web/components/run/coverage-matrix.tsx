import type { Plan, Requirement } from "@/lib/types";

interface Props {
  requirements: Requirement[];
  plan: Plan;
  onToggle: (taskId: string, reqId: string) => void;
  onEditTask: (id: string) => void;
}

// Requirement × task grid. Click a cell to add or remove that requirement from the task.
export function CoverageMatrix({ requirements, plan, onToggle, onEditTask }: Props) {
  const groups = plan.milestones
    .map((m) => ({ milestone: m, tasks: plan.tasks.filter((t) => t.milestone_id === m.id) }))
    .filter((g) => g.tasks.length > 0);
  const columns = groups.flatMap((g) => g.tasks);
  const covers = new Set(
    plan.tasks.flatMap((t) => t.requirement_ids.map((r) => `${t.id}|${r}`)),
  );

  return (
    <div>
      <p className="mb-3 text-sm text-zinc-600 dark:text-zinc-400">
        Click a cell to add or remove a requirement from a task. Click a task ID to edit it.
        Red rows have no task.
      </p>
      <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <table className="text-xs">
          <thead>
            <tr className="border-b border-zinc-200 dark:border-zinc-800">
              <th className="sticky left-0 z-10 bg-white dark:bg-zinc-900" />
              {groups.map(({ milestone, tasks }) => (
                <th
                  key={milestone.id}
                  colSpan={tasks.length}
                  title={milestone.name}
                  className="border-l border-zinc-200 px-1 py-1.5 font-mono font-medium text-zinc-500 dark:border-zinc-800"
                >
                  {milestone.id}
                </th>
              ))}
            </tr>
            <tr className="border-b border-zinc-200 dark:border-zinc-800">
              <th className="sticky left-0 z-10 bg-white px-3 py-2 text-left font-medium uppercase text-zinc-500 dark:bg-zinc-900">
                Requirement
              </th>
              {columns.map((t, i) => (
                <th
                  key={t.id}
                  className={`px-0.5 pb-2 align-bottom ${firstOfGroup(columns, i) ? "border-l border-zinc-200 dark:border-zinc-800" : ""}`}
                >
                  <button
                    type="button"
                    onClick={() => onEditTask(t.id)}
                    title={t.title}
                    className="font-mono font-normal text-indigo-700 [writing-mode:vertical-rl] rotate-180 hover:underline dark:text-indigo-300"
                  >
                    {t.id}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {requirements.map((r) => {
              const count = columns.filter((t) => covers.has(`${t.id}|${r.req_id}`)).length;
              return (
                <tr
                  key={r.req_id}
                  className={`border-b border-zinc-100 last:border-0 dark:border-zinc-800 ${
                    count ? "" : "bg-red-50 dark:bg-red-950/30"
                  }`}
                >
                  <th
                    scope="row"
                    title={r.text}
                    className={`sticky left-0 z-10 max-w-64 truncate px-3 py-1 text-left font-normal ${
                      count ? "bg-white dark:bg-zinc-900" : "bg-red-50 dark:bg-red-950"
                    }`}
                  >
                    <span className="font-mono">{r.req_id}</span>{" "}
                    <span className="text-zinc-500">{r.text}</span>
                  </th>
                  {columns.map((t, i) => {
                    const on = covers.has(`${t.id}|${r.req_id}`);
                    return (
                      <td
                        key={t.id}
                        className={`p-0 text-center ${firstOfGroup(columns, i) ? "border-l border-zinc-200 dark:border-zinc-800" : ""}`}
                      >
                        <button
                          type="button"
                          onClick={() => onToggle(t.id, r.req_id)}
                          aria-pressed={on}
                          aria-label={`${t.id} covers ${r.req_id}`}
                          title={`${t.id} · ${t.title}`}
                          className="size-6 rounded hover:bg-indigo-100 dark:hover:bg-indigo-950"
                        >
                          {on ? (
                            <span className="inline-block size-2.5 rounded-full bg-indigo-600 dark:bg-indigo-400" />
                          ) : null}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function firstOfGroup(columns: Plan["tasks"], i: number): boolean {
  return i === 0 || columns[i - 1].milestone_id !== columns[i].milestone_id;
}
