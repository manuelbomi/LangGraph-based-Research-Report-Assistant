import type { StateSnapshot, TraceEventOut } from "../api/types";

interface NodePanelProps {
  snapshot: StateSnapshot;
  trace: TraceEventOut[];
}

/** Side panel rendering each node's intermediate output as it streams in:
 * sub-questions from `plan`, findings from `research`, the draft from
 * `draft`, and the critique feedback from `critique`. */
export function NodePanel({ snapshot, trace }: NodePanelProps) {
  return (
    <div className="flex h-[560px] flex-col gap-4 overflow-y-auto rounded-xl border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        Live node output
      </h3>

      {snapshot.sub_questions && snapshot.sub_questions.length > 0 && (
        <section>
          <h4 className="mb-1 text-sm font-semibold text-slate-800">Sub-questions</h4>
          <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-600">
            {snapshot.sub_questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ol>
        </section>
      )}

      {snapshot.findings && snapshot.findings.length > 0 && (
        <section>
          <h4 className="mb-1 text-sm font-semibold text-slate-800">Findings</h4>
          <ul className="space-y-2 text-sm text-slate-600">
            {snapshot.findings.map((f) => (
              <li key={f.source_id} className="rounded-md bg-slate-50 p-2">
                <span className="mr-1 rounded bg-slate-200 px-1.5 py-0.5 text-xs font-mono">
                  {f.source_id}
                </span>
                <span className="text-xs uppercase text-slate-400">
                  {f.source_type === "kb" ? "knowledge base" : "web"}
                </span>
                <div className="font-medium text-slate-700">{f.title}</div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {snapshot.draft && (
        <section>
          <h4 className="mb-1 text-sm font-semibold text-slate-800">
            Draft {snapshot.draft_revision ? `(revision ${snapshot.draft_revision})` : ""}
          </h4>
          <p className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-md bg-slate-50 p-2 text-xs text-slate-600">
            {snapshot.draft}
          </p>
        </section>
      )}

      {snapshot.critique_feedback && (
        <section>
          <h4 className="mb-1 text-sm font-semibold text-slate-800">
            Critique: {snapshot.critique_decision ?? "pending"}
          </h4>
          <p className="rounded-md bg-amber-50 p-2 text-xs text-amber-900">
            {snapshot.critique_feedback}
          </p>
        </section>
      )}

      <section className="mt-auto">
        <h4 className="mb-1 text-sm font-semibold text-slate-800">Trace</h4>
        <ul className="space-y-1 text-xs text-slate-500">
          {trace.map((t, i) => (
            <li key={`${t.node}-${i}`}>
              <span className="font-mono text-slate-400">
                {new Date(t.timestamp).toLocaleTimeString()}
              </span>{" "}
              <span className="font-semibold text-slate-600">{t.node}</span>: {t.summary}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
