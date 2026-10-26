"use client";

import { useEffect, useRef, useState } from "react";
import { previewSync, pushToLinear } from "@/lib/api";
import type { Plan, SyncItem, SyncResult } from "@/lib/types";

interface Props {
  runId: string;
  plan: Plan;
  onClose: () => void;
}

type State =
  | { step: "loading" }
  | { step: "preview"; items: SyncItem[] }
  | { step: "pushing"; items: SyncItem[] }
  | { step: "done"; result: SyncResult }
  | { step: "error"; message: string };

export function SyncDialog({ runId, plan, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [state, setState] = useState<State>({ step: "loading" });

  useEffect(() => {
    dialogRef.current?.showModal();
    previewSync(runId, plan)
      .then((items) => setState({ step: "preview", items }))
      .catch((e: Error) => setState({ step: "error", message: e.message }));
  }, [runId, plan]);

  async function push() {
    if (state.step !== "preview") return;
    setState({ step: "pushing", items: state.items });
    try {
      setState({ step: "done", result: await pushToLinear(runId) });
    } catch (e) {
      setState({
        step: "error",
        message: e instanceof Error ? e.message : "Push failed",
      });
    }
  }

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      className="m-auto w-full max-w-lg rounded-xl bg-white p-5 text-zinc-900 shadow-xl backdrop:bg-black/40 dark:bg-zinc-900 dark:text-zinc-100"
    >
      <h2 className="font-semibold">Push to Linear</h2>

      {state.step === "loading" && (
        <p className="mt-4 text-sm text-zinc-500">Preparing preview…</p>
      )}

      {(state.step === "preview" || state.step === "pushing") && (
        <>
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            Dry run: this is what will be created or updated in Linear.
          </p>
          <SyncSummary items={state.items} />
          <ul className="mt-3 max-h-60 space-y-1 overflow-y-auto rounded-md border border-zinc-200 p-2 text-sm dark:border-zinc-800">
            {state.items.map((item, i) => (
              <li key={i} className="flex gap-2">
                <span
                  className={
                    item.action === "create"
                      ? "text-emerald-600"
                      : "text-amber-600"
                  }
                >
                  {item.action === "create" ? "+" : "~"}
                </span>
                <span className="w-20 shrink-0 text-zinc-500">{item.kind}</span>
                <span className="truncate">{item.title}</span>
              </li>
            ))}
          </ul>
        </>
      )}

      {state.step === "done" && (
        <p className="mt-4 text-sm">
          Done: {state.result.created} created, {state.result.updated} updated.{" "}
          <a
            href={state.result.project_url}
            target="_blank"
            rel="noreferrer"
            className="text-indigo-600 underline"
          >
            Open in Linear
          </a>
        </p>
      )}

      {state.step === "error" && (
        <p className="mt-4 text-sm text-red-600">{state.message}</p>
      )}

      <div className="mt-5 flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          className="rounded-md px-3 py-1.5 text-sm"
        >
          {state.step === "done" ? "Close" : "Cancel"}
        </button>
        {(state.step === "preview" || state.step === "pushing") && (
          <button
            type="button"
            onClick={push}
            disabled={state.step === "pushing"}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {state.step === "pushing" ? "Pushing…" : "Push"}
          </button>
        )}
      </div>
    </dialog>
  );
}

function SyncSummary({ items }: { items: SyncItem[] }) {
  const counts = items.reduce<Record<string, number>>((acc, i) => {
    acc[i.kind] = (acc[i.kind] ?? 0) + 1;
    return acc;
  }, {});
  return (
    <div className="mt-3 flex flex-wrap gap-2 text-xs">
      {Object.entries(counts).map(([kind, n]) => (
        <span
          key={kind}
          className="rounded-full bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800"
        >
          {n} {kind}
          {n > 1 ? "s" : ""}
        </span>
      ))}
    </div>
  );
}
