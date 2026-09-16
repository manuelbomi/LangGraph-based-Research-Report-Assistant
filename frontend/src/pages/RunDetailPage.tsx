import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getRun, resumeRun } from "../api/client";
import type { GraphNodeName, HumanDecisionRequest } from "../api/types";
import { GraphView } from "../components/GraphView";
import { HumanReview } from "../components/HumanReview";
import { MarkdownReport } from "../components/MarkdownReport";
import { NodePanel } from "../components/NodePanel";
import { useRunStream } from "../hooks/useRunStream";

const TERMINAL_STATUSES = new Set(["completed", "rejected", "error"]);

export function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const runId = id ?? null;
  const [generation, setGeneration] = useState(0);

  const { data: runDetail } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId as string),
    enabled: !!runId,
  });

  const stream = useRunStream(runId, generation);

  const resumeMutation = useMutation({
    mutationFn: (payload: HumanDecisionRequest) => resumeRun(runId as string, payload),
    onSuccess: () => setGeneration((g) => g + 1),
  });

  const currentNode: GraphNodeName | null = (stream.currentNode as GraphNodeName) ?? null;
  const completedNodes = stream.completedNodes as GraphNodeName[];
  const isLive = !TERMINAL_STATUSES.has(stream.status) || resumeMutation.isPending;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <Link to="/history" className="text-sm text-brand-600 hover:underline">
          &larr; Back to run history
        </Link>
        <h2 className="mt-1 text-xl font-semibold text-slate-900">
          {runDetail?.question ?? "Loading run..."}
        </h2>
        <p className="text-sm text-slate-500">
          Status:{" "}
          <span className="font-medium text-slate-700">
            {stream.status === "connecting" ? "connecting..." : stream.status.replace("_", " ")}
          </span>
          {isLive && <span className="ml-2 text-brand-600">(live)</span>}
        </p>
      </div>

      {stream.error && (
        <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">{stream.error}</p>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <GraphView currentNode={currentNode} completedNodes={completedNodes} />
        <NodePanel snapshot={stream.snapshot} trace={stream.trace} />
      </div>

      {stream.status === "awaiting_human" && stream.interrupt && (
        <HumanReview
          interrupt={stream.interrupt}
          submitting={resumeMutation.isPending}
          onDecision={(decision) => resumeMutation.mutate(decision)}
        />
      )}

      {(stream.finalReport || runDetail?.final_report) && (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Final report
          </h3>
          <MarkdownReport markdown={stream.finalReport ?? runDetail?.final_report ?? ""} />
        </div>
      )}
    </div>
  );
}
