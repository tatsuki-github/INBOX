"""Build and persist RAG index."""

from __future__ import annotations

from ..config import RAG_INDEX_PATH
from .chunker import build_all_chunks, chunks_to_index_dict


def build_index(*, years: list[int] | None = None) -> dict:
    chunks = build_all_chunks(years=years)
    return chunks_to_index_dict(chunks)


def write_index(path=None, *, years: list[int] | None = None):
    from pathlib import Path

    path = Path(path) if path else RAG_INDEX_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    data = build_index(years=years)
    import json

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
