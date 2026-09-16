import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { RunSummary } from "../api/types";
import { RunHistory } from "../components/RunHistory";

const SEEDED_RUNS: RunSummary[] = [
  {
    id: "r1",
    question: "What are the main renewable energy sources, and how has their cost changed?",
    status: "completed",
    created_at: "2026-09-13T10:00:00Z",
    updated_at: "2026-09-13T10:06:00Z",
  },
  {
    id: "r2",
    question: "How do microservices compare to monolithic architectures?",
    status: "completed",
    created_at: "2026-09-16T02:00:00Z",
    updated_at: "2026-09-16T02:04:00Z",
  },
];

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("RunHistory", () => {
  it("renders the seeded example runs with their questions and statuses", () => {
    renderWithRouter(<RunHistory runs={SEEDED_RUNS} />);

    expect(
      screen.getByText(/main renewable energy sources/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/microservices compare/i)).toBeInTheDocument();
    expect(screen.getAllByText(/completed/i)).toHaveLength(2);
  });

  it("links each run to its detail page", () => {
    renderWithRouter(<RunHistory runs={SEEDED_RUNS} />);

    const links = screen.getAllByRole("link");
    expect(links[0]).toHaveAttribute("href", "/runs/r1");
    expect(links[1]).toHaveAttribute("href", "/runs/r2");
  });

  it("shows an empty state when there are no runs", () => {
    renderWithRouter(<RunHistory runs={[]} />);

    expect(screen.getByText(/no runs yet/i)).toBeInTheDocument();
  });
});
