"""SQLAlchemy models for the `prompts` registry and `runs` history tables.

Note: LangGraph's `AsyncPostgresSaver` manages its own checkpoint tables
(`checkpoints`, `checkpoint_writes`, ...) via `checkpointer.setup()` -- those
are NOT modeled here and are intentionally left out of Alembic's autogenerate
scope (see `db/migrations/env.py`).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Prompt(Base):
    """A versioned prompt template.

    Only one version per `name` is `is_active` at a time; `get_prompt(name)`
    (see `app/prompts/registry.py`) resolves to that active version.
    """

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Prompt name={self.name!r} v{self.version} active={self.is_active}>"


class Run(Base):
    """One end-to-end research run, keyed by the LangGraph `thread_id`.

    `trace` is an append-only JSON array of `{node, timestamp, summary}`
    events written as the graph executes, powering the "step-by-step trace"
    view in the Run History / Example Analyses UI without needing to
    re-inspect LangGraph checkpoints.
    """

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    # pending | running | awaiting_human | revising | completed | rejected | error
    final_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Run id={self.id} status={self.status!r}>"
