#!/usr/bin/env python3
"""Generate a current-year school roster + SB digest for Q&A retrieval.

The wide SB CSV is an all-school snapshot and is intentionally chunked by row.
That is useful for athlete lookups, but it cannot answer a school-level
"players and SB" question reliably when a school has no row in that snapshot.
The year-specific adopted JSON is the canonical source for this digest.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SB_DIR = ROOT / "input" / "external" / "sb" / "middle-school" / "by-year"
OUT_DIR = ROOT / "out" / "analysis" / "arato-tamana-teams"


def _time_key(value: str) -> tuple[int, float]:
    parts = value.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]), float(parts[1])
        return 0, float(parts[0])
    except ValueError:
        return (10**9, 10**9)


def _load_rows(year: int, affiliation: str) -> list[dict[str, Any]]:
    path = SB_DIR / f"{year}-sb-adopted.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [row for row in rows if row.get("所属") == affiliation]


def render_digest(year: int, affiliation: str) -> str:
    rows = _load_rows(year, affiliation)
    if not rows:
        raise ValueError(f"no SB rows for {affiliation!r} in {year}")

    athletes: dict[str, tuple[str, str]] = {}
    by_distance: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        name = str(row.get("名前") or "")
        distance = str(row.get("距離") or "")
        if not name or not distance:
            continue
        athletes[name] = (str(row.get("性別") or ""), str(row.get("学年") or ""))
        key = (name, distance)
        current = by_distance.get(key)
        sb = str(row.get("SB") or row.get("記録") or "")
        if current is None or _time_key(sb) < _time_key(str(current.get("SB") or "")):
            by_distance[key] = row

    lines = [
        f"# {affiliation} 選手・SB一覧（{year}年度）",
        "",
        f"{year}年度の SB 採用記録から、{affiliation} の選手と距離別 SB をまとめた一覧。",
        "年度指定がない学校別質問では、この現行年度一覧を回答の正本として使用する。",
        "",
        f"出典: `input/external/sb/middle-school/by-year/{year}-sb-adopted.json`",
        "",
        "## 選手一覧",
        "",
        "| 選手 | 性別 | 学年 |",
        "|---|---|---:|",
    ]
    for name in sorted(athletes):
        gender, grade = athletes[name]
        lines.append(f"| {name} | {gender} | {grade} |")

    lines.extend(["", "## SB一覧", "", "| 選手 | 性別 | 学年 | 距離 | SB | 日付 | 大会結果URL |", "|---|---|---:|---|---:|---|---|"])
    ordered = sorted(
        by_distance.values(),
        key=lambda r: (str(r.get("名前") or ""), str(r.get("距離") or "")),
    )
    for row in ordered:
        url = str(row.get("参考") or "").replace("|", "/")
        lines.append(
            f"| {row.get('名前', '')} | {row.get('性別', '')} | {row.get('学年', '')} | "
            f"{row.get('距離', '')} | {row.get('SB', '')} | {row.get('日付', '')} | {url} |"
        )
    lines.extend(["", f"件数: 選手 {len(athletes)}人、SB {len(ordered)}件"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--affiliation", default="荒尾三中")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{args.affiliation}_SB.md"
    path.write_text(render_digest(args.year, args.affiliation), encoding="utf-8")
    print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
