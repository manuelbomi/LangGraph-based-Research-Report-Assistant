"""API contract tests for the /runs endpoints.

Uses a lightweight in-memory fake in place of the Postgres-backed
`SessionLocal`, and an `InMemorySaver` in place of the Postgres checkpointer,
so these run without any real database. LLM + tool calls are mocked exactly
as in `test_graph_nodes.py` / `test_graph_flow.py`.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import InMemorySaver

from app.api.routers.runs import router as runs_router
from app.db.models import Run
from app.graph.graph import build_graph
from app.tools.web_search import WebResult


class _FakeResultSet:
    def __init__(self, rows: list[Run]):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, store: dict[str, Run]):
        self._store = store

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def add(self, obj: Run) -> None:
        self._store[obj.id] = obj

    def commit(self) -> None:
        pass

    def get(self, _model, run_id: str):
        return self._store.get(run_id)

    def execute(self, _stmt):
        rows = sorted(self._store.values(), key=lambda r: r.created_at, reverse=True)
        return _FakeResultSet(rows)


@pytest.fixture
def api_app(monkeypatch, fake_chat_model, fake_prompts):
    store: dict[str, Run] = {}
    monkeypatch.setattr(
        "app.api.routers.runs.SessionLocal", lambda: _FakeSession(store)
    )
    monkeypatch.setattr(
        "app.graph.nodes.search_web",
        lambda q, max_results=3: [WebResult(title="T", url="http://x", snippet="s")],
    )
    monkeypatch.setattr("app.graph.nodes.search_kb", lambda q, top_k=3: [])

    app = FastAPI()
    app.state.run_queues = {}
    app.state.run_tasks = {}
    app.state.graph = build_graph(checkpointer=InMemorySaver())
    app.include_router(runs_router)
    return app, store


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_create_run_and_reach_human_review(api_app, fake_chat_model):
    app, store = api_app
    fake_chat_model([
        '["What is the sub-question?"]',
        "A synthesized finding [S1].",
        "# Report draft [S1]",
        '{"decision": "approve", "feedback": "Solid."}',
    ])

    async with await _client(app) as client:
        resp = await client.post("/runs", json={"question": "What is X and why does it matter?"})
        assert resp.status_code == 200
        body = resp.json()
        run_id = body["id"]
        assert body["status"] == "pending"

        await app.state.run_tasks[run_id]  # let the background graph run finish this leg

        detail = await client.get(f"/runs/{run_id}")
        assert detail.status_code == 200
        detail_body = detail.json()
        assert detail_body["status"] == "awaiting_human"
        assert detail_body["state_snapshot"]["interrupt"]["draft"]
        assert len(detail_body["trace"]) >= 3  # plan, research, draft, critique


async def test_resume_run_completes(api_app, fake_chat_model):
    app, store = api_app
    fake_chat_model([
        '["sub-question?"]',
        "synthesis [S1]",
        "# Report draft [S1]",
        '{"decision": "approve", "feedback": "ok"}',
    ])

    async with await _client(app) as client:
        resp = await client.post("/runs", json={"question": "A real question here?"})
        run_id = resp.json()["id"]
        await app.state.run_tasks[run_id]

        resume_resp = await client.post(
            f"/runs/{run_id}/resume", json={"decision": "approve", "feedback": "Great work."}
        )
        assert resume_resp.status_code == 200
        await app.state.run_tasks[run_id]

        detail = await client.get(f"/runs/{run_id}")
        detail_body = detail.json()
        assert detail_body["status"] == "completed"
        assert "## Sources" in detail_body["final_report"]


async def test_resume_rejects_when_not_awaiting_human(api_app):
    app, _ = api_app
    async with await _client(app) as client:
        resp = await client.post(
            "/runs/does-not-exist/resume", json={"decision": "approve", "feedback": ""}
        )
        assert resp.status_code == 404


async def test_list_runs_returns_summaries(api_app):
    app, store = api_app
    from datetime import datetime, timezone

    store["r1"] = Run(id="r1", question="Q1", status="completed", trace=[], state_snapshot={},
                       created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    store["r2"] = Run(id="r2", question="Q2", status="awaiting_human", trace=[], state_snapshot={},
                       created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))

    async with await _client(app) as client:
        resp = await client.get("/runs")
        assert resp.status_code == 200
        ids = {r["id"] for r in resp.json()["runs"]}
        assert ids == {"r1", "r2"}


async def test_get_unknown_run_404(api_app):
    app, _ = api_app
    async with await _client(app) as client:
        resp = await client.get("/runs/nope")
        assert resp.status_code == 404
