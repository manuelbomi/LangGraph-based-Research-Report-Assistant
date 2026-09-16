"""End-to-end graph flow test using LangGraph's in-memory checkpointer.

This proves the interrupt/resume *mechanics* (the same API the FastAPI app
uses against Postgres in `app/db/checkpointer.py`) without needing a real
database or LLM. The equivalent test against a *real* Postgres checkpointer
and a *real* OpenAI key lives in `tests/live/test_live_smoke.py`.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph.graph import build_graph
from app.tools.knowledge_base import KBResult
from app.tools.web_search import WebResult


async def test_graph_pauses_at_human_review_and_resumes_to_completion(
    fake_chat_model, fake_prompts, monkeypatch
):
    monkeypatch.setattr("app.graph.nodes.search_web",
                         lambda q, max_results=3: [WebResult(title="T", url="http://x", snippet="s")])
    monkeypatch.setattr("app.graph.nodes.search_kb", lambda q, top_k=3: [])

    fake_chat_model([
        '["What is the main sub-question?"]',        # plan
        "A synthesized answer citing [S1].",          # research summarization
        "# Report\n\nA synthesized answer citing [S1].",  # draft
        '{"decision": "approve", "feedback": "Good."}',  # critique
    ])

    graph = build_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "test-thread-1"}}

    result = None
    async for event in graph.astream({"question": "What is X?"}, config=config, stream_mode="updates"):
        result = event

    assert result is not None
    assert "__interrupt__" in result, "graph should pause at human_review"
    interrupt_payload = result["__interrupt__"][0].value
    assert "draft" in interrupt_payload
    assert interrupt_payload["critique_feedback"] == "Good."

    state_before_resume = await graph.aget_state(config)
    assert state_before_resume.next == ("human_review",)

    final_event = None
    async for event in graph.astream(
        Command(resume={"decision": "approve", "feedback": "Ship it."}),
        config=config,
        stream_mode="updates",
    ):
        final_event = event

    assert "finalize" in final_event
    final_state = await graph.aget_state(config)
    assert final_state.next == ()  # graph reached END
    assert final_state.values["status"] == "completed"
    assert "## Sources" in final_state.values["final_report"]


async def test_graph_bounded_critique_loop_terminates(fake_chat_model, fake_prompts, monkeypatch):
    """A critique that always says 'revise' must still terminate (forced
    approve after `max_revision_loops`), proving the cycle is bounded."""
    monkeypatch.setattr("app.graph.nodes.search_web",
                         lambda q, max_results=3: [WebResult(title="T", url="http://x", snippet="s")])
    monkeypatch.setattr("app.graph.nodes.search_kb", lambda q, top_k=3: [])

    # plan, then 3x (research + critique) since max_revision_loops=2 means:
    # pass 1 critique -> revise (count=1), pass 2 critique -> revise (count=2,
    # still < cap check happens BEFORE increment... see nodes.critique_node),
    # pass 3 critique -> forced approve.
    fake_chat_model([
        '["sub question?"]',
        "synthesis 1 [S1]",
        "draft 1",
        '{"decision": "revise", "feedback": "more detail"}',
        "synthesis 2 [S2]",
        "draft 2",
        '{"decision": "revise", "feedback": "still more"}',
        "synthesis 3 [S3]",
        "draft 3",
        '{"decision": "revise", "feedback": "never satisfied"}',
    ])

    graph = build_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "test-thread-2"}}

    last_event = None
    async for event in graph.astream({"question": "What is X?"}, config=config, stream_mode="updates"):
        last_event = event

    assert "__interrupt__" in last_event
    state = await graph.aget_state(config)
    assert state.values["critique_decision"] == "approve"
    assert "forced" in state.values["trace"][-1]["summary"].lower() or "auto-approved" in state.values["critique_feedback"].lower()
