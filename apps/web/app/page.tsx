import { UploadForm } from "@/components/upload-form";

export default function Home() {
  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-2xl font-semibold tracking-tight">
        New plan from a spec
      </h1>
      <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
        Upload a .docx or .pdf specification. Specwright extracts the
        requirements, drafts milestones and tasks, and checks that every
        requirement is covered.
      </p>
      <UploadForm />
    </div>
  );
}
