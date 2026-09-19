#!/usr/bin/env python3
"""Rebuild aragyoku/winners-by-year.md from transcripts (優勝+準優勝)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANS = ROOT / "input" / "idaten-corpus" / "aragyoku" / "transcripts"
OUTS = [
    ROOT / "input" / "idaten-corpus" / "aragyoku" / "winners-by-year.md",
    ROOT / "input" / "aragyoku" / "winners-by-year.md",
]


def _school(t: dict) -> str:
    return str(t.get("school") or t.get("team") or "").strip()


def _time(t: dict) -> str:
    return str(t.get("time") or t.get("total_time") or t.get("total") or "").strip()


def collect_rows() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(TRANS.glob("*-*.json")):
        year_s, _, gender = path.stem.partition("-")
        if not year_s.isdigit() or gender not in {"男子", "女子"}:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        by_rank = {
            int(t["rank"]): t for t in (data.get("teams") or []) if t.get("rank") in (1, 2)
        }
        w = by_rank.get(1)
        if not w:
            continue
        r = by_rank.get(2)
        rows.append(
            {
                "year": int(year_s),
                "gender": gender,
                "winner": _school(w),
                "winner_time": _time(w),
                "runner": _school(r) if r else "",
                "runner_time": _time(r) if r else "",
            }
        )
    rows.sort(key=lambda x: (x["year"], 0 if x["gender"] == "女子" else 1))
    return rows


def render(rows: list[dict]) -> str:
    lines = [
        "# 荒玉駅伝 年度別優勝・準優勝校",
        "",
        "文字起こし（`input/idaten-corpus/aragyoku/transcripts/*.json`）の "
        "`teams[rank=1]` / `teams[rank=2]` に基づく要約。",
        "「去年の優勝校」「過去5年の優勝・準優勝」などでは、質問時点の西暦とこの表の年度を対応づける。",
        "",
    ]
    recent_w = [r for r in rows if r["year"] >= 2021 and r["gender"] == "女子"]
    recent_m = [r for r in rows if r["year"] >= 2021 and r["gender"] == "男子"]
    lines.extend(
        [
            "## 女子・直近5年（2021–2025）優勝・準優勝",
            "",
            "| 年度 | 優勝校 | 準優勝校 |",
            "| --- | --- | --- |",
        ]
    )
    for r in recent_w:
        lines.append(f"| {r['year']} | {r['winner']} | {r['runner']} |")
    lines.append("")
    lines.append(
        "女子過去5年の優勝・準優勝: "
        + "、".join(f"{r['year']}年 優勝{r['winner']}・準優勝{r['runner']}" for r in recent_w)
        + "。"
    )
    lines.extend(
        [
            "",
            "## 男子・直近5年（2021–2025）優勝・準優勝",
            "",
            "| 年度 | 優勝校 | 準優勝校 |",
            "| --- | --- | --- |",
        ]
    )
    for r in recent_m:
        lines.append(f"| {r['year']} | {r['winner']} | {r['runner']} |")
    lines.append("")
    lines.append(
        "男子過去5年の優勝・準優勝: "
        + "、".join(f"{r['year']}年 優勝{r['winner']}・準優勝{r['runner']}" for r in recent_m)
        + "。"
    )
    lines.extend(
        [
            "",
            "| 年度 | 性別 | 優勝校 | 優勝タイム | 準優勝校 | 準優勝タイム |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for r in rows:
        lines.append(
            f"| {r['year']} | {r['gender']} | {r['winner']} | {r['winner_time']} | "
            f"{r['runner'] or '—'} | {r['runner_time'] or '—'} |"
        )
    lines.append("")
    for r in rows:
        wt = f"（総合 {r['winner_time']}）" if r["winner_time"] else ""
        rt = f"（総合 {r['runner_time']}）" if r["runner_time"] else ""
        lines.append(
            f"{r['year']}年荒玉駅伝{r['gender']}の優勝校は「{r['winner']}」{wt}、"
            f"準優勝校は「{r['runner'] or '（データなし）'}」{rt}。"
            f"1位 {r['winner']}／2位 {r['runner'] or '—'}。"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    text = render(collect_rows())
    for out in OUTS:
        if out.parent.exists():
            out.write_text(text, encoding="utf-8")
            print(f"Wrote {out}")


if __name__ == "__main__":
    main()
