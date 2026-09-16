"""REST + SSE API for starting, streaming, resuming, and listing research runs.

Concurrency model (intentionally simple for a tutorial app): each active run
gets one `asyncio.Queue` in `request.app.state.run_queues`, fed by a
background `asyncio.Task` that drives `graph.astream(...)`. The SSE endpoint
just relays whatever lands on that queue. Every event is also persisted to
the `runs` table as it happens, so a client that reconnects (or a run that
finished while nobody was watching) can still be inspected via
`GET /runs/{id}` / replayed via `GET /runs/{id}/stream`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from sqlalchemy import select

from app.api.schemas import (
    HumanDecisionRequest,
    RunCreateRequest,
    RunCreateResponse,
    RunDetail,
    RunListResponse,
    RunSummary,
)
from app.db.models import Run
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/runs", tags=["runs"])

# Keys not stored verbatim in state_snapshot because they're already
# first-class Run columns or are internal bookkeeping only.
_SNAPSHOT_EXCLUDE = {"trace"}


def _sse(event_type: str, data: dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"


def _merge_snapshot(existing: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in update.items():
        if key in _SNAPSHOT_EXCLUDE:
            continue
        if key == "findings" and isinstance(value, list):
            merged["findings"] = [*merged.get("findings", []), *value]
        else:
            merged[key] = value
    return merged


async def _run_graph(
    request: Request,
    thread_id: str,
    graph_input: Any,
) -> None:
    """Background task: drive the graph, persist + broadcast each step."""
    graph = request.app.state.graph
    queue: asyncio.Queue = request.app.state.run_queues[thread_id]
    config = {"configurable": {"thread_id": thread_id}}

    def _set_status(status: str, **extra: Any) -> None:
        with SessionLocal() as db:
            run = db.get(Run, thread_id)
            if run is None:
                return
            run.status = status
            for k, v in extra.items():
                setattr(run, k, v)
            db.commit()

    def _record_event(node_name: str, node_output: dict[str, Any]) -> None:
        trace_items = node_output.get("trace", [])
        with SessionLocal() as db:
            run = db.get(Run, thread_id)
            if run is None:
                return
            run.trace = [*run.trace, *trace_items]
            run.state_snapshot = _merge_snapshot(run.state_snapshot, node_output)
            db.commit()

    try:
        _set_status("running")
        async for event in graph.astream(graph_input, config=config, stream_mode="updates"):
            if "__interrupt__" in event:
                interrupt_obj = event["__interrupt__"][0]
                payload = dict(interrupt_obj.value)
                with SessionLocal() as db:
                    run = db.get(Run, thread_id)
                    if run is not None:
                        run.status = "awaiting_human"
                        run.state_snapshot = {**run.state_snapshot, "interrupt": payload}
                        db.commit()
                await queue.put(_sse("interrupt", payload))
                continue

            for node_name, node_output in event.items():
                if not isinstance(node_output, dict):
                    continue
                _record_event(node_name, node_output)
                await queue.put(
                    _sse(
                        "node",
                        {
                            "node": node_name,
                            "output": {k: v for k, v in node_output.items() if k != "trace"},
                            "trace": node_output.get("trace", []),
                        },
                    )
                )
                if node_name != "human_review":
                    _set_status("revising" if node_name in {"research", "draft", "critique"} else "running")

        # Loop ended without an interrupt -> graph ran to completion (END).
        state = await graph.aget_state(config)
        if not state.next:  # no pending nodes => finished
            values = state.values
            final_report = values.get("final_report")
            status = values.get("status", "completed")
            with SessionLocal() as db:
                run = db.get(Run, thread_id)
                if run is not None:
                    run.status = status
                    run.final_report = final_report
                    run.state_snapshot = _merge_snapshot(run.state_snapshot, values)
                    db.commit()
            await queue.put(_sse("done", {"status": status, "final_report": final_report}))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Run %s failed", thread_id)
        with SessionLocal() as db:
            run = db.get(Run, thread_id)
            if run is not None:
                run.status = "error"
                run.error = str(exc)
                db.commit()
        await queue.put(_sse("error", {"message": str(exc)}))
    finally:
        await queue.put(None)  # sentinel: close the SSE stream


def _start_background_run(request: Request, thread_id: str, graph_input: Any) -> None:
    queue: asyncio.Queue = asyncio.Queue()
    request.app.state.run_queues[thread_id] = queue
    task = asyncio.create_task(_run_graph(request, thread_id, graph_input))
    request.app.state.run_tasks[thread_id] = task


@router.post("", response_model=RunCreateResponse)
async def create_run(body: RunCreateRequest, request: Request) -> RunCreateResponse:
    thread_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        run = Run(
            id=thread_id,
            question=body.question,
            status="pending",
            trace=[],
            state_snapshot={},
            created_at=now,
            updated_at=now,
        )
        db.add(run)
        db.commit()

    _start_background_run(request, thread_id, {"question": body.question})
    return RunCreateResponse(id=thread_id, status="pending", question=body.question)


@router.post("/{run_id}/resume", response_model=RunCreateResponse)
async def resume_run(run_id: str, body: HumanDecisionRequest, request: Request) -> RunCreateResponse:
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if run is None:
            raise HTTPException(404, "run not found")
        if run.status != "awaiting_human":
            raise HTTPException(409, f"run is not awaiting human review (status={run.status})")
        question = run.question

    _start_background_run(
        request, run_id, Command(resume={"decision": body.decision, "feedback": body.feedback})
    )
    return RunCreateResponse(id=run_id, status="running", question=question)


@router.get("/{run_id}/stream")
async def stream_run(run_id: str, request: Request) -> StreamingResponse:
    async def event_source():
        queue: asyncio.Queue | None = request.app.state.run_queues.get(run_id)

        if queue is None:
            # No live background task (already finished, or the server was
            # restarted after this run reached a terminal/awaiting state).
            # Replay what's durably stored instead of streaming live.
            with SessionLocal() as db:
                run = db.get(Run, run_id)
            if run is None:
                yield _sse("error", {"message": "run not found"})
                return
            yield _sse(
                "replay",
                {
                    "status": run.status,
                    "trace": run.trace,
                    "state_snapshot": run.state_snapshot,
                    "final_report": run.final_report,
                },
            )
            if run.status == "awaiting_human":
                interrupt_payload = run.state_snapshot.get("interrupt", {})
                yield _sse("interrupt", interrupt_payload)
            yield _sse("done", {"status": run.status, "final_report": run.final_report})
            return

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("", response_model=RunListResponse)
async def list_runs() -> RunListResponse:
    with SessionLocal() as db:
        rows = db.execute(select(Run).order_by(Run.created_at.desc())).scalars().all()
        return RunListResponse(
            runs=[
                RunSummary(
                    id=r.id,
                    question=r.question,
                    status=r.status,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
                for r in rows
            ]
        )


@router.get("/{run_id}", response_model=RunDetail)
async def get_run(run_id: str) -> RunDetail:
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if run is None:
            raise HTTPException(404, "run not found")
        return RunDetail(
            id=run.id,
            question=run.question,
            status=run.status,
            final_report=run.final_report,
            trace=run.trace,
            state_snapshot=run.state_snapshot,
            error=run.error,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )
