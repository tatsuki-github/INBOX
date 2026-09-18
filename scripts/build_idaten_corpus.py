#!/usr/bin/env python3
"""Build the single-folder いだてん岱明 corpus and Node BM25 RAG index.

Writes:
  - input/idaten-corpus/   (text-only allowlist copies)
  - backend/data/rag_index.json
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "input" / "idaten-corpus"
INDEX_PATH = ROOT / "backend" / "data" / "rag_index.json"
EXTERNAL = ROOT / "input" / "external"
ARAGYOKU = ROOT / "input" / "aragyoku"

DAIMING_TAGS = frozenset({"practice:daiming", "いだてん岱明練習", "岱明中"})
DAIMING_TITLE_HINTS = ("いだてん岱明", "岱明中", "岱明")

NOTION_DBS = (
    "いだてん岱明生徒",
    "いだてん岱明の未来",
    "荒玉中体連駅伝歴代",
    "荒玉中体連駅伝戦略",
    "練習のバリエーション",
    "動きづくり",
    "怪我について",
)

DRIVE_TEXT_DIRS = ("名簿", "練習", "記録データベース", "大会")

ARAGYOKU_FILES = (
    "taimei-records-2012-2025.md",
    "men_full_2012_2025.json",
    "women_full_2012_2025.json",
    "women_top6_2012_2025.json",
    "women_top4_2012_2025.json",
    "course-videos.md",
)

DOC_FILES = (
    ROOT / "docs" / "adr" / "010-external-idaten-import.md",
    ROOT / "docs" / "adr" / "011-idaten-media-ocr-kg.md",
    ROOT / "docs" / "adr" / "015-line-idaten-qa-backend.md",
    ROOT / "docs" / "adr" / "016-kg-first-idaten-qa.md",
    ROOT / "docs" / "aragyoku-ekiden-distance-definitions.md",
    ROOT / "docs" / "data-model.md",
    ROOT / "docs" / "ai-practice-generation.md",
    ROOT / "README.md",
    ROOT / "AGENTS.md",
)

MAX_CHUNK_CHARS = 900
TEXT_SUFFIXES = {".md", ".txt", ".csv", ".json", ".yaml", ".yml"}


def _reset_corpus() -> None:
    if CORPUS_DIR.exists():
        shutil.rmtree(CORPUS_DIR)
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)


def _copy_file(src: Path, dest: Path, sources: list[dict[str, str]]) -> None:
    if not src.is_file():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    sources.append(
        {
            "source": str(src.relative_to(ROOT)),
            "corpus": str(dest.relative_to(CORPUS_DIR)),
        }
    )


def _copy_tree_text(
    src_dir: Path,
    dest_dir: Path,
    sources: list[dict[str, str]],
    *,
    name_filter: re.Pattern[str] | None = None,
) -> None:
    if not src_dir.is_dir():
        return
    for path in sorted(src_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if name_filter and not name_filter.search(path.name):
            continue
        rel = path.relative_to(src_dir)
        _copy_file(path, dest_dir / rel, sources)


def _event_is_daiming(ev: dict[str, Any]) -> bool:
    tags = {str(t) for t in (ev.get("tags") or [])}
    if tags & DAIMING_TAGS:
        return True
    title = str(ev.get("title") or "")
    return any(h in title for h in DAIMING_TITLE_HINTS)


def _extract_calendar(sources: list[dict[str, str]]) -> None:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("PyYAML required") from exc

    out_events: list[dict[str, Any]] = []
    for year in (2025, 2026):
        path = ROOT / "input" / f"events.{year}.yaml"
        if not path.exists():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for ev in data.get("events") or []:
            if isinstance(ev, dict) and _event_is_daiming(ev):
                out_events.append(ev)
        sources.append(
            {
                "source": str(path.relative_to(ROOT)),
                "corpus": f"calendar/events.{year}.filtered.yaml",
                "note": "daiming-filtered",
            }
        )
    dest = CORPUS_DIR / "calendar" / "events.daiming.yaml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as fh:
        import yaml

        yaml.safe_dump(
            {"events": out_events, "filter": "daiming"},
            fh,
            allow_unicode=True,
            sort_keys=False,
        )


def _extract_practice(sources: list[dict[str, str]]) -> None:
    practice_dir = CORPUS_DIR / "practice"
    practice_dir.mkdir(parents=True, exist_ok=True)
    for year in (2025, 2026):
        path = ROOT / "out" / str(year) / "practice.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("events") or data.get("practices") or []
        filtered: list[Any] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            blob = json.dumps(item, ensure_ascii=False)
            tags = {str(t) for t in (item.get("tags") or [])}
            title = str(item.get("title") or item.get("name") or "")
            if tags & DAIMING_TAGS or any(h in title for h in DAIMING_TITLE_HINTS) or "岱明" in blob:
                filtered.append(item)
        dest = practice_dir / f"practice.{year}.json"
        dest.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")
        sources.append(
            {
                "source": str(path.relative_to(ROOT)),
                "corpus": str(dest.relative_to(CORPUS_DIR)),
                "note": f"filtered {len(filtered)} items",
            }
        )
    menus = ROOT / "out" / "daiming-practice-menus-kpace.md"
    if menus.exists():
        _copy_file(menus, practice_dir / menus.name, sources)


def _extract_sb(sources: list[dict[str, str]]) -> None:
    sb_src = EXTERNAL / "sb" / "middle-school" / "wide" / "中学生SB.csv"
    if not sb_src.exists():
        return
    lines = sb_src.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return
    header = lines[0]
    kept = [header]
    for line in lines[1:]:
        if "岱明" in line:
            kept.append(line)
    dest = CORPUS_DIR / "sb" / "中学生SB_岱明.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(kept) + "\n", encoding="utf-8")
    sources.append(
        {
            "source": str(sb_src.relative_to(ROOT)),
            "corpus": str(dest.relative_to(CORPUS_DIR)),
            "note": f"filtered {len(kept) - 1} rows",
        }
    )


def _build_corpus() -> list[dict[str, str]]:
    _reset_corpus()
    sources: list[dict[str, str]] = []

    _copy_tree_text(
        EXTERNAL / "notion" / "media" / "ekiden-history" / "ocr",
        CORPUS_DIR / "ekiden-ocr",
        sources,
    )
    _copy_tree_text(
        EXTERNAL / "drive" / "shared" / "分析",
        CORPUS_DIR / "analysis-ocr",
        sources,
        name_filter=re.compile(r"\.ocr\.md$", re.I),
    )

    aragyoku_dest = CORPUS_DIR / "aragyoku"
    for name in ARAGYOKU_FILES:
        _copy_file(ARAGYOKU / name, aragyoku_dest / name, sources)
    _copy_tree_text(ARAGYOKU / "transcripts", aragyoku_dest / "transcripts", sources)
    if (ARAGYOKU / "ocr_raw").is_dir():
        _copy_tree_text(ARAGYOKU / "ocr_raw", aragyoku_dest / "ocr_raw", sources)
    if (ARAGYOKU / "quiz").is_dir():
        _copy_tree_text(ARAGYOKU / "quiz", aragyoku_dest / "quiz", sources)
    _write_aragyoku_winners(sources)

    # Repo-wide text: analysis outputs + remaining docs under docs/
    analysis_src = ROOT / "out" / "analysis"
    if analysis_src.is_dir():
        _copy_tree_text(
            analysis_src,
            CORPUS_DIR / "out-analysis",
            sources,
            name_filter=re.compile(r"\.(md|json)$", re.I),
        )
    docs_root = ROOT / "docs"
    if docs_root.is_dir():
        for path in sorted(docs_root.rglob("*.md")):
            rel = path.relative_to(docs_root)
            # Skip already-copied top-level names into docs/
            if path in DOC_FILES:
                continue
            _copy_file(path, CORPUS_DIR / "repo-docs" / rel, sources)

    for db in NOTION_DBS:
        src = EXTERNAL / "notion" / "databases" / db
        if src.is_dir():
            _copy_tree_text(src, CORPUS_DIR / "notion-db" / db, sources)

    pages = EXTERNAL / "notion" / "pages"
    if pages.is_dir():
        for path in sorted(pages.rglob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            if any(k in text or k in str(path) for k in ("岱明", "いだてん", "荒玉", "駅伝")):
                rel = path.relative_to(pages)
                _copy_file(path, CORPUS_DIR / "notion-pages" / rel, sources)

    for folder in DRIVE_TEXT_DIRS:
        _copy_tree_text(
            EXTERNAL / "drive" / "shared" / folder,
            CORPUS_DIR / "drive-text" / folder,
            sources,
        )

    personal = EXTERNAL / "drive" / "personal"
    if personal.is_dir():
        for path in sorted(personal.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            if any(k in text or k in path.name for k in ("岱明", "いだてん", "荒玉")):
                _copy_file(path, CORPUS_DIR / "drive-text" / "personal" / path.name, sources)

    _extract_calendar(sources)
    _extract_practice(sources)
    _extract_sb(sources)

    docs_dest = CORPUS_DIR / "docs"
    for path in DOC_FILES:
        if path.exists():
            _copy_file(path, docs_dest / path.name, sources)

    # Manifest pointer (text only)
    manifest = EXTERNAL / "media-manifest.json"
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("items") or data.get("media") or []
        slim = []
        for item in items:
            if not isinstance(item, dict):
                continue
            topic = str(item.get("topic") or "")
            if topic in {"ekiden", "analysis"}:
                slim.append(
                    {
                        k: item.get(k)
                        for k in ("id", "title", "topic", "ocr", "path", "binary_saved")
                        if k in item
                    }
                )
        dest = CORPUS_DIR / "media-manifest.slim.json"
        dest.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
        sources.append(
            {
                "source": str(manifest.relative_to(ROOT)),
                "corpus": str(dest.relative_to(CORPUS_DIR)),
                "note": f"ekiden+analysis {len(slim)} items",
            }
        )

    index_md = CORPUS_DIR / "INDEX.md"
    index_md.write_text(
        "\n".join(
            [
                "# リポジトリ知識コーパス（単一フォルダ）",
                "",
                "LINE Q&A バックエンドが参照するテキスト専用コーパス（いだてん岱明＋荒玉＋分析＋docs）。",
                "バイナリ（画像・PDF）は含めない。再生成: `python3 scripts/build_idaten_corpus.py`",
                "",
                "## ディレクトリ",
                "",
                "- `ekiden-ocr/` — 荒玉駅伝歴代 OCR",
                "- `analysis-ocr/` — 分析 PDF の OCR",
                "- `aragyoku/` — 荒玉構造化テキスト・優勝校要約・transcripts",
                "- `out-analysis/` — `out/analysis` の md/json",
                "- `repo-docs/` — docs 配下の Markdown",
                "- `notion-db/` / `notion-pages/` — Notion スナップショット",
                "- `drive-text/` — Drive テキスト",
                "- `calendar/` / `practice/` / `sb/` — 岱明フィルタ済み予定・練習・SB",
                "- `docs/` — 関連 ADR・定義（抜粋）",
                "",
                f"ファイル数（SOURCES）: {len(sources)}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (CORPUS_DIR / "SOURCES.md").write_text(
        "# Sources\n\n"
        + "\n".join(
            f"- `{s['source']}` → `{s['corpus']}`"
            + (f" ({s['note']})" if s.get("note") else "")
            for s in sources
        )
        + "\n",
        encoding="utf-8",
    )
    (CORPUS_DIR / "sources.json").write_text(
        json.dumps(sources, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return sources


def _write_aragyoku_winners(sources: list[dict[str, str]]) -> None:
    """Derive a BM25-friendly winners table from transcripts (rank=1)."""
    transcripts = ARAGYOKU / "transcripts"
    if not transcripts.is_dir():
        return
    lines = [
        "# 荒玉駅伝 年度別優勝校",
        "",
        "文字起こし（`input/aragyoku/transcripts/*.json`）の teams[rank=1] に基づく要約。",
        "「去年の優勝校」など相対年の質問では、質問時点の西暦とこの表の年度を対応づける。",
        "",
        "| 年度 | 性別 | 優勝校 | 総合タイム |",
        "| --- | --- | --- | --- |",
    ]
    for path in sorted(transcripts.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        year = data.get("year")
        gender = data.get("gender")
        teams = data.get("teams") or []
        winner = next(
            (t for t in teams if isinstance(t, dict) and t.get("rank") in (1, "1")),
            None,
        )
        if not winner:
            continue
        team = winner.get("team") or "?"
        total = winner.get("total") or ""
        lines.append(f"| {year} | {gender} | {team} | {total} |")
        # Plain-language line for BM25 (テーブル記号に依存しない)
        lines.append(
            f"{year}年荒玉駅伝{gender}の優勝校は「{team}」である（総合 {total}）。1位 {team}。"
        )
    if len(lines) <= 7:
        return
    dest = CORPUS_DIR / "aragyoku" / "winners-by-year.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sources.append(
        {
            "source": "input/aragyoku/transcripts (derived)",
            "corpus": str(dest.relative_to(CORPUS_DIR)),
            "note": "winners summary from rank=1",
        }
    )


def _chunk_aragyoku_transcript(path: Path, rel: str) -> list[dict[str, Any]]:
    """One summary + per-team chunks so year/winner stay co-located."""
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    year = data.get("year")
    gender = data.get("gender")
    teams = [t for t in (data.get("teams") or []) if isinstance(t, dict)]
    out: list[dict[str, Any]] = []
    winner = next((t for t in teams if t.get("rank") in (1, "1")), None)
    summary_parts = [
        f"{year}年 荒玉中体連駅伝 {gender} 結果要約。",
    ]
    if winner:
        summary_parts.append(
            f"優勝校（1位）は「{winner.get('team')}」（総合 {winner.get('total', '')}）。"
        )
    for t in teams[:8]:
        summary_parts.append(
            f"{t.get('rank')}位 {t.get('team')} {t.get('total', '')}。"
        )
    out.append(
        {
            "id": f"{rel}:0",
            "source": rel,
            "text": " ".join(summary_parts),
            "metadata": {"path": f"input/idaten-corpus/{rel}", "index": 0, "kind": "winner_summary"},
        }
    )
    for idx, team in enumerate(teams, start=1):
        header = (
            f"{year}年荒玉駅伝{gender} "
            f"{team.get('rank')}位 {team.get('team')} 総合{team.get('total', '')}"
        )
        if team.get("rank") in (1, "1"):
            header = f"{header} 優勝校"
        body = json.dumps(team, ensure_ascii=False, indent=2)
        text = f"{header}\n{body}"
        if len(text) > MAX_CHUNK_CHARS:
            text = text[:MAX_CHUNK_CHARS]
        out.append(
            {
                "id": f"{rel}:{idx}",
                "source": rel,
                "text": text,
                "metadata": {"path": f"input/idaten-corpus/{rel}", "index": idx, "kind": "team"},
            }
        )
    return out


def _split_paragraphs(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
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


def _iter_corpus_files() -> Iterator[Path]:
    skip_names = {"SOURCES.md", "sources.json", "INDEX.md"}
    for path in sorted(CORPUS_DIR.rglob("*")):
        if not path.is_file():
            continue
        if path.name in skip_names:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield path


def _chunk_file(path: Path) -> list[dict[str, Any]]:
    rel = str(path.relative_to(CORPUS_DIR)).replace("\\", "/")
    if rel.startswith("aragyoku/transcripts/") and path.suffix.lower() == ".json":
        return _chunk_aragyoku_transcript(path, rel)
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(raw)
            raw = json.dumps(data, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
    pieces = _split_paragraphs(raw)
    out: list[dict[str, Any]] = []
    for idx, piece in enumerate(pieces):
        out.append(
            {
                "id": f"{rel}:{idx}",
                "source": rel,
                "text": piece,
                "metadata": {"path": f"input/idaten-corpus/{rel}", "index": idx},
            }
        )
    return out


def _build_index() -> dict[str, Any]:
    chunks: list[dict[str, Any]] = []
    for path in _iter_corpus_files():
        chunks.extend(_chunk_file(path))
    return {
        "version": 1,
        "corpus": "input/idaten-corpus",
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


def main() -> int:
    sources = _build_corpus()
    index = _build_index()
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    size_mb = INDEX_PATH.stat().st_size / (1024 * 1024)
    print(
        f"corpus: {CORPUS_DIR.relative_to(ROOT)} ({len(sources)} sources)\n"
        f"index:  {INDEX_PATH.relative_to(ROOT)} "
        f"({index['chunk_count']} chunks, {size_mb:.2f} MB)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
