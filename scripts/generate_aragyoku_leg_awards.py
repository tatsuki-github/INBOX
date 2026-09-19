#!/usr/bin/env python3
"""荒玉駅伝の区間賞・区間順位を検索用 Markdown に展開する。

正本: input/aragyoku/transcripts/{year}-{gender}.json
  - 区間賞 = split_rank == 1（同タイム複数は併記）
  - split_rank が全年欠損の場合は区間タイムから再計算
出力: out/analysis/aragyoku_leg_awards.md
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTS = ROOT / "input" / "aragyoku" / "transcripts"
OUT = ROOT / "out" / "analysis" / "aragyoku_leg_awards.md"


def parse_split_seconds(split: Any) -> int | None:
    if split is None:
        return None
    m = re.match(r"^(\d+):(\d{2})$", str(split).strip())
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def load_year(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def collect_leg_rows(data: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    by_leg: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for team in data.get("teams") or []:
        if not isinstance(team, dict):
            continue
        school = str(team.get("team") or "").strip() or "?"
        for leg in team.get("legs") or []:
            if not isinstance(leg, dict):
                continue
            if leg.get("status") not in (None, "ok", ""):
                # keep ok / missing status; skip explicit DQ etc. if present
                if str(leg.get("status")).lower() in {"dq", "dns", "dnf"}:
                    continue
            leg_n = leg.get("leg")
            if not isinstance(leg_n, int):
                continue
            by_leg[leg_n].append(
                {
                    "leg": leg_n,
                    "name": str(leg.get("name") or "").strip() or "?",
                    "grade": leg.get("grade"),
                    "team": school,
                    "split": str(leg.get("split") or "").strip() or "—",
                    "split_rank": leg.get("split_rank"),
                    "split_record": bool(leg.get("split_record")),
                    "seconds": parse_split_seconds(leg.get("split")),
                }
            )
    return by_leg


def awards_from_board(by_leg: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for leg_n in sorted(by_leg):
        winners = [r for r in by_leg[leg_n] if r.get("split_rank") == 1]
        out.extend(sorted(winners, key=lambda r: (r["team"], r["name"])))
    return out


def awards_from_times(by_leg: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for leg_n in sorted(by_leg):
        timed = [r for r in by_leg[leg_n] if r["seconds"] is not None]
        if not timed:
            continue
        best = min(r["seconds"] for r in timed)
        winners = [r for r in timed if r["seconds"] == best]
        for r in winners:
            r = {**r, "split_rank": 1}
            out.append(r)
    return out


def top_n_for_leg(
    rows: list[dict[str, Any]], n: int = 3
) -> list[dict[str, Any]]:
    with_rank = [r for r in rows if isinstance(r.get("split_rank"), int)]
    if with_rank:
        ordered = sorted(
            with_rank,
            key=lambda r: (r["split_rank"], r["seconds"] if r["seconds"] is not None else 10**9),
        )
        return ordered[:n]
    timed = [r for r in rows if r["seconds"] is not None]
    timed.sort(key=lambda r: r["seconds"] or 10**9)
    out: list[dict[str, Any]] = []
    for i, r in enumerate(timed[:n], start=1):
        out.append({**r, "split_rank": i})
    return out


def grade_s(grade: Any) -> str:
    if grade in (None, ""):
        return "—"
    return str(grade)


def build() -> str:
    paths = sorted(TRANSCRIPTS.glob("*.json"), reverse=True)
    year_blocks: list[tuple[int, str, str]] = []

    for path in paths:
        data = load_year(path)
        if not data:
            continue
        year = data.get("year")
        gender = data.get("gender")
        if not isinstance(year, int) or gender not in ("男子", "女子"):
            continue
        by_leg = collect_leg_rows(data)
        board = awards_from_board(by_leg)
        source = "board"
        if not board:
            board = awards_from_times(by_leg)
            source = "computed" if board else "missing"

        lines: list[str] = []
        lines.append(f"### {year}年{gender}")
        lines.append("")
        if source == "missing":
            lines.append(
                f"- **区間賞**: データ不足（`split_rank` / 区間タイムから特定不可）。"
            )
            lines.append("")
            year_blocks.append((year, gender, "\n".join(lines)))
            continue

        note = ""
        if source == "computed":
            note = "（ボード区間順位欠損のため区間タイムから算出）"
        lines.append(f"- **区間賞**{note}（`split_rank=1`、同タイムは併記）")
        lines.append("")
        lines.append("| 区 | 選手 | 学年 | 学校 | 区間タイム | 区間新 |")
        lines.append("|---:|---|---:|---|---:|:---:|")
        for r in board:
            flag = "○" if r.get("split_record") else ""
            lines.append(
                f"| {r['leg']} | {r['name']} | {grade_s(r['grade'])} | "
                f"{r['team']} | {r['split']} | {flag} |"
            )
        lines.append("")
        for r in board:
            rec = "（区間新）" if r.get("split_record") else ""
            lines.append(
                f"{year}年荒玉駅伝{gender}の{r['leg']}区区間賞は"
                f"{r['name']}（{grade_s(r['grade'])}年・{r['team']}）"
                f"・{r['split']}{rec}。"
            )
        lines.append("")
        lines.append(f"#### {year}年{gender}・区間別上位（区間順位）")
        lines.append("")
        for leg_n in sorted(by_leg):
            top = top_n_for_leg(by_leg[leg_n], 3)
            if not top:
                continue
            lines.append(f"**{leg_n}区**")
            lines.append("")
            lines.append("| 区間順 | 選手 | 学年 | 学校 | 区間タイム |")
            lines.append("|---:|---|---:|---|---:|")
            for r in top:
                lines.append(
                    f"| {r.get('split_rank')} | {r['name']} | {grade_s(r['grade'])} | "
                    f"{r['team']} | {r['split']} |"
                )
            lines.append("")
            for r in top:
                lines.append(
                    f"{year}年荒玉駅伝{gender}{r['leg']}区の区間{r.get('split_rank')}位は"
                    f"{r['name']}（{grade_s(r['grade'])}年・{r['team']}）・{r['split']}。"
                )
            lines.append("")

        year_blocks.append((year, gender, "\n".join(lines)))

    # Newest years first for RAG / offline preview
    year_blocks.sort(key=lambda x: (-x[0], 0 if x[1] == "男子" else 1))

    header = [
        "# 荒玉駅伝：区間賞・区間順位",
        "",
        "各年度・男女の **区間賞（区間1位）** と **区間別上位3**。",
        "正本は [`input/aragyoku/transcripts/`](../../input/aragyoku/transcripts/) の `split_rank` / `name` / `grade`。",
        "",
        "## Q&A の使い方",
        "",
        "- 「○年の区間賞の名前と学年は？」→ **この文書の区間賞表**",
        "- 「○年○区の区間順位は？」「○区2位は誰？」→ **区間別上位**",
        "- ボード上部の**歴代区間記録**（保持者）は `aragyoku_meet_records.md`（別概念）",
        "- 当日の区間新フラグは区間賞表の「区間新」列（`split_record`）",
        "",
        "## コース注記",
        "",
        "- 男子: 6区 / 女子: 5区",
        "- 同タイムの場合は区間賞を複数行で併記する",
        "",
    ]
    return "\n".join(header + [block for _, _, block in year_blocks]).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    text = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    awards = text.count("区間賞は")
    print(f"wrote {args.out} ({awards} award prose lines)")


if __name__ == "__main__":
    main()
