import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listRuns } from "../api/client";
import { RunHistory } from "../components/RunHistory";

export function HistoryPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["runs"],
    queryFn: listRuns,
  });

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Run history</h2>
          <p className="text-sm text-slate-500">
            Past runs, including seeded example analyses -- click any run for its full
            step-by-step trace and final report.
          </p>
        </div>
        <Link
          to="/"
          className="shrink-0 rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
        >
          New run
        </Link>
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading runs...</p>}
      {isError && <p className="text-sm text-rose-600">{(error as Error).message}</p>}
      {data && <RunHistory runs={data.runs} />}
    </div>
  );
}
