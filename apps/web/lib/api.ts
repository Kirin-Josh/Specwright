import { mockIssues, mockPlan, mockRequirements } from "./mock-data";
import type {
  Language,
  Plan,
  Run,
  RunEvent,
  Stage,
  SyncItem,
  SyncResult,
} from "./types";

// Every call the UI makes goes through this file.
// With NEXT_PUBLIC_USE_MOCK=true it returns fake data; later, flip it to false to hit FastAPI.

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export async function createRun(
  file: File,
  language: Language,
): Promise<{ runId: string }> {
  if (USE_MOCK) {
    await wait(600);
    return { runId: `run_${Date.now().toString(36)}` };
  }
  const body = new FormData();
  body.append("file", file);
  body.append("language", language);
  return request("/runs", { method: "POST", body });
}

export async function getRun(id: string): Promise<Run> {
  if (USE_MOCK) {
    await wait(300);
    return {
      id,
      spec_title: "Room booking app — spec v1",
      language: "en",
      stage: "ingesting",
      requirements: [],
      plan: null,
      issues: [],
    };
  }
  return request(`/runs/${id}`);
}

/** Streams stage updates. Returns a function that stops listening. */
export function subscribeToRun(
  id: string,
  onEvent: (event: RunEvent) => void,
): () => void {
  if (USE_MOCK) {
    const steps: Stage[] = ["extracting", "planning", "reviewing", "reviewed"];
    const timers = steps.map((stage, i) =>
      setTimeout(() => onEvent({ stage }), (i + 1) * 1200),
    );
    return () => timers.forEach(clearTimeout);
  }
  const source = new EventSource(`${API_URL}/runs/${id}/events`);
  source.onmessage = (e) => onEvent(JSON.parse(e.data) as RunEvent);
  return () => source.close();
}

/** Called once the run reaches "reviewed" to load the results. */
export async function getRunResults(
  id: string,
): Promise<Pick<Run, "requirements" | "plan" | "issues">> {
  if (USE_MOCK) {
    await wait(300);
    return {
      requirements: mockRequirements,
      plan: structuredClone(mockPlan),
      issues: mockIssues,
    };
  }
  const run = await request<Run>(`/runs/${id}`);
  return { requirements: run.requirements, plan: run.plan, issues: run.issues };
}

export async function savePlan(id: string, plan: Plan): Promise<void> {
  if (USE_MOCK) {
    await wait(400);
    return;
  }
  await request(`/runs/${id}/plan`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(plan),
  });
}

export async function previewSync(id: string, plan: Plan): Promise<SyncItem[]> {
  if (USE_MOCK) {
    await wait(500);
    const labels = [...new Set(plan.tasks.map((t) => t.label))];
    return [
      ...labels.map(
        (l): SyncItem => ({ kind: "label", title: l, action: "create" }),
      ),
      { kind: "project", title: "Room booking app", action: "create" },
      ...plan.milestones.map(
        (m): SyncItem => ({
          kind: "milestone",
          title: m.name,
          action: "create",
        }),
      ),
      ...plan.tasks.map(
        (t): SyncItem => ({
          kind: "issue",
          title: `[${t.label}] ${t.title}`,
          action: "create",
        }),
      ),
    ];
  }
  return request(`/runs/${id}/sync/preview`, { method: "POST" });
}

export async function pushToLinear(id: string): Promise<SyncResult> {
  if (USE_MOCK) {
    await wait(1500);
    return { created: 14, updated: 0, project_url: "https://linear.app" };
  }
  return request(`/runs/${id}/sync`, { method: "POST" });
}
