"""CLI entrypoint to seed the Milvus Lite knowledge base.

Run with:
    python -m app.tools.seed_kb [--force]

Requires OPENAI_API_KEY (used to embed the fixed demo corpus with
text-embedding-3-small). Only needs to be run once per `milvus_lite_path`
data file; safe to re-run (no-ops unless the collection is empty or
--force is passed).
"""
from __future__ import annotations

import argparse
import logging

from app.tools.knowledge_base import seed_knowledge_base

logging.basicConfig(level=logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="Re-embed and re-insert even if already seeded."
    )
    args = parser.parse_args()
    count = seed_knowledge_base(force=args.force)
    print(f"Inserted {count} documents into the knowledge base.")


if __name__ == "__main__":
    main()
