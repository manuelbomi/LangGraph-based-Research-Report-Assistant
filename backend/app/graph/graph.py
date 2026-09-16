"""Assembles the LangGraph `StateGraph` for the Research & Report Assistant.

    START -> plan -> research -> draft -> critique --revise--> research
                                              |
                                           approve
                                              v
                                        human_review --revise--> research
                                              |
                                    approve / reject
                                              v
                                          finalize -> END

Both loops (critique->research and human_review->research) are bounded by
`max_revision_loops` / `max_human_revision_loops` in `app/config.py` to
guarantee termination.
"""
from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    critique_node,
    draft_node,
    finalize_node,
    human_review_node,
    plan_node,
    research_node,
    route_after_critique,
    route_after_human_review,
)
from app.graph.state import ResearchState


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Build (and optionally compile-with-checkpointer) the research graph.

    Pass `checkpointer=None` to get an uncompiled-but-still-runnable graph
    with LangGraph's default in-memory checkpointing (handy for unit tests
    that don't need durability/interrupts across processes). Pass a real
    `AsyncPostgresSaver` in the FastAPI app for durable, resumable runs.
    """
    builder = StateGraph(ResearchState)

    builder.add_node("plan", plan_node)
    builder.add_node("research", research_node)
    builder.add_node("draft", draft_node)
    builder.add_node("critique", critique_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "plan")
    builder.add_edge("plan", "research")
    builder.add_edge("research", "draft")
    builder.add_edge("draft", "critique")

    builder.add_conditional_edges(
        "critique",
        route_after_critique,
        {"research": "research", "human_review": "human_review"},
    )
    builder.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {"research": "research", "finalize": "finalize"},
    )
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)
