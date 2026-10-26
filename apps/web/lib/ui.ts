import type { IssueKind, Label } from "./types";

export const labelStyles: Record<Label, string> = {
  BE: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300",
  FE: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300",
  QA: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
};

export const issueLabels: Record<IssueKind, string> = {
  uncovered: "Uncovered requirement",
  orphan: "Broken reference",
  cycle: "Dependency cycle",
  estimate: "Estimate out of range",
  duplicate: "Possible duplicate",
  vague: "Too vague",
};

export const priorityLabels: Record<number, string> = {
  1: "Urgent",
  2: "High",
  3: "Medium",
  4: "Low",
};