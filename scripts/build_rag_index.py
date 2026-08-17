#!/usr/bin/env python3
"""Build local RAG index for AI practice generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ai.rag.retriever import save_index  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, nargs="*", default=[2025, 2026, 2027])
    args = parser.parse_args(argv)
    path = save_index(years=args.years)
    print(f"Wrote RAG index: {path}")
    chunk_count = len(__import__("json").loads(path.read_text(encoding="utf-8")).get("chunks", []))
    print(f"Chunks: {chunk_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
