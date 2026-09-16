"""Centralized application settings.

All configuration is read from environment variables (see `.env.example` at the
repo root). We use `pydantic-settings` so misconfiguration fails fast and
loudly at process startup instead of deep inside a graph node.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM provider ---------------------------------------------------
    llm_provider: str = "openai"  # "openai" | "anthropic"
    llm_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-haiku-latest"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    llm_temperature: float = 0.2

    # --- Postgres (runs, prompts, LangGraph checkpoints) -----------------
    # SQLAlchemy (sync engine) uses the psycopg3 dialect: postgresql+psycopg://
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/research_assistant"
    )
    # AsyncPostgresSaver needs a plain psycopg-style DSN (no "+psycopg" driver
    # suffix); we strip it in db/checkpointer.py.

    # --- Milvus Lite (embedded vector store, no server/docker needed) ---
    milvus_lite_path: str = "./data/milvus_kb.db"
    milvus_collection: str = "kb_documents"

    # --- Graph behaviour ---------------------------------------------------
    max_revision_loops: int = 2  # critique -> research loop bound
    max_human_revision_loops: int = 2  # human_review -> research loop bound
    web_search_max_results: int = 3
    kb_search_top_k: int = 3

    # --- API ---------------------------------------------------------------
    cors_allow_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
