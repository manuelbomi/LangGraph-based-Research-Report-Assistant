"""Seed version-1 prompts for the plan/research/draft/critique nodes.

Run with:
    python -m app.prompts.seed_prompts

Safe to re-run: it only inserts a new version if the active template text
for a given name has actually changed.
"""
from __future__ import annotations

from sqlalchemy import select

from app.db.models import Prompt
from app.db.session import SessionLocal
from app.prompts.registry import add_prompt_version

PROMPTS_V1: dict[str, str] = {
    "plan": (
        "You are a meticulous research planner. Given a user's research question, "
        "break it down into 2 to 4 focused, non-overlapping sub-questions that, "
        "together, would let a researcher fully answer the original question.\n\n"
        "User question: {question}\n\n"
        "{revision_context}\n\n"
        "Respond with ONLY a JSON array of strings, e.g. "
        '["sub-question 1", "sub-question 2"]. Do not include numbering, markdown, '
        "or commentary outside the JSON array."
    ),
    "research_summarize": (
        "You are a careful research analyst. You are investigating the following "
        "sub-question as part of a larger research report:\n\n"
        "Sub-question: {sub_question}\n\n"
        "Below are raw snippets retrieved from web search and/or an internal "
        "knowledge base. Each snippet has a source tag like [S3].\n\n"
        "{raw_snippets}\n\n"
        "Write a concise, factual synthesis (3-6 sentences) that answers the "
        "sub-question using ONLY the information in the snippets above. Cite the "
        'source tag(s) inline, e.g. "Solar capacity has grown rapidly since 2010 '
        '[S2][S4]." If the snippets don\'t fully answer the sub-question, say what '
        "is missing. Do not fabricate facts not present in the snippets."
    ),
    "draft": (
        "You are a professional research report writer. Write a well-structured "
        "markdown report answering the user's original question, using the "
        "synthesized findings below. Each finding already contains inline "
        "citation tags like [S1] -- preserve them in your prose.\n\n"
        "Original question: {question}\n\n"
        "Sub-questions and findings:\n{findings_block}\n\n"
        "{revision_context}\n\n"
        "Write the report with:\n"
        "- A one-paragraph executive summary\n"
        '- A "## Findings" section with a subsection per sub-question\n'
        '- A short "## Conclusion" section\n'
        "Preserve the [S#] citation tags from the findings verbatim. Do not add a "
        "sources list yourself; that is appended automatically. Respond with ONLY "
        "the markdown report body."
    ),
    "critique": (
        "You are a rigorous editorial reviewer for research reports. Compare the "
        "draft report against the original question and the underlying findings, "
        "and decide whether it is ready to publish.\n\n"
        "Original question: {question}\n\n"
        "Draft report:\n{draft}\n\n"
        "Underlying findings (for fact-checking coverage, not for style):\n"
        "{findings_block}\n\n"
        "Evaluate: Does the draft fully and accurately answer the original "
        "question? Are claims supported by the findings and cited? Is anything "
        "important missing or unclear?\n\n"
        "Respond with ONLY a JSON object of the form:\n"
        '{{"decision": "approve" or "revise", "feedback": "specific, actionable '
        "feedback for the next research pass if revise, or a brief note on why "
        'it\'s ready if approve"}}'
    ),
}


def seed() -> None:
    with SessionLocal() as db:
        for name, template in PROMPTS_V1.items():
            active = db.execute(
                select(Prompt).where(Prompt.name == name, Prompt.is_active.is_(True))
            ).scalar_one_or_none()
            if active is not None and active.template == template:
                print(f"[skip] '{name}' already has this template active (v{active.version})")
                continue
            version = add_prompt_version(name, template, activate=True)
            print(f"[seeded] '{name}' -> v{version}")


if __name__ == "__main__":
    seed()
