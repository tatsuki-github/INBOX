"""RAG chunking for Norwegian Method and practice history."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import yaml

from ..config import INPUT_DIR, ROOT


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source: str
    text: str
    metadata: dict[str, Any]


def _split_paragraphs(text: str, max_chars: int = 800) -> list[str]:
    parts = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    buf = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(buf) + len(part) + 2 <= max_chars:
            buf = f"{buf}\n\n{part}".strip()
        else:
            if buf:
                chunks.append(buf)
            if len(part) <= max_chars:
                buf = part
            else:
                for i in range(0, len(part), max_chars):
                    chunks.append(part[i : i + max_chars])
                buf = ""
    if buf:
        chunks.append(buf)
    return chunks


def chunk_text_file(path: Path, source: str, *, max_chars: int = 800) -> list[Chunk]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    chunks: list[Chunk] = []
    for idx, piece in enumerate(_split_paragraphs(text, max_chars=max_chars)):
        chunks.append(
            Chunk(
                chunk_id=f"{source}:{idx}",
                source=source,
                text=piece,
                metadata={"path": str(path), "index": idx},
            )
        )
    return chunks


def chunk_events_yaml(path: Path, source: str) -> list[Chunk]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    chunks: list[Chunk] = []
    for idx, ev in enumerate(data.get("events") or []):
        practice = ev.get("practice")
        if not practice:
            continue
        title = ev.get("title", "?")
        date = ev.get("date", "")
        text = f"{title} ({date})\n{yaml.dump(practice, allow_unicode=True)}"
        chunks.append(
            Chunk(
                chunk_id=f"{source}:{idx}",
                source=source,
                text=text,
                metadata={"title": title, "date": date},
            )
        )
    return chunks


def chunk_templates(path: Path) -> list[Chunk]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    chunks: list[Chunk] = []
    for tpl in data.get("templates") or []:
        tid = tpl.get("id", "?")
        label = tpl.get("label", tid)
        text = f"{tid}: {label}\n{yaml.dump(tpl.get('practice') or {}, allow_unicode=True)}"
        chunks.append(
            Chunk(
                chunk_id=f"template:{tid}",
                source="practice_templates",
                text=text,
                metadata={"template_id": tid, "label": label},
            )
        )
    return chunks


def build_all_chunks(*, years: list[int] | None = None) -> list[Chunk]:
    years = years or [2025, 2026, 2027]
    chunks: list[Chunk] = []
    chunks.extend(
        chunk_text_file(
            INPUT_DIR / "memos" / "norwegian_method_applied_full.txt",
            "norwegian_full",
        )
    )
    summary = ROOT / "tmp" / "norwegian_method_summary.md"
    chunks.extend(chunk_text_file(summary, "norwegian_summary", max_chars=1200))
    chunks.extend(chunk_templates(INPUT_DIR / "practice_templates.yaml"))
    for year in years:
        chunks.extend(chunk_events_yaml(INPUT_DIR / f"events.{year}.yaml", f"events_{year}"))
    return chunks


def chunks_to_index_dict(chunks: list[Chunk]) -> dict[str, Any]:
    return {
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "source": c.source,
                "text": c.text,
                "metadata": c.metadata,
            }
            for c in chunks
        ]
    }


def iter_chunks_from_index(data: dict[str, Any]) -> Iterator[Chunk]:
    for item in data.get("chunks") or []:
        yield Chunk(
            chunk_id=item["chunk_id"],
            source=item["source"],
            text=item["text"],
            metadata=item.get("metadata") or {},
        )
