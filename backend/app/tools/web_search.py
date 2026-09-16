"""Free, no-API-key web search tool backed by DuckDuckGo (via `ddgs`).

`ddgs` is the current maintained package name for what used to ship as
`duckduckgo-search` (that PyPI name is now a thin deprecated shim pointing
at `ddgs`).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class WebResult:
    title: str
    url: str
    snippet: str


def search_web(query: str, max_results: int | None = None) -> list[WebResult]:
    """Run a DuckDuckGo text search. Returns [] on any failure (network,
    rate limiting, etc.) rather than raising -- research should degrade
    gracefully to whatever the knowledge base found instead of crashing
    the whole graph run.
    """
    settings = get_settings()
    n = max_results or settings.web_search_max_results
    try:
        from ddgs import DDGS

        results: list[WebResult] = []
        with DDGS() as ddgs:
            for hit in ddgs.text(query, max_results=n):
                results.append(
                    WebResult(
                        title=hit.get("title", ""),
                        url=hit.get("href", hit.get("link", "")),
                        snippet=hit.get("body", hit.get("snippet", "")),
                    )
                )
        return results
    except Exception:  # noqa: BLE001 - deliberate, see docstring
        logger.exception("web_search failed for query=%r", query)
        return []
