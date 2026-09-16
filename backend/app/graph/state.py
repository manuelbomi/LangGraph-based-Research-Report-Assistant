"""Graph state schema.

A `TypedDict` (LangGraph's preferred state shape) rather than a Pydantic
model, so partial node returns (`{"draft": "..."}`) merge cleanly via
LangGraph's default "last write wins per key" reducer without needing
custom Annotated reducers for the fields we mutate wholesale each pass.
`findings` and `trace` *do* use `operator.add` reducers so each research
pass appends rather than clobbering prior findings.
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class Finding(TypedDict):
    source_id: str  # e.g. "S1" -- referenced by [S1] citation tags
    sub_question: str
    source_type: str  # "web" | "kb"
    title: str
    url_or_doc_id: str
    synthesis: str  # LLM-synthesized, cited answer to the sub-question


class TraceEvent(TypedDict):
    node: str
    timestamp: str
    summary: str


class ResearchState(TypedDict, total=False):
    # --- input ---
    question: str

    # --- plan ---
    sub_questions: list[str]

    # --- research (accumulates across revision loops) ---
    findings: Annotated[list[Finding], operator.add]

    # --- draft ---
    draft: str
    draft_revision: int

    # --- critique ---
    critique_decision: str  # "approve" | "revise"
    critique_feedback: str
    revision_count: int

    # --- human review ---
    human_decision: str  # "approve" | "revise" | "reject" | ""
    human_feedback: str
    human_revision_count: int

    # --- finalize ---
    final_report: str
    status: str  # mirrors app.db.models.Run.status

    # --- observability (appended to, not replaced) ---
    trace: Annotated[list[TraceEvent], operator.add]
