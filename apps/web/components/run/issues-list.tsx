import { issueLabels } from "@/lib/ui";
import type { ReviewIssue } from "@/lib/types";

interface Props {
  issues: ReviewIssue[];
  onEditTask: (id: string) => void;
}

export function IssuesList({ issues, onEditTask }: Props) {
  if (issues.length === 0) {
    return (
      <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300">
        No issues. Every requirement is covered and all references are valid.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {issues.map((issue, i) => (
        <li
          key={i}
          className="flex flex-wrap items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/30"
        >
          <span className="rounded bg-amber-200 px-1.5 py-0.5 text-xs font-medium text-amber-900 dark:bg-amber-900 dark:text-amber-100">
            {issueLabels[issue.kind]}
          </span>
          <span>{issue.detail}</span>
          {issue.task_ids.map((id) => (
            <button
              key={id}
              type="button"
              onClick={() => onEditTask(id)}
              className="font-mono text-xs text-indigo-700 underline dark:text-indigo-300"
            >
              {id}
            </button>
          ))}
        </li>
      ))}
    </ul>
  );
}
