"""Pydantic request/response schemas for the REST + SSE API.

Keep these in sync with `frontend/src/api/types.ts` -- that file is a
hand-written TypeScript mirror of this one.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RunStatus = Literal[
    "pending", "running", "awaiting_human", "revising", "completed", "rejected", "error"
]


class RunCreateRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class RunCreateResponse(BaseModel):
    id: str
    status: RunStatus
    question: str


class HumanDecisionRequest(BaseModel):
    decision: Literal["approve", "revise", "reject"]
    feedback: str = ""


class TraceEventOut(BaseModel):
    node: str
    timestamp: datetime
    summary: str


class RunSummary(BaseModel):
    id: str
    question: str
    status: RunStatus
    created_at: datetime
    updated_at: datetime


class RunDetail(BaseModel):
    id: str
    question: str
    status: RunStatus
    final_report: str | None
    trace: list[TraceEventOut]
    state_snapshot: dict[str, Any]
    error: str | None
    created_at: datetime
    updated_at: datetime


class RunListResponse(BaseModel):
    runs: list[RunSummary]
