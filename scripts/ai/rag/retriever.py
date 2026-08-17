"""Local BM25 retrieval for practice RAG."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import RAG_INDEX_PATH
from .chunker import Chunk, build_all_chunks, chunks_to_index_dict, iter_chunks_from_index


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    return re.findall(r"[\w\d]+", text)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float


class BM25Retriever:
    def __init__(self, chunks: list[Chunk], *, k1: float = 1.5, b: float = 0.75) -> None:
        self._chunks = chunks
        self._k1 = k1
        self._b = b
        self._doc_tokens = [_tokenize(c.text) for c in chunks]
        self._doc_lens = [len(t) for t in self._doc_tokens]
        self._avgdl = sum(self._doc_lens) / max(len(self._doc_lens), 1)
        self._nd = len(chunks)
        self._df: Counter[str] = Counter()
        for tokens in self._doc_tokens:
            for term in set(tokens):
                self._df[term] += 1

    def _idf(self, term: str) -> float:
        n = self._df.get(term, 0)
        return math.log(1 + (self._nd - n + 0.5) / (n + 0.5))

    def search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        scores: list[RetrievedChunk] = []
        for idx, tokens in enumerate(self._doc_tokens):
            tf = Counter(tokens)
            dl = self._doc_lens[idx]
            score = 0.0
            for term in q_tokens:
                if term not in tf:
                    continue
                freq = tf[term]
                idf = self._idf(term)
                denom = freq + self._k1 * (1 - self._b + self._b * dl / self._avgdl)
                score += idf * (freq * (self._k1 + 1)) / denom
            if score > 0:
                scores.append(RetrievedChunk(chunk=self._chunks[idx], score=score))
        scores.sort(key=lambda r: r.score, reverse=True)
        return scores[:top_k]


def save_index(path: Path | None = None, *, years: list[int] | None = None) -> Path:
    path = path or RAG_INDEX_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    chunks = build_all_chunks(years=years)
    data = chunks_to_index_dict(chunks)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_retriever(path: Path | None = None) -> BM25Retriever:
    path = path or RAG_INDEX_PATH
    if not path.exists():
        save_index(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    chunks = list(iter_chunks_from_index(data))
    return BM25Retriever(chunks)


def retrieve_context(query: str, top_k: int = 5, path: Path | None = None) -> list[str]:
    retriever = load_retriever(path)
    return [r.chunk.text for r in retriever.search(query, top_k=top_k)]
