"""LangGraph node implementations for the Research & Report Assistant.

Six real (non-stub) nodes:
  plan          - LLM breaks the question into 2-4 sub-questions
  research      - per sub-question, picks web search / knowledge-base / both,
                  then an LLM synthesizes a cited finding
  draft         - LLM writes a cited markdown report from the findings
  critique      - LLM approves or requests revision (bounded loop back to
                  research)
  human_review  - interrupt() pauses the graph for a human decision
  finalize      - assembles the final markdown report (+ sources section)
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from langgraph.types import interrupt

from app.config import get_settings
from app.graph.state import Finding, ResearchState, TraceEvent
from app.llm import get_chat_model
from app.prompts import render_prompt
from app.tools.knowledge_base import KB_TOPIC_KEYWORDS, search_kb
from app.tools.web_search import search_web

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trace(node: str, summary: str) -> list[TraceEvent]:
    return [{"node": node, "timestamp": _now(), "summary": summary}]


def _extract_json(text: str) -> str:
    """Strip ```json ... ``` fences an LLM may wrap its answer in."""
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text.strip()


# --------------------------------------------------------------------------
# 1. plan
# --------------------------------------------------------------------------
async def plan_node(state: ResearchState) -> dict:
    llm = get_chat_model()
    revision_context = ""
    if state.get("critique_feedback"):
        revision_context = (
            "Note: this is a revision. Prior reviewer feedback to address: "
            f"{state['critique_feedback']}"
        )

    prompt = render_prompt(
        "plan", question=state["question"], revision_context=revision_context
    )
    response = await llm.ainvoke(prompt)
    raw = _extract_json(response.content if isinstance(response.content, str) else str(response.content))

    try:
        sub_questions = json.loads(raw)
        if not isinstance(sub_questions, list) or not sub_questions:
            raise ValueError("empty or non-list plan response")
        sub_questions = [str(q) for q in sub_questions][:4]
    except (json.JSONDecodeError, ValueError):
        logger.warning("plan_node: failed to parse LLM JSON, falling back. raw=%r", raw)
        sub_questions = [state["question"]]

    return {
        "sub_questions": sub_questions,
        "trace": _trace("plan", f"Generated {len(sub_questions)} sub-question(s)."),
    }


# --------------------------------------------------------------------------
# 2. research
# --------------------------------------------------------------------------
def should_consult_kb(sub_question: str) -> bool:
    """Real, inspectable heuristic: does this sub-question plausibly fall
    inside the fixed demo knowledge base's topic (renewable energy)?

    A production system might instead have the LLM classify per
    sub-question, or run a cheap embedding-similarity threshold against the
    KB's topic centroid; a keyword heuristic is used here to keep the
    research node fast and free of extra LLM calls for the routing
    decision itself.
    """
    lowered = sub_question.lower()
    return any(keyword in lowered for keyword in KB_TOPIC_KEYWORDS)


async def research_node(state: ResearchState) -> dict:
    llm = get_chat_model()
    existing_findings = state.get("findings", [])
    next_source_num = len(existing_findings) + 1
    settings = get_settings()

    new_findings: list[Finding] = []
    research_log: list[str] = []

    for sub_question in state["sub_questions"]:
        use_kb = should_consult_kb(sub_question)
        raw_snippets: list[str] = []
        # (source_id, source_type, title, url_or_doc_id)
        snippet_sources: list[tuple[str, str, str, str]] = []
        kb_hit_count = 0

        if use_kb:
            kb_hits = search_kb(sub_question, top_k=settings.kb_search_top_k)
            for hit in kb_hits:
                sid = f"S{next_source_num}"
                next_source_num += 1
                raw_snippets.append(f"[{sid}] (knowledge base: {hit.title}) {hit.snippet}")
                snippet_sources.append((sid, "kb", hit.title, hit.doc_id))
            kb_hit_count = len(kb_hits)

        # Always also check the web, unless the KB heuristic didn't fire for
        # this sub-question, or fired but came up empty -- this keeps the
        # demo cheap while still genuinely branching behavior based on
        # `use_kb`.
        used_web = False
        if not use_kb or kb_hit_count == 0:
            web_hits = search_web(sub_question, max_results=settings.web_search_max_results)
            for hit in web_hits:
                sid = f"S{next_source_num}"
                next_source_num += 1
                raw_snippets.append(f"[{sid}] (web: {hit.title}) {hit.snippet}")
                snippet_sources.append((sid, "web", hit.title, hit.url))
            used_web = bool(web_hits)

        if not raw_snippets:
            research_log.append(f"No sources found for: {sub_question!r}")
            continue

        synthesis_prompt = render_prompt(
            "research_summarize",
            sub_question=sub_question,
            raw_snippets="\n".join(raw_snippets),
        )
        response = await llm.ainvoke(synthesis_prompt)
        synthesis_text = (
            response.content if isinstance(response.content, str) else str(response.content)
        )

        # One Finding per source consulted, all sharing the same synthesis
        # text (so the draft/critique prompts can render a clean per-source
        # citation list while the synthesis reads as one coherent answer).
        for sid, source_type, title, ref in snippet_sources:
            new_findings.append(
                Finding(
                    source_id=sid,
                    sub_question=sub_question,
                    source_type=source_type,
                    title=title,
                    url_or_doc_id=ref,
                    synthesis=synthesis_text.strip(),
                )
            )
        tool_label = "kb+web" if (kb_hit_count and used_web) else ("kb" if kb_hit_count else "web")
        research_log.append(
            f"{sub_question!r} -> {len(snippet_sources)} source(s) via {tool_label}"
        )

    return {
        "findings": new_findings,
        "trace": _trace("research", "; ".join(research_log) or "No findings gathered."),
    }


def _findings_block(findings: list[Finding]) -> str:
    lines = []
    by_sub_question: dict[str, list[Finding]] = {}
    for f in findings:
        by_sub_question.setdefault(f["sub_question"], []).append(f)
    for sub_question, group in by_sub_question.items():
        lines.append(f"### {sub_question}")
        # All findings in a group share the same synthesis text; print once.
        lines.append(group[0]["synthesis"])
        for f in group:
            lines.append(f"  - [{f['source_id']}] {f['title']} ({f['source_type']})")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 3. draft
# --------------------------------------------------------------------------
async def draft_node(state: ResearchState) -> dict:
    llm = get_chat_model()
    revision_context = ""
    if state.get("human_feedback"):
        # A human's request-for-changes is the most recent, most authoritative
        # signal, so it takes priority over any earlier automated critique.
        revision_context = (
            "A human reviewer requested changes to a previous draft: "
            f"{state['human_feedback']}"
        )
    elif state.get("critique_feedback"):
        revision_context = (
            "This is a revision of a previous draft. Address this reviewer "
            f"feedback: {state['critique_feedback']}"
        )

    prompt = render_prompt(
        "draft",
        question=state["question"],
        findings_block=_findings_block(state.get("findings", [])),
        revision_context=revision_context,
    )
    response = await llm.ainvoke(prompt)
    draft_text = response.content if isinstance(response.content, str) else str(response.content)

    return {
        "draft": draft_text.strip(),
        "draft_revision": state.get("draft_revision", 0) + 1,
        "trace": _trace("draft", f"Drafted report (revision {state.get('draft_revision', 0) + 1})."),
    }


# --------------------------------------------------------------------------
# 4. critique
# --------------------------------------------------------------------------
async def critique_node(state: ResearchState) -> dict:
    llm = get_chat_model()
    prompt = render_prompt(
        "critique",
        question=state["question"],
        draft=state["draft"],
        findings_block=_findings_block(state.get("findings", [])),
    )
    response = await llm.ainvoke(prompt)
    raw = _extract_json(response.content if isinstance(response.content, str) else str(response.content))

    try:
        parsed = json.loads(raw)
        decision = str(parsed.get("decision", "approve")).lower()
        feedback = str(parsed.get("feedback", ""))
        if decision not in {"approve", "revise"}:
            decision = "approve"
    except json.JSONDecodeError:
        logger.warning("critique_node: failed to parse LLM JSON, defaulting to approve. raw=%r", raw)
        decision, feedback = "approve", "Auto-approved: could not parse reviewer output."

    revision_count = state.get("revision_count", 0)
    settings = get_settings()
    forced = False
    if decision == "revise" and revision_count >= settings.max_revision_loops:
        decision = "approve"
        feedback = (
            f"{feedback} [Auto-approved after reaching the maximum of "
            f"{settings.max_revision_loops} automated revision loops.]"
        )
        forced = True

    next_revision_count = revision_count + 1 if (decision == "revise" or forced) else revision_count

    return {
        "critique_decision": decision,
        "critique_feedback": feedback,
        "revision_count": next_revision_count,
        "trace": _trace(
            "critique",
            f"Decision={decision}" + (" (forced)" if forced else "") + f" | {feedback[:200]}",
        ),
    }


def route_after_critique(state: ResearchState) -> str:
    """Conditional edge: loop back to research on 'revise', else proceed to
    human_review. This bounded cycle (critique -> research -> draft ->
    critique) is the centerpiece feature this repo demonstrates."""
    if state.get("critique_decision") == "revise":
        return "research"
    return "human_review"


# --------------------------------------------------------------------------
# 5. human_review
# --------------------------------------------------------------------------
async def human_review_node(state: ResearchState) -> dict:
    """Pause the graph and wait for a human decision.

    `interrupt()` raises a `GraphInterrupt` the first time this node runs
    for a given task; LangGraph's Postgres checkpointer persists state up to
    (but not including) this node's completion, so the process can exit
    entirely and be resumed later via `Command(resume=...)` against the
    same `thread_id` -- see `app/api/routers/runs.py::resume_run`.
    """
    decision_payload = interrupt(
        {
            "question": state["question"],
            "draft": state["draft"],
            "critique_feedback": state.get("critique_feedback", ""),
            "sub_questions": state.get("sub_questions", []),
        }
    )
    decision = str(decision_payload.get("decision", "approve")).lower()
    feedback = str(decision_payload.get("feedback", ""))
    if decision not in {"approve", "revise", "reject"}:
        decision = "approve"

    human_revision_count = state.get("human_revision_count", 0)
    if decision == "revise":
        human_revision_count += 1

    return {
        "human_decision": decision,
        "human_feedback": feedback,
        "human_revision_count": human_revision_count,
        "trace": _trace("human_review", f"Human decision={decision} | {feedback[:200]}"),
    }


def route_after_human_review(state: ResearchState) -> str:
    """Conditional edge: human can approve (-> finalize), request changes
    (-> back to research, bounded), or reject (-> finalize, marked rejected).
    """
    settings = get_settings()
    decision = state.get("human_decision")
    if decision == "revise":
        if state.get("human_revision_count", 0) < settings.max_human_revision_loops:
            return "research"
        return "finalize"  # bounded: force finalize after too many human revisions
    return "finalize"  # approve or reject both proceed to finalize


# --------------------------------------------------------------------------
# 6. finalize
# --------------------------------------------------------------------------
async def finalize_node(state: ResearchState) -> dict:
    human_decision = state.get("human_decision", "approve")

    if human_decision == "reject":
        final_report = (
            f"# Research Report: {state['question']}\n\n"
            "_This run was reviewed and **rejected** by a human reviewer._\n\n"
            f"**Reviewer feedback:** {state.get('human_feedback') or '(none provided)'}\n\n"
            "---\n\n## Last Draft (rejected)\n\n" + state.get("draft", "")
        )
        status = "rejected"
    else:
        sources_section = "\n".join(
            f"- **[{f['source_id']}]** {f['title']} "
            f"({'Knowledge Base' if f['source_type'] == 'kb' else 'Web'}: {f['url_or_doc_id']})"
            for f in _dedupe_findings(state.get("findings", []))
        )
        final_report = (
            state.get("draft", "")
            + "\n\n---\n\n## Sources\n\n"
            + (sources_section or "_No sources recorded._")
        )
        status = "completed"

    return {
        "final_report": final_report,
        "status": status,
        "trace": _trace("finalize", f"Run finalized with status={status}."),
    }


def _dedupe_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[str] = set()
    deduped: list[Finding] = []
    for f in findings:
        if f["source_id"] in seen:
            continue
        seen.add(f["source_id"])
        deduped.append(f)
    return deduped
