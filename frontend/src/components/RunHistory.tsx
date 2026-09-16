import { Link } from "react-router-dom";

import type { RunSummary } from "../api/types";

const STATUS_STYLES: Record<string, string> = {
  completed: "bg-emerald-100 text-emerald-800",
  rejected: "bg-rose-100 text-rose-800",
  awaiting_human: "bg-amber-100 text-amber-800",
  running: "bg-brand-100 text-brand-800",
  revising: "bg-brand-100 text-brand-800",
  pending: "bg-slate-100 text-slate-700",
  error: "bg-rose-100 text-rose-800",
};

export function RunHistory({ runs }: { runs: RunSummary[] }) {
  if (runs.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
        No runs yet. Start a new research run to see it appear here.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white" role="list">
      {runs.map((run) => (
        <li key={run.id}>
          <Link
            to={`/runs/${run.id}`}
            className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-slate-50"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-800">{run.question}</p>
              <p className="text-xs text-slate-400">
                {new Date(run.created_at).toLocaleString()}
              </p>
            </div>
            <span
              className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${
                STATUS_STYLES[run.status] ?? "bg-slate-100 text-slate-700"
              }`}
            >
              {run.status.replace("_", " ")}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
