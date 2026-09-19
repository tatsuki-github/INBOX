#!/usr/bin/env python3
"""荒玉ボード上部の大会／区間記録を検索用 Markdown に展開する。

正本: input/aragyoku/transcripts/*/meet_records
出力: out/analysis/aragyoku_meet_records.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTS = ROOT / "input" / "aragyoku" / "transcripts"
OUT = ROOT / "out" / "analysis" / "aragyoku_meet_records.md"


def holders_text(holders: list[Any]) -> str:
    parts: list[str] = []
    for h in holders:
        if not isinstance(h, dict):
            continue
        name = str(h.get("name") or "").strip() or "?"
        school = str(h.get("school") or "").strip()
        years = ",".join(str(y) for y in (h.get("year_labels") or []))
        bit = name
        if school:
            bit += f"（{school}）"
        if years:
            bit += f"/{years}"
        parts.append(bit)
    return "、".join(parts) if parts else "—"


def build() -> str:
    lines = [
        "# 荒玉駅伝 大会記録・区間記録（ボード上部）",
        "",
        "結果ボード上部に印刷された **総合大会記録** と **各区間の大会区間記録**。",
        "正本は各年 transcript の `meet_records`（ADR 033）。",
        "",
        "## Q&A の使い方",
        "",
        "- 「○年の大会記録（総合）は？」「男子2区の大会区間記録は誰？」→ **この文書を優先**。",
        "- 当日の区間新フラグは各チーム結果の `split_record`（別概念）。",
        "- 男子は2024年以降でコース再編（`course_era`）があり、記録がリセットされる。",
        "",
    ]
    paths = sorted(TRANSCRIPTS.glob("*.json"))
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        mr = data.get("meet_records")
        if not isinstance(mr, dict):
            continue
        year = data.get("year")
        gender = data.get("gender")
        era = mr.get("course_era") or data.get("course_era") or "—"
        total = mr.get("total") or {}
        t_time = total.get("time") or "—"
        t_school = total.get("school") or "—"
        t_name = total.get("name") or ""
        t_years = ",".join(str(y) for y in (total.get("year_labels") or []))
        lines.append(f"## {year}年 {gender}")
        lines.append("")
        lines.append(f"- course_era: `{era}`")
        lines.append(
            f"- **総合大会記録**: {t_time}"
            + (f"（{t_school}）" if t_school and t_school != "—" else "")
            + (f" {t_name}" if t_name else "")
            + (f" / {t_years}" if t_years else "")
        )
        lines.append("")
        lines.append("| 区 | 距離 | 区間記録 | 保持者 |")
        lines.append("|---:|---:|---:|---|")
        for leg in mr.get("legs") or []:
            if not isinstance(leg, dict):
                continue
            lines.append(
                f"| {leg.get('leg')} | {leg.get('distance_km') or '—'} | "
                f"{leg.get('time') or '—'} | {holders_text(leg.get('holders') or [])} |"
            )
        lines.append("")
        # searchable prose
        lines.append(
            f"{year}年荒玉駅伝{gender}のボード上部・総合大会記録は{t_time}"
            f"（{t_school}{('/' + t_years) if t_years else ''}）。"
        )
        for leg in mr.get("legs") or []:
            if not isinstance(leg, dict):
                continue
            ht = holders_text(leg.get("holders") or [])
            lines.append(
                f"{year}年荒玉駅伝{gender}の{leg.get('leg')}区大会区間記録は"
                f"{leg.get('time')}・保持者{ht}。"
            )
        lines.append("")

    lines.append("生成: `scripts/generate_aragyoku_meet_records_markdown.py`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = build()
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out.relative_to(ROOT)} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
