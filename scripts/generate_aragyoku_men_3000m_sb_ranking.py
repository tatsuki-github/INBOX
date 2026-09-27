#!/usr/bin/env python3
"""荒玉地区 男子3000m SBランキング Markdown を再生成する。

正本: `load_sb_index`（採用SB・ナイター含む）から、荒尾・玉名地区の所属のみ抽出。
所属スコープは従来どおり notion_records_2026 の男子3000mに出た所属
（金栗PROJECT / ATRC / 玉名アスリーツ / 南関中 / 岱明中 / 玉名中 / 玉名附中）。

Outputs:
  out/analysis/2026_aragyoku_men_3000m_sb_ranking.md
  input/idaten-corpus/out-analysis/2026_aragyoku_men_3000m_sb_ranking.md

再生成後: `python3 scripts/build_idaten_corpus.py` で RAG に載せる。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_aragyoku_ekiden_sb_preview as aragyoku  # noqa: E402
import generate_nagomi_order_sb_preview as nagomi  # noqa: E402

OUT = ROOT / "out" / "analysis" / "2026_aragyoku_men_3000m_sb_ranking.md"
CORPUS_OUT = (
    ROOT / "input" / "idaten-corpus" / "out-analysis" / "2026_aragyoku_men_3000m_sb_ranking.md"
)
NOTION = ROOT / "out" / "analysis" / "notion_records_2026.json"
AS_OF = "2026-09-27"
FRESHNESS_DAYS = 365


def region_affiliations() -> set[str]:
    """従来ランキングと同じ地区所属セット。"""
    rows = json.loads(NOTION.read_text(encoding="utf-8"))
    return {
        str(r.get("affiliation") or "").strip()
        for r in rows
        if r.get("gender") == "男子"
        and r.get("distance") == "3000m"
        and str(r.get("affiliation") or "").strip()
    }


def fmt_date(raw: str) -> str:
    text = (raw or "").strip().replace("-", "/")
    return text


def build_rows() -> list[tuple[float, str, str, str, str]]:
    allowed = region_affiliations()
    aff_by_name = aragyoku.load_name_affiliations()
    idx, _ = nagomi.load_sb_index(
        as_of=AS_OF, gender="男子", freshness_days=FRESHNESS_DAYS
    )
    best: dict[str, tuple[float, str, str, str, str]] = {}
    for key, ath in idx.items():
        mark = ath.marks.get("3000m")
        if mark is None:
            continue
        affiliation = (aff_by_name.get(key) or "").strip()
        if affiliation not in allowed:
            continue
        sec = float(mark.seconds)
        prev = best.get(key)
        if prev is None or sec < prev[0]:
            best[key] = (
                sec,
                ath.name,
                affiliation,
                mark.text,
                fmt_date(str(mark.date or "")),
            )
    return sorted(best.values(), key=lambda x: (x[0], nagomi.norm_name(x[1])))


def render(rows: list[tuple[float, str, str, str, str]]) -> str:
    lines = [
        "# 荒玉地区 男子3000m SBランキング（2026年度登録ベース）",
        "",
        "出典: `load_sb_index` 採用SB（Notion / 中学生SB / ナイター等）。",
        f"所属スコープ: `notion_records_2026.json` の荒尾・玉名地区（as_of={AS_OF}, freshness={FRESHNESS_DAYS}日）。",
        "同一選手は最速記録のみ。",
        "",
        "| 順位 | 選手 | 所属 | 記録 | 日付 |",
        "|---:|---|---|---:|---|",
    ]
    for i, (_sec, name, affiliation, text, date) in enumerate(rows, 1):
        lines.append(f"| {i} | {name} | {affiliation} | {text} | {date} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    rows = build_rows()
    if not rows:
        print("no rows", file=sys.stderr)
        return 1
    text = render(rows)
    for path in (OUT, CORPUS_OUT):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path} ({len(rows)} athletes, #1 {rows[0][1]} {rows[0][3]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
