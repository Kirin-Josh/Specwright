import { STAGES, type Stage } from "@/lib/types";

const names: Record<(typeof STAGES)[number], string> = {
  ingesting: "Reading spec",
  extracting: "Extracting requirements",
  planning: "Planning",
  reviewing: "Reviewing",
  reviewed: "Ready",
};

interface Props {
  stage: Stage;
  message: string;
  onRetry: () => void;
}

export function StageStepper({ stage, message, onRetry }: Props) {
  if (stage === "failed") {
    return (
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <p className="text-red-600">
          The run failed{message ? `: ${message}` : "."}
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md border border-zinc-300 px-3 py-1 dark:border-zinc-700"
        >
          Retry
        </button>
      </div>
    );
  }
  const current = STAGES.indexOf(stage);

  return (
    <div className="space-y-1">
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
        {STAGES.map((s, i) => {
          const done = i < current || stage === "reviewed";
          const active = i === current && stage !== "reviewed";
          return (
            <li key={s} className="flex items-center gap-2">
              <span
                className={`flex size-5 items-center justify-center rounded-full text-[10px] font-semibold ${
                  done
                    ? "bg-indigo-600 text-white"
                    : active
                      ? "animate-pulse bg-indigo-200 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200"
                      : "bg-zinc-200 text-zinc-500 dark:bg-zinc-800"
                }`}
              >
                {done ? "✓" : i + 1}
              </span>
              <span className={done || active ? "" : "text-zinc-400"}>
                {names[s]}
              </span>
              {i < STAGES.length - 1 && (
                <span className="text-zinc-300 dark:text-zinc-700">—</span>
              )}
            </li>
          );
        })}
      </ol>
      {stage !== "reviewed" && message && (
        <p className="truncate font-mono text-xs text-zinc-500">{message}</p>
      )}
    </div>
  );
}
