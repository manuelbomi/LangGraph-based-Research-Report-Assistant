"""Unit tests for individual graph nodes and routing functions.

Everything here is mocked: LLM calls go through `FakeChatModel` (see
conftest.py), and the web/KB tools are monkeypatched directly. No network,
no Postgres, no API key spend.
"""
from __future__ import annotations

import pytest

from app.graph import nodes
from app.tools.knowledge_base import KBResult
from app.tools.web_search import WebResult


# ---------------------------------------------------------------------
# plan_node
# ---------------------------------------------------------------------
async def test_plan_node_parses_json_list(fake_chat_model, fake_prompts):
    fake_chat_model(['["What is X?", "What is Y?"]'])
    state = {"question": "What is renewable energy?"}

    result = await nodes.plan_node(state)

    assert result["sub_questions"] == ["What is X?", "What is Y?"]
    assert len(result["trace"]) == 1
    assert result["trace"][0]["node"] == "plan"


async def test_plan_node_handles_fenced_json(fake_chat_model, fake_prompts):
    fake_chat_model(['```json\n["only one question?"]\n```'])
    state = {"question": "anything"}

    result = await nodes.plan_node(state)

    assert result["sub_questions"] == ["only one question?"]


async def test_plan_node_falls_back_on_bad_json(fake_chat_model, fake_prompts):
    fake_chat_model(["this is not json at all"])
    state = {"question": "What is renewable energy?"}

    result = await nodes.plan_node(state)

    assert result["sub_questions"] == ["What is renewable energy?"]


async def test_plan_node_caps_at_four_subquestions(fake_chat_model, fake_prompts):
    fake_chat_model([str(["q1", "q2", "q3", "q4", "q5", "q6"]).replace("'", '"')])
    state = {"question": "anything"}

    result = await nodes.plan_node(state)

    assert len(result["sub_questions"]) == 4


# ---------------------------------------------------------------------
# should_consult_kb heuristic
# ---------------------------------------------------------------------
@pytest.mark.parametrize(
    "sub_question,expected",
    [
        ("What are the main types of solar energy technology?", True),
        ("How has wind turbine capacity grown since the 1980s?", True),
        ("What is a feed-in tariff and how does it work?", True),
        ("How do microservices compare to monolithic architectures?", False),
        ("What is the capital of France?", False),
    ],
)
def test_should_consult_kb(sub_question, expected):
    assert nodes.should_consult_kb(sub_question) is expected


# ---------------------------------------------------------------------
# research_node
# ---------------------------------------------------------------------
async def test_research_node_uses_web_when_no_kb_match(fake_chat_model, fake_prompts, monkeypatch):
    monkeypatch.setattr(
        nodes, "search_web",
        lambda query, max_results=3: [WebResult(title="Result A", url="http://a.test", snippet="snippet A")],
    )
    called = {"kb": False}

    def fake_search_kb(*args, **kwargs):
        called["kb"] = True
        return []

    monkeypatch.setattr(nodes, "search_kb", fake_search_kb)
    fake_chat_model(["Synthesis referencing [S1]."])

    state = {"sub_questions": ["How do microservices compare to monoliths?"], "findings": []}
    result = await nodes.research_node(state)

    assert called["kb"] is False
    assert len(result["findings"]) == 1
    assert result["findings"][0]["source_type"] == "web"
    assert result["findings"][0]["source_id"] == "S1"


async def test_research_node_uses_kb_when_topic_matches(fake_chat_model, fake_prompts, monkeypatch):
    monkeypatch.setattr(
        nodes, "search_kb",
        lambda query, top_k=3: [KBResult(doc_id="re-003", title="Solar PV", snippet="...", score=0.9)],
    )
    monkeypatch.setattr(nodes, "search_web", lambda *a, **k: pytest.fail("should not call web search"))
    fake_chat_model(["Synthesis referencing [S1]."])

    state = {"sub_questions": ["How efficient are modern solar panels?"], "findings": []}
    result = await nodes.research_node(state)

    assert len(result["findings"]) == 1
    assert result["findings"][0]["source_type"] == "kb"


async def test_research_node_continues_source_numbering_across_passes(fake_chat_model, fake_prompts, monkeypatch):
    monkeypatch.setattr(
        nodes, "search_web",
        lambda query, max_results=3: [WebResult(title="R", url="http://x", snippet="s")],
    )
    monkeypatch.setattr(nodes, "search_kb", lambda *a, **k: [])
    fake_chat_model(["synthesis"])

    existing = [{"source_id": "S1", "sub_question": "q0", "source_type": "web",
                 "title": "t", "url_or_doc_id": "u", "synthesis": "x"}]
    state = {"sub_questions": ["a new sub-question"], "findings": existing}

    result = await nodes.research_node(state)

    assert result["findings"][0]["source_id"] == "S2"


# ---------------------------------------------------------------------
# critique_node
# ---------------------------------------------------------------------
async def test_critique_node_approves(fake_chat_model, fake_prompts):
    fake_chat_model(['{"decision": "approve", "feedback": "Looks solid."}'])
    state = {"question": "q", "draft": "some draft", "findings": [], "revision_count": 0}

    result = await nodes.critique_node(state)

    assert result["critique_decision"] == "approve"
    assert result["revision_count"] == 0


async def test_critique_node_requests_revision(fake_chat_model, fake_prompts):
    fake_chat_model(['{"decision": "revise", "feedback": "Add more detail on X."}'])
    state = {"question": "q", "draft": "some draft", "findings": [], "revision_count": 0}

    result = await nodes.critique_node(state)

    assert result["critique_decision"] == "revise"
    assert result["revision_count"] == 1


async def test_critique_node_forces_approval_at_revision_cap(fake_chat_model, fake_prompts):
    fake_chat_model(['{"decision": "revise", "feedback": "still not great"}'])
    # max_revision_loops defaults to 2 (see app/config.py); simulate being at the cap.
    state = {"question": "q", "draft": "draft", "findings": [], "revision_count": 2}

    result = await nodes.critique_node(state)

    assert result["critique_decision"] == "approve"
    assert "forced" in result["trace"][0]["summary"].lower() or "auto-approved" in result["critique_feedback"].lower()


def test_route_after_critique():
    assert nodes.route_after_critique({"critique_decision": "revise"}) == "research"
    assert nodes.route_after_critique({"critique_decision": "approve"}) == "human_review"


# ---------------------------------------------------------------------
# route_after_human_review
# ---------------------------------------------------------------------
def test_route_after_human_review_approve():
    assert nodes.route_after_human_review({"human_decision": "approve"}) == "finalize"


def test_route_after_human_review_reject():
    assert nodes.route_after_human_review({"human_decision": "reject"}) == "finalize"


def test_route_after_human_review_revise_under_cap():
    assert nodes.route_after_human_review({"human_decision": "revise", "human_revision_count": 1}) == "research"


def test_route_after_human_review_revise_over_cap():
    assert nodes.route_after_human_review({"human_decision": "revise", "human_revision_count": 2}) == "finalize"


# ---------------------------------------------------------------------
# finalize_node
# ---------------------------------------------------------------------
async def test_finalize_node_completed():
    state = {
        "question": "q",
        "draft": "draft body",
        "human_decision": "approve",
        "findings": [
            {"source_id": "S1", "sub_question": "sq", "source_type": "web",
             "title": "Title", "url_or_doc_id": "http://x", "synthesis": "..."}
        ],
    }
    result = await nodes.finalize_node(state)

    assert result["status"] == "completed"
    assert "draft body" in result["final_report"]
    assert "## Sources" in result["final_report"]
    assert "S1" in result["final_report"]


async def test_finalize_node_rejected():
    state = {
        "question": "q",
        "draft": "draft body",
        "human_decision": "reject",
        "human_feedback": "Not aligned with the question.",
        "findings": [],
    }
    result = await nodes.finalize_node(state)

    assert result["status"] == "rejected"
    assert "rejected" in result["final_report"].lower()
    assert "Not aligned with the question." in result["final_report"]
