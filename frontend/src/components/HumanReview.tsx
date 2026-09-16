import { useState } from "react";

import type { HumanDecisionRequest, InterruptPayload } from "../api/types";
import { MarkdownReport } from "./MarkdownReport";

interface HumanReviewProps {
  interrupt: InterruptPayload;
  onDecision: (decision: HumanDecisionRequest) => void;
  submitting?: boolean;
}

/** Renders the draft + critique feedback awaiting a human decision, with
 * Approve / Request Changes / Reject actions that call `onDecision` --
 * the page wires that to `POST /runs/{id}/resume`. */
export function HumanReview({ interrupt, onDecision, submitting }: HumanReviewProps) {
  const [feedback, setFeedback] = useState("");
  const [showFeedbackBox, setShowFeedbackBox] = useState(false);

  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50 p-5">
      <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-amber-700">
        Human review required
      </h3>
      <p className="mb-4 text-sm text-amber-900">
        The graph is paused. Review the draft report and the automated critique below, then
        approve, request changes, or reject.
      </p>

      <div className="mb-4 rounded-lg border border-amber-200 bg-white p-4">
        <h4 className="mb-1 text-xs font-semibold uppercase text-slate-500">
          Reviewer (critique) feedback
        </h4>
        <p className="mb-3 text-sm text-slate-700">{interrupt.critique_feedback}</p>
        <h4 className="mb-1 text-xs font-semibold uppercase text-slate-500">Draft report</h4>
        <div className="max-h-72 overflow-y-auto">
          <MarkdownReport markdown={interrupt.draft} />
        </div>
      </div>

      {showFeedbackBox && (
        <textarea
          className="mb-3 w-full rounded-md border border-slate-300 p-2 text-sm"
          rows={3}
          placeholder="What should change?"
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          aria-label="Requested changes"
        />
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={submitting}
          onClick={() => onDecision({ decision: "approve", feedback: "" })}
          className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          Approve
        </button>
        <button
          type="button"
          disabled={submitting}
          onClick={() => {
            if (!showFeedbackBox) {
              setShowFeedbackBox(true);
              return;
            }
            onDecision({ decision: "revise", feedback });
          }}
          className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50"
        >
          Request Changes
        </button>
        <button
          type="button"
          disabled={submitting}
          onClick={() => onDecision({ decision: "reject", feedback })}
          className="rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 disabled:opacity-50"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
