"""Shared test fixtures.

All tests in `tests/` (excluding `tests/live/`) are fully mocked: no real
LLM calls, no real Postgres, no real network. This keeps `pytest` free and
fast to run in CI. The real end-to-end path is exercised separately by
`tests/live/test_live_smoke.py`, which is excluded by default (see the
`live` marker in `pyproject.toml`) and requires a real `OPENAI_API_KEY`
plus a reachable Postgres.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-dummy-key")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")


@dataclass
class _FakeAIMessage:
    content: str


class FakeChatModel:
    """Stand-in for a LangChain chat model.

    Construct with a list of canned response strings; each call to
    `ainvoke` pops the next one (regardless of prompt content). Raises
    `AssertionError` if called more times than responses were queued, so
    tests fail loudly instead of hanging on `None`.
    """

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[str] = []

    async def ainvoke(self, prompt: str, *args: Any, **kwargs: Any) -> _FakeAIMessage:
        self.calls.append(prompt)
        if not self._responses:
            raise AssertionError("FakeChatModel called more times than responses were queued")
        return _FakeAIMessage(content=self._responses.pop(0))


@pytest.fixture
def fake_chat_model(monkeypatch):
    """Patch `app.graph.nodes.get_chat_model` to return a FakeChatModel.

    Returns a factory: `make(responses=[...])` -> the FakeChatModel instance,
    so each test controls exactly what the "LLM" says at each graph step.
    """
    holder: dict[str, FakeChatModel] = {}

    def make(responses: list[str]) -> FakeChatModel:
        model = FakeChatModel(responses)
        holder["model"] = model
        return model

    def fake_get_chat_model(*args: Any, **kwargs: Any) -> FakeChatModel:
        return holder["model"]

    monkeypatch.setattr("app.graph.nodes.get_chat_model", fake_get_chat_model)
    return make


@pytest.fixture
def fake_prompts(monkeypatch):
    """Patch `app.graph.nodes.render_prompt` to a template-free passthrough.

    Node logic is what's under test here, not prompt wording (that's
    covered by the real templates in `app/prompts/seed_prompts.py`, which
    `scripts/seed_examples.py`'s live counterpart exercises against a real
    LLM). This just avoids requiring a Postgres-backed prompt registry in
    unit tests.
    """

    def fake_render_prompt(name: str, **kwargs: Any) -> str:
        return f"[[{name}]] {kwargs}"

    monkeypatch.setattr("app.graph.nodes.render_prompt", fake_render_prompt)
