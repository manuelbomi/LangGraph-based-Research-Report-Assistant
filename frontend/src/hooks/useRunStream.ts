import { useEffect, useRef, useState } from "react";

import { streamUrl } from "../api/client";
import type {
  GraphNodeName,
  InterruptPayload,
  RunStatus,
  StateSnapshot,
  TraceEventOut,
} from "../api/types";

export interface RunStreamState {
  status: RunStatus | "connecting";
  currentNode: GraphNodeName | null;
  completedNodes: GraphNodeName[];
  snapshot: StateSnapshot;
  trace: TraceEventOut[];
  interrupt: InterruptPayload | null;
  finalReport: string | null;
  error: string | null;
}

const INITIAL_STATE: RunStreamState = {
  status: "connecting",
  currentNode: null,
  completedNodes: [],
  snapshot: {},
  trace: [],
  interrupt: null,
  finalReport: null,
  error: null,
};

/**
 * Subscribes to `GET /runs/{id}/stream` (Server-Sent Events) and folds the
 * incoming events into a single state object a component can render
 * directly -- driving both the live GraphView highlighting and the
 * node-by-node output panel.
 */
export function useRunStream(runId: string | null, generation = 0): RunStreamState {
  const [state, setState] = useState<RunStreamState>(INITIAL_STATE);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId) {
      setState(INITIAL_STATE);
      return;
    }

    setState({ ...INITIAL_STATE, status: "connecting" });
    const source = new EventSource(streamUrl(runId));
    sourceRef.current = source;

    source.addEventListener("node", (evt) => {
      const data = JSON.parse((evt as MessageEvent).data) as {
        node: GraphNodeName;
        output: Record<string, unknown>;
        trace: TraceEventOut[];
      };
      setState((prev) => ({
        ...prev,
        status: "running",
        currentNode: data.node,
        completedNodes: prev.completedNodes.includes(data.node)
          ? prev.completedNodes
          : [...prev.completedNodes, data.node],
        snapshot: { ...prev.snapshot, ...(data.output as StateSnapshot) },
        trace: [...prev.trace, ...data.trace],
      }));
    });

    source.addEventListener("interrupt", (evt) => {
      const data = JSON.parse((evt as MessageEvent).data) as InterruptPayload;
      setState((prev) => ({
        ...prev,
        status: "awaiting_human",
        currentNode: "human_review",
        completedNodes: prev.completedNodes.includes("human_review")
          ? prev.completedNodes
          : [...prev.completedNodes, "human_review"],
        interrupt: data,
      }));
    });

    source.addEventListener("done", (evt) => {
      const data = JSON.parse((evt as MessageEvent).data) as {
        status: RunStatus;
        final_report: string | null;
      };
      setState((prev) => ({
        ...prev,
        status: data.status,
        finalReport: data.final_report,
        currentNode: data.status === "completed" || data.status === "rejected" ? "finalize" : prev.currentNode,
        completedNodes:
          data.status === "completed" || data.status === "rejected"
            ? prev.completedNodes.includes("finalize")
              ? prev.completedNodes
              : [...prev.completedNodes, "finalize"]
            : prev.completedNodes,
      }));
      source.close();
    });

    source.addEventListener("replay", (evt) => {
      const data = JSON.parse((evt as MessageEvent).data) as {
        status: RunStatus;
        trace: TraceEventOut[];
        state_snapshot: StateSnapshot;
        final_report: string | null;
      };
      setState((prev) => ({
        ...prev,
        status: data.status,
        trace: data.trace,
        snapshot: data.state_snapshot,
        finalReport: data.final_report,
      }));
    });

    source.addEventListener("error", (evt) => {
      // Only MessageEvents carry a backend-emitted `error` payload; a plain
      // connection failure fires this same listener with no `.data`.
      const data = (evt as MessageEvent).data;
      if (typeof data === "string") {
        const parsed = JSON.parse(data) as { message: string };
        setState((prev) => ({ ...prev, status: "error", error: parsed.message }));
        source.close();
      }
    });

    source.onerror = () => {
      setState((prev) =>
        prev.status === "completed" || prev.status === "rejected"
          ? prev
          : { ...prev, error: prev.error ?? "Connection to the run stream was lost." },
      );
    };

    return () => {
      source.close();
      sourceRef.current = null;
    };
    // `generation` is bumped by callers (e.g. after POST /resume) to force
    // a fresh EventSource connection against the new background task.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, generation]);

  return state;
}
