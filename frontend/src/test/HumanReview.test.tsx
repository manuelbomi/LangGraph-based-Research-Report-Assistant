import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { InterruptPayload } from "../api/types";
import { HumanReview } from "../components/HumanReview";

const INTERRUPT: InterruptPayload = {
  question: "What is renewable energy?",
  draft: "# Report\n\nRenewable energy comes from naturally replenishing sources.",
  critique_feedback: "Well-cited and complete.",
  sub_questions: ["What is renewable energy?"],
};

describe("HumanReview", () => {
  it("calls onDecision with approve when Approve is clicked", async () => {
    const onDecision = vi.fn();
    const user = userEvent.setup();
    render(<HumanReview interrupt={INTERRUPT} onDecision={onDecision} />);

    await user.click(screen.getByRole("button", { name: /approve/i }));

    expect(onDecision).toHaveBeenCalledWith({ decision: "approve", feedback: "" });
  });

  it("calls onDecision with reject when Reject is clicked", async () => {
    const onDecision = vi.fn();
    const user = userEvent.setup();
    render(<HumanReview interrupt={INTERRUPT} onDecision={onDecision} />);

    await user.click(screen.getByRole("button", { name: /reject/i }));

    expect(onDecision).toHaveBeenCalledWith({ decision: "reject", feedback: "" });
  });

  it("reveals a feedback box and sends it as revise", async () => {
    const onDecision = vi.fn();
    const user = userEvent.setup();
    render(<HumanReview interrupt={INTERRUPT} onDecision={onDecision} />);

    // First click reveals the free-text box instead of submitting immediately.
    await user.click(screen.getByRole("button", { name: /request changes/i }));
    expect(onDecision).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText(/requested changes/i), "Add more sources.");
    await user.click(screen.getByRole("button", { name: /request changes/i }));

    expect(onDecision).toHaveBeenCalledWith({ decision: "revise", feedback: "Add more sources." });
  });

  it("renders the draft and critique feedback", () => {
    render(<HumanReview interrupt={INTERRUPT} onDecision={vi.fn()} />);

    expect(screen.getByText(/well-cited and complete/i)).toBeInTheDocument();
    expect(screen.getByText(/naturally replenishing sources/i)).toBeInTheDocument();
  });

  it("disables the buttons while submitting", () => {
    render(<HumanReview interrupt={INTERRUPT} onDecision={vi.fn()} submitting />);

    expect(screen.getByRole("button", { name: /approve/i })).toBeDisabled();
  });
});
