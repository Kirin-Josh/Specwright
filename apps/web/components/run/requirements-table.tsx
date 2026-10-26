import { coverageMap } from "@/lib/checks";
import type { Plan, Requirement } from "@/lib/types";

interface Props {
  requirements: Requirement[];
  plan: Plan;
  onEditTask: (id: string) => void;
}

export function RequirementsTable({ requirements, plan, onEditTask }: Props) {
  const coverage = coverageMap(plan);
  const covered = requirements.filter((r) => coverage.has(r.req_id)).length;
  const percent = requirements.length
    ? Math.round((covered / requirements.length) * 100)
    : 0;

  return (
    <div>
      <p className="mb-3 text-sm text-zinc-600 dark:text-zinc-400">
        <span className="font-semibold text-zinc-900 dark:text-zinc-100">
          {percent}%
        </span>{" "}
        covered · {covered} of {requirements.length} requirements have at least
        one task
      </p>
      <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <table className="w-full text-sm">
          <thead className="border-b border-zinc-200 text-left text-xs uppercase text-zinc-500 dark:border-zinc-800">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Requirement</th>
              <th className="px-3 py-2">Type</th>
              <th className="px-3 py-2">Section</th>
              <th className="px-3 py-2">Tasks</th>
            </tr>
          </thead>
          <tbody>
            {requirements.map((r) => {
              const tasks = coverage.get(r.req_id) ?? [];
              return (
                <tr
                  key={r.req_id}
                  className={`border-b border-zinc-100 last:border-0 dark:border-zinc-800 ${
                    tasks.length ? "" : "bg-red-50 dark:bg-red-950/30"
                  }`}
                >
                  <td className="px-3 py-2 font-mono text-xs">{r.req_id}</td>
                  <td className="px-3 py-2">{r.text}</td>
                  <td className="px-3 py-2 text-zinc-500">{r.type}</td>
                  <td className="px-3 py-2 text-zinc-500">{r.section}</td>
                  <td className="px-3 py-2">
                    {tasks.length ? (
                      <div className="flex flex-wrap gap-1">
                        {tasks.map((id) => (
                          <button
                            key={id}
                            type="button"
                            onClick={() => onEditTask(id)}
                            className="rounded bg-indigo-50 px-1.5 py-0.5 font-mono text-[11px] text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-950 dark:text-indigo-300"
                          >
                            {id}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs font-medium text-red-600">
                        Not covered
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
