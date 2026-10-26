"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createRun } from "@/lib/api";
import type { Language } from "@/lib/types";

const ACCEPTED = [".docx", ".pdf"];

export function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState<Language>("en");
  const [dragging, setDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function pick(candidate: File | undefined) {
    if (!candidate) return;
    if (!ACCEPTED.some((ext) => candidate.name.toLowerCase().endsWith(ext))) {
      setError("Only .docx and .pdf files are supported.");
      return;
    }
    setError(null);
    setFile(candidate);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setSubmitting(true);
    setError(null);
    try {
      const { runId } = await createRun(file, language);
      router.push(`/runs/${runId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-8 space-y-6">
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          pick(e.dataTransfer.files[0]);
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition ${
          dragging
            ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950/40"
            : "border-zinc-300 bg-white hover:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-900"
        }`}
      >
        <input
          type="file"
          accept={ACCEPTED.join(",")}
          className="sr-only"
          onChange={(e) => pick(e.target.files?.[0])}
        />
        {file ? (
          <>
            <span className="font-medium">{file.name}</span>
            <span className="mt-1 text-xs text-zinc-500">
              {(file.size / 1024).toFixed(0)} KB · click to change
            </span>
          </>
        ) : (
          <>
            <span className="font-medium">Drop your spec here</span>
            <span className="mt-1 text-xs text-zinc-500">
              or click to browse · .docx, .pdf
            </span>
          </>
        )}
      </label>

      <fieldset>
        <legend className="text-sm font-medium">Write tasks in</legend>
        <div className="mt-2 flex gap-2">
          {(["en", "fr"] as const).map((lang) => (
            <button
              key={lang}
              type="button"
              onClick={() => setLanguage(lang)}
              className={`rounded-md border px-3 py-1.5 text-sm ${
                language === lang
                  ? "border-indigo-600 bg-indigo-600 text-white"
                  : "border-zinc-300 bg-white dark:border-zinc-700 dark:bg-zinc-900"
              }`}
            >
              {lang === "en" ? "English" : "Français"}
            </button>
          ))}
        </div>
      </fieldset>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={!file || submitting}
        className="w-full rounded-md bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "Uploading…" : "Generate plan"}
      </button>
    </form>
  );
}
