"""Tests for RAG retrieval."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.rag.chunker import build_all_chunks
from ai.rag.retriever import BM25Retriever, save_index


def test_build_all_chunks_non_empty():
    chunks = build_all_chunks(years=[2026])
    assert len(chunks) > 10


def test_bm25_finds_golden_zone_content():
    chunks = build_all_chunks(years=[2026])
    retriever = BM25Retriever(chunks)
    results = retriever.search("Golden Zone threshold GZ", top_k=3)
    assert results
    joined = " ".join(r.chunk.text.lower() for r in results)
    assert "golden" in joined or "gz" in joined or "閾値" in joined or "threshold" in joined


def test_save_index_writes_file(tmp_path):
    from ai.config import RAG_INDEX_PATH

    target = tmp_path / "rag_index.json"
    path = save_index(target, years=[2026])
    assert path.exists()
    data = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert len(data.get("chunks", [])) > 0
