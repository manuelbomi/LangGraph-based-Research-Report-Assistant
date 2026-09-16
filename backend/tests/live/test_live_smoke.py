"""REAL end-to-end smoke test: actual OpenAI API calls + a real Postgres.

This is deliberately excluded from the default `pytest` run (see the `live`
marker + `addopts` in `pyproject.toml`). Run it explicitly with:

    export OPENAI_API_KEY=sk-...           # real key
    export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/research_assistant
    pytest -m live tests/live/test_live_smoke.py -v -s

What it proves, with no mocks anywhere in the graph/LLM/DB path:
  1. A full run (plan -> research -> draft -> critique) reaches
     `human_review` and genuinely pauses there (`interrupt()`).
  2. The checkpointer can be torn down and a BRAND NEW `AsyncPostgresSaver`
     + freshly-compiled graph (standing in for "a new process") can resume
     that exact thread and finish the run (`finalize`).

Cost note: this makes ~4-6 small `gpt-4o-mini` chat completions total
(plan, one research synthesis per sub-question, draft, critique) and zero
embedding calls (the smoke-test question deliberately avoids the renewable
-energy knowledge-base keywords, so it exercises the web-search path, which
also sidesteps Milvus Lite's Linux/macOS-only requirement on a Windows
host -- see README).
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

if sys.platform == "win32":
    # psycopg's async mode cannot run on Windows' default ProactorEventLoop;
    # it needs a selector-based loop. This only matters for local dev on
    # Windows -- the backend Docker image (and CI) run on Linux, where this
    # is a no-op. See: https://www.psycopg.org/psycopg3/docs/advanced/async.html
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from alembic import command
from alembic.config import Config
from langgraph.types import Command

from app.db.checkpointer import build_checkpointer
from app.graph.graph import build_graph
from app.prompts.seed_prompts import seed as seed_prompts

pytestmark = pytest.mark.live

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run_migrations() -> None:
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "app", "db", "migrations"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="module", autouse=True)
def _prepare_schema():
    assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY must be set for the live smoke test"
    assert os.environ.get("DATABASE_URL"), "DATABASE_URL must point at a real reachable Postgres"
    _run_migrations()
    seed_prompts()
    yield


async def test_live_full_run_survives_checkpointer_restart():
    thread_id = "live-smoke-thread"
    config = {"configurable": {"thread_id": thread_id}}
    question = "What is the difference between TCP and UDP, in brief?"

    # --- Phase 1: run until it pauses at human_review ------------------
    async with build_checkpointer() as checkpointer_1:
        graph_1 = build_graph(checkpointer=checkpointer_1)

        saw_interrupt = False
        async for event in graph_1.astream({"question": question}, config=config, stream_mode="updates"):
            print("EVENT:", list(event.keys()))
            if "__interrupt__" in event:
                saw_interrupt = True
                payload = event["__interrupt__"][0].value
                assert payload["draft"], "expected a non-empty draft in the interrupt payload"
                print("\n--- DRAFT AT HUMAN_REVIEW ---\n", payload["draft"][:500], "...\n")
        assert saw_interrupt, "graph should have paused at human_review"

        state = await graph_1.aget_state(config)
        assert state.next == ("human_review",)
    # `async with` exits here -> checkpointer_1's connection pool is fully
    # closed, simulating the backend process shutting down.

    # --- Phase 2: brand new checkpointer + graph, standing in for a ----
    # --- freshly-started process, resumes the SAME thread_id -----------
    async with build_checkpointer() as checkpointer_2:
        graph_2 = build_graph(checkpointer=checkpointer_2)

        # Prove the state genuinely persisted in Postgres, not in memory.
        resumed_state = await graph_2.aget_state(config)
        assert resumed_state.next == ("human_review",)
        assert resumed_state.values["question"] == question

        finished = False
        async for event in graph_2.astream(
            Command(resume={"decision": "approve", "feedback": "Approved by live smoke test."}),
            config=config,
            stream_mode="updates",
        ):
            print("RESUME EVENT:", list(event.keys()))
            if "finalize" in event:
                finished = True

        assert finished, "graph should have reached finalize after resume"
        final_state = await graph_2.aget_state(config)
        assert final_state.next == ()
        assert final_state.values["status"] == "completed"
        assert final_state.values["final_report"]
        print("\n--- FINAL REPORT ---\n", final_state.values["final_report"][:800], "...\n")
