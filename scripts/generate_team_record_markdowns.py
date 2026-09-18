#!/usr/bin/env python3
"""荒尾玉名チーム別・荒玉駅伝チーム別の全年記録 Markdown を生成する。

Outputs:
  out/analysis/arato-tamana-teams/{team}.md   — トラック記録（年度ごと・全件）
  out/analysis/aragyoku-teams/{team}.md       — 荒玉駅伝 年度別フル結果
  out/analysis/arato-tamana-teams/INDEX.md
  out/analysis/aragyoku-teams/INDEX.md

再生成後は `python3 scripts/build_idaten_corpus.py` で rag_index に載せる。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arato_tamana_records import (  # noqa: E402
    RecordRow,
    filter_rows,
    group_by_affiliation,
    load_config,
    matches_arato_tamana,
    row_from_cache_dict,
    sort_records,
)

ARATO_OUT = ROOT / "out" / "analysis" / "arato-tamana-teams"
ARAGYOKU_OUT = ROOT / "out" / "analysis" / "aragyoku-teams"
TRANSCRIPTS = ROOT / "input" / "aragyoku" / "transcripts"
NOTION_YEAR_SOURCES: list[tuple[str, Path]] = [
    ("2024", ROOT / "input" / "external" / "notion" / "databases" / "2024年度中学生" / "rows.json"),
    ("2025", ROOT / "input" / "external" / "notion" / "databases" / "2025年度中学生記録" / "rows.json"),
    ("2026", ROOT / "out" / "analysis" / "notion_records_2026.json"),
]


def safe_filename(name: str) -> str:
    text = name.strip() or "unknown"
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    text = re.sub(r"\s+", "_", text)
    return text[:80]


def row_from_notion_export(item: dict[str, Any]) -> tuple[RecordRow, str]:
    """2024/2025 の rows.json（日本語キー）を RecordRow に変換。"""
    if "affiliation" in item or "name" in item:
        return row_from_cache_dict(item), str(item.get("prefecture") or item.get("都道府県") or "")

    sb_adopted_raw = item.get("SB採用")
    sb_adopted = sb_adopted_raw in (True, "__YES__", "YES", "yes", 1, "1")
    grade = item.get("学年")
    try:
        grade_i = int(grade) if grade is not None and grade != "" else None
    except (TypeError, ValueError):
        grade_i = None
    seconds = item.get("記録秒")
    try:
        seconds_f = float(seconds) if seconds is not None else None
    except (TypeError, ValueError):
        seconds_f = None
    row = RecordRow(
        name=str(item.get("名前") or ""),
        affiliation=str(item.get("所属") or ""),
        grade=grade_i,
        gender=str(item.get("性別") or ""),
        distance=str(item.get("距離") or ""),
        time_text=str(item.get("記録") or ""),
        sb_text=str(item.get("SB") or item.get("sb_text") or ""),
        sb_adopted=sb_adopted,
        date=str(item.get("日付") or ""),
        url=str(item.get("参考") or item.get("url") or ""),
        record_seconds=seconds_f,
    )
    return row, str(item.get("都道府県") or "")


def load_year_records(year: str, path: Path, config: dict[str, Any]) -> list[RecordRow]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    paired: list[tuple[RecordRow, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        row, pref = row_from_notion_export(item)
        paired.append((row, pref))
    # 2026 cache is already region-filtered; still apply matches for consistency
    if year == "2026" and path.name.startswith("notion_records"):
        return [r for r, _ in paired if matches_arato_tamana(r, config)]
    return filter_rows(paired, config)


def render_arato_team_md(affiliation: str, by_year: dict[str, list[RecordRow]]) -> str:
    lines: list[str] = [
        f"# {affiliation} 記録一覧（荒尾玉名）",
        "",
        "荒尾・玉名地区の中学生トラック記録を所属（チーム）単位でまとめたもの。",
        "出典: Notion 中学生記録 DB / `notion_records_2026.json`。",
        "",
    ]
    for year in sorted(by_year.keys()):
        rows = sort_records(by_year[year])
        lines.append(f"## {year}年度")
        lines.append("")
        lines.append(f"件数: {len(rows)}")
        lines.append("")
        # group by distance then gender
        by_dist: dict[str, list[RecordRow]] = defaultdict(list)
        for r in rows:
            by_dist[r.distance or "（距離不明）"].append(r)
        dist_order = ["800m", "1500m", "3000m", "3000mSC", "5000m"]
        dists = sorted(by_dist.keys(), key=lambda d: (dist_order.index(d) if d in dist_order else 99, d))
        for dist in dists:
            lines.append(f"### {dist}")
            lines.append("")
            lines.append("| 性別 | 学年 | 選手 | 記録 | 日付 | 大会/URL |")
            lines.append("|---|---:|---|---:|---|---|")
            for r in by_dist[dist]:
                grade = "" if r.grade is None else str(r.grade)
                meet = r.url.replace("|", "/") if r.url else ""
                if len(meet) > 60:
                    meet = meet[:57] + "..."
                lines.append(
                    f"| {r.gender} | {grade} | {r.name} | {r.time_text} | {r.date} | {meet} |"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_arato_tamana_team_mds(config: dict[str, Any]) -> list[Path]:
    # affiliation -> year -> records
    bucket: dict[str, dict[str, list[RecordRow]]] = defaultdict(lambda: defaultdict(list))
    for year, path in NOTION_YEAR_SOURCES:
        rows = load_year_records(year, path, config)
        for row in rows:
            aff = row.affiliation or "（所属不明）"
            bucket[aff][year].append(row)

    ARATO_OUT.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    index_lines = [
        "# 荒尾玉名 チーム別記録 INDEX",
        "",
        "各ファイルは所属ごとの全年トラック記録一覧。",
        "",
        "| チーム | ファイル | 年度件数 |",
        "|---|---|---|",
    ]
    for section in group_by_affiliation(
        [r for years in bucket.values() for rs in years.values() for r in rs]
    ):
        aff = section.affiliation
        by_year = bucket.get(aff) or {}
        if not by_year:
            continue
        path = ARATO_OUT / f"{safe_filename(aff)}.md"
        path.write_text(render_arato_team_md(aff, by_year), encoding="utf-8")
        written.append(path)
        counts = ", ".join(f"{y}:{len(by_year[y])}" for y in sorted(by_year))
        index_lines.append(f"| {aff} | `{path.name}` | {counts} |")

    index_path = ARATO_OUT / "INDEX.md"
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    written.append(index_path)
    return written


def _format_leg_line(leg: dict[str, Any]) -> str:
    num = leg.get("leg", "?")
    name = leg.get("name") or "?"
    grade = leg.get("grade")
    split = leg.get("split") or ""
    cum = leg.get("cumulative") or ""
    g = f"{grade}" if grade not in (None, "") else "?"
    return f"| {num} | {name} | {g} | {split} | {cum} |"


def render_aragyoku_team_md(team: str, entries: list[dict[str, Any]]) -> str:
    lines = [
        f"# {team} 荒玉駅伝 歴代結果",
        "",
        "玉名荒尾中体連駅伝（荒玉駅伝）の構造化 transcripts から、チーム単位で全年の結果を整理。",
        "",
    ]
    # sort by year desc, men then women
    entries = sorted(
        entries,
        key=lambda e: (-int(e.get("year") or 0), 0 if e.get("gender") == "男子" else 1),
    )
    for e in entries:
        year = e.get("year")
        gender = e.get("gender")
        rank = e.get("rank")
        total = e.get("total") or "—"
        lines.append(f"## {year}年 {gender}")
        lines.append("")
        lines.append(f"- 順位: **{rank}位**")
        lines.append(f"- 総合: **{total}**")
        if rank in (1, "1"):
            lines.append("- 優勝校")
        lines.append("")
        legs = [L for L in (e.get("legs") or []) if isinstance(L, dict)]
        if legs:
            lines.append("| 区 | 選手 | 学年 | 区間 | 累計 |")
            lines.append("|---:|---|---:|---:|---:|")
            for L in sorted(legs, key=lambda x: int(x.get("leg") or 0)):
                lines.append(_format_leg_line(L))
            lines.append("")
        # searchable one-liner
        names = "、".join(
            str(L.get("name") or "") for L in legs if L.get("name")
        )
        lines.append(
            f"{year}年荒玉駅伝{gender} {team}は{rank}位・総合{total}。"
            + (f" 区間選手: {names}。" if names else "")
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_aragyoku_team_mds() -> list[Path]:
    by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not TRANSCRIPTS.is_dir():
        return []
    for path in sorted(TRANSCRIPTS.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        year = data.get("year")
        gender = data.get("gender")
        for team in data.get("teams") or []:
            if not isinstance(team, dict):
                continue
            name = str(team.get("team") or "").strip()
            if not name:
                continue
            by_team[name].append(
                {
                    "year": year,
                    "gender": gender,
                    "rank": team.get("rank"),
                    "total": team.get("total"),
                    "legs": team.get("legs") or [],
                }
            )

    ARAGYOKU_OUT.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    index_lines = [
        "# 荒玉駅伝 チーム別歴代 INDEX",
        "",
        "| チーム | ファイル | 出場年数 |",
        "|---|---|---|",
    ]
    for team in sorted(by_team.keys()):
        path = ARAGYOKU_OUT / f"{safe_filename(team)}.md"
        path.write_text(render_aragyoku_team_md(team, by_team[team]), encoding="utf-8")
        written.append(path)
        years = sorted({str(e.get("year")) for e in by_team[team]})
        index_lines.append(f"| {team} | `{path.name}` | {len(years)}（{years[0]}–{years[-1]}） |")

    index_path = ARAGYOKU_OUT / "INDEX.md"
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    written.append(index_path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arato-only", action="store_true")
    parser.add_argument("--aragyoku-only", action="store_true")
    args = parser.parse_args()
    config = load_config()

    written: list[Path] = []
    if not args.aragyoku_only:
        written.extend(generate_arato_tamana_team_mds(config))
    if not args.arato_only:
        written.extend(generate_aragyoku_team_mds())

    print(f"wrote {len(written)} files")
    for p in written[:8]:
        print(" ", p.relative_to(ROOT))
    if len(written) > 8:
        print(f"  ... +{len(written) - 8} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
