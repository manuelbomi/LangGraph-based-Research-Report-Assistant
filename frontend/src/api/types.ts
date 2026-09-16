/**
 * Hand-written TypeScript mirror of `backend/app/api/schemas.py`.
 * Keep these two files in sync when the API contract changes.
 */

export type RunStatus =
  | "pending"
  | "running"
  | "awaiting_human"
  | "revising"
  | "completed"
  | "rejected"
  | "error";

export interface RunCreateRequest {
  question: string;
}

export interface RunCreateResponse {
  id: string;
  status: RunStatus;
  question: string;
}

export interface HumanDecisionRequest {
  decision: "approve" | "revise" | "reject";
  feedback: string;
}

export interface TraceEventOut {
  node: string;
  timestamp: string;
  summary: string;
}

export interface RunSummary {
  id: string;
  question: string;
  status: RunStatus;
  created_at: string;
  updated_at: string;
}

export interface Finding {
  source_id: string;
  sub_question: string;
  source_type: "web" | "kb";
  title: string;
  url_or_doc_id: string;
  synthesis: string;
}

/** Loosely-typed mirror of `ResearchState` (backend/app/graph/state.py). */
export interface StateSnapshot {
  question?: string;
  sub_questions?: string[];
  findings?: Finding[];
  draft?: string;
  draft_revision?: number;
  critique_decision?: "approve" | "revise";
  critique_feedback?: string;
  revision_count?: number;
  human_decision?: "approve" | "revise" | "reject" | "";
  human_feedback?: string;
  human_revision_count?: number;
  final_report?: string;
  status?: RunStatus;
  interrupt?: InterruptPayload;
}

export interface RunDetail {
  id: string;
  question: string;
  status: RunStatus;
  final_report: string | null;
  trace: TraceEventOut[];
  state_snapshot: StateSnapshot;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface RunListResponse {
  runs: RunSummary[];
}

export interface InterruptPayload {
  question: string;
  draft: string;
  critique_feedback: string;
  sub_questions: string[];
}

/** Shapes of the SSE events emitted by GET /runs/{id}/stream. */
export type StreamEvent =
  | { type: "node"; node: string; output: Record<string, unknown>; trace: TraceEventOut[] }
  | { type: "interrupt"; data: InterruptPayload }
  | { type: "done"; status: RunStatus; final_report: string | null }
  | { type: "error"; message: string }
  | {
      type: "replay";
      status: RunStatus;
      trace: TraceEventOut[];
      state_snapshot: StateSnapshot;
      final_report: string | null;
    };

/** The graph node names, in the order they appear in the LangGraph
 * StateGraph (backend/app/graph/graph.py) -- used to drive the GraphView. */
export const GRAPH_NODES = [
  "plan",
  "research",
  "draft",
  "critique",
  "human_review",
  "finalize",
] as const;

export type GraphNodeName = (typeof GRAPH_NODES)[number];
