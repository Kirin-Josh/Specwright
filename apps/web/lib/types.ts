// Mirrors apps/api/app/schemas.py — keep the two in sync.

export type Language = "en" | "fr";
export type Label = "BE" | "FE" | "QA";
export type RequirementType = "functional" | "security" | "technical" | "acceptance";

export interface Requirement {
  req_id: string;
  text: string;
  type: RequirementType;
  section: string;
}

export interface Milestone {
  id: string;
  name: string;
  goal: string;
}

export interface Task {
  id: string;
  milestone_id: string;
  title: string;
  description: string;
  label: Label;
  estimate: number; // 1–8 points
  priority: number; // 1 = urgent … 4 = low
  requirement_ids: string[];
  depends_on: string[];
}

export interface Plan {
  milestones: Milestone[];
  tasks: Task[];
}

export type IssueKind = "uncovered" | "orphan" | "cycle" | "estimate" | "duplicate" | "vague";

export interface ReviewIssue {
  kind: IssueKind;
  detail: string;
  task_ids: string[];
  requirement_ids: string[];
}

export const STAGES = ["ingesting", "extracting", "planning", "reviewing", "reviewed"] as const;
export type Stage = (typeof STAGES)[number] | "failed";

export interface Run {
  id: string;
  spec_title: string;
  language: Language;
  stage: Stage;
  requirements: Requirement[];
  plan: Plan | null;
  issues: ReviewIssue[];
}

export interface RunEvent {
  stage: Stage;
  message?: string;
}

export interface SyncItem {
  kind: "label" | "project" | "milestone" | "issue";
  title: string;
  action: "create" | "update";
}

export interface SyncResult {
  created: number;
  updated: number;
  project_url: string;
}