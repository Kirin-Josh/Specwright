import { STAGES, type Stage } from "@/lib/types";

const names: Record<(typeof STAGES)[number], string> = {
  ingesting: "Reading spec",
  extracting: "Extracting requirements",
  planning: "Planning",
  reviewing: "Reviewing",
  reviewed: "Ready",
};

export function StageStepper({ stage }: { stage: Stage }) {
  if (stage === "failed") {
    return (
      <p className="text-sm text-red-600">
        The run failed. Try uploading the spec again.
      </p>
    );
  }
  const current = STAGES.indexOf(stage);

  return (
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
  );
}
