import { Suspense } from "react";
import { RunView } from "@/components/run/run-view";

export default function RunPage({ params }: PageProps<"/runs/[id]">) {
  // params is dynamic, so it must be read inside <Suspense> (Next.js 16 Cache Components).
  return (
    <Suspense fallback={<p className="text-sm text-zinc-500">Loading run…</p>}>
      <RunContent params={params} />
    </Suspense>
  );
}

async function RunContent({ params }: Pick<PageProps<"/runs/[id]">, "params">) {
  const { id } = await params;
  return <RunView runId={id} />;
}
