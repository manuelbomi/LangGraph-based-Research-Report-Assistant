import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { createRun } from "../api/client";

export function NewRunPage() {
  const [question, setQuestion] = useState("");
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: createRun,
    onSuccess: (data) => navigate(`/runs/${data.id}`),
  });

  return (
    <div className="mx-auto max-w-2xl">
      <h2 className="mb-2 text-xl font-semibold text-slate-900">Start a new research run</h2>
      <p className="mb-6 text-sm text-slate-500">
        Ask a question. The graph will plan sub-questions, research them (web search and/or the
        internal knowledge base), draft a cited report, critique and revise it automatically,
        then pause for your review before finalizing.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (question.trim().length >= 3) {
            mutation.mutate({ question: question.trim() });
          }
        }}
        className="space-y-3"
      >
        <textarea
          className="w-full rounded-lg border border-slate-300 p-3 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          rows={4}
          placeholder="e.g. What are the main renewable energy sources, and how has their cost changed over the last two decades?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button
          type="submit"
          disabled={mutation.isPending || question.trim().length < 3}
          className="rounded-md bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:opacity-50"
        >
          {mutation.isPending ? "Starting..." : "Start research run"}
        </button>
        {mutation.isError && (
          <p className="text-sm text-rose-600">{(mutation.error as Error).message}</p>
        )}
      </form>
    </div>
  );
}
