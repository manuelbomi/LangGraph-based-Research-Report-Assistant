"""Embedded vector-store knowledge-base tool, backed by Milvus Lite.

Milvus Lite (`pymilvus[milvus_lite]`) runs the vector database in-process
against a local file -- no Docker, no server, no network hop. This is a
deliberate simplification for the tutorial; see the README section
"Docker / infra" for notes on swapping to full Milvus server mode for
production/multi-process/larger-scale use.

IMPORTANT (platform note): Milvus Lite's native binary is published for
Linux and macOS only. It works out of the box inside this repo's Linux
backend Docker image / CI, but will fail to import on native Windows
Python -- run the backend via Docker or WSL on Windows. See README.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.llm import get_embeddings
from app.tools.kb_documents import KB_DOCUMENTS

logger = logging.getLogger(__name__)

_client_lock = threading.Lock()
_client = None  # lazily-created MilvusClient singleton


@dataclass
class KBResult:
    doc_id: str
    title: str
    snippet: str
    score: float


def _get_client():
    """Lazily create (and cache) the Milvus Lite client.

    Lazy + cached so importing this module never requires milvus_lite to be
    installed (unit tests mock this module out entirely / never call this),
    and so the file-backed client is opened at most once per process.
    """
    global _client
    with _client_lock:
        if _client is None:
            from pymilvus import MilvusClient

            settings = get_settings()
            db_path = Path(settings.milvus_lite_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            _client = MilvusClient(str(db_path))
        return _client


def ensure_collection(dim: int = 1536) -> None:
    """Create the KB collection if it doesn't already exist."""
    settings = get_settings()
    client = _get_client()
    if not client.has_collection(settings.milvus_collection):
        client.create_collection(
            collection_name=settings.milvus_collection,
            dimension=dim,
            metric_type="COSINE",
            auto_id=False,
        )


def seed_knowledge_base(force: bool = False) -> int:
    """Embed and upsert the fixed demo corpus into Milvus Lite.

    Returns the number of documents (re)inserted. No-op if the collection
    already has data, unless `force=True`.
    """
    settings = get_settings()
    client = _get_client()

    if client.has_collection(settings.milvus_collection) and not force:
        stats = client.get_collection_stats(settings.milvus_collection)
        if int(stats.get("row_count", 0)) > 0:
            logger.info("Knowledge base already seeded (%s rows); skipping.", stats["row_count"])
            return 0

    embeddings = get_embeddings()
    texts = [f"{d.title}\n{d.text}" for d in KB_DOCUMENTS]
    vectors = embeddings.embed_documents(texts)

    ensure_collection(dim=len(vectors[0]))

    rows = [
        {
            "id": idx,
            "vector": vector,
            "doc_id": doc.doc_id,
            "title": doc.title,
            "text": doc.text,
        }
        for idx, (doc, vector) in enumerate(zip(KB_DOCUMENTS, vectors, strict=True))
    ]
    client.insert(collection_name=settings.milvus_collection, data=rows)
    logger.info("Seeded %d documents into Milvus Lite knowledge base.", len(rows))
    return len(rows)


def search_kb(query: str, top_k: int | None = None) -> list[KBResult]:
    """Embed `query` and return the top-k most similar KB documents.

    Returns [] on any failure (e.g. collection not yet seeded, or -- on
    native Windows -- milvus_lite not being installed at all) so the graph
    degrades gracefully to web search instead of crashing.
    """
    settings = get_settings()
    k = top_k or settings.kb_search_top_k
    try:
        client = _get_client()
        if not client.has_collection(settings.milvus_collection):
            logger.warning("KB collection does not exist yet; returning no results.")
            return []

        embeddings = get_embeddings()
        query_vector = embeddings.embed_query(query)

        hits = client.search(
            collection_name=settings.milvus_collection,
            data=[query_vector],
            limit=k,
            output_fields=["doc_id", "title", "text"],
        )
        results: list[KBResult] = []
        for hit in hits[0]:
            entity = hit.get("entity", hit)
            results.append(
                KBResult(
                    doc_id=entity.get("doc_id", ""),
                    title=entity.get("title", ""),
                    snippet=entity.get("text", ""),
                    score=float(hit.get("distance", 0.0)),
                )
            )
        return results
    except Exception:  # noqa: BLE001 - deliberate, see docstring
        logger.exception("knowledge base search failed for query=%r", query)
        return []


# Keyword heuristic used by the research node to decide, per sub-question,
# whether the fixed demo knowledge base (renewable energy) is likely to be
# relevant. This is real, inspectable decision logic (not a stub) -- see
# `app/graph/nodes.py::should_consult_kb`.
KB_TOPIC_KEYWORDS: list[str] = [
    "renewable", "solar", "wind", "hydro", "hydropower", "geothermal",
    "biomass", "bioenergy", "tidal", "wave energy", "photovoltaic", "pv",
    "turbine", "battery storage", "energy storage", "grid", "fossil fuel",
    "carbon", "emissions", "feed-in tariff", "clean energy", "green energy",
    "sustainable energy", "energy policy",
]
