#!/usr/bin/env python3
"""荒玉駅伝：全年度・全チームの平均ペース Markdown を生成する。

正本距離: docs/aragyoku-ekiden-distance-definitions.md
入力: input/idaten-corpus/aragyoku/transcripts/*.json
出力:
  - out/analysis/aragyoku_all_teams_average_pace.md（全チーム）
  - out/analysis/aragyoku_top6_historical_average_pace.md（互換・上位6位要約）

再生成後は build_idaten_corpus.py で rag_index に載せる。
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTS = ROOT / "input" / "idaten-corpus" / "aragyoku" / "transcripts"
OUT_ALL = ROOT / "out" / "analysis" / "aragyoku_all_teams_average_pace.md"
OUT_TOP6 = ROOT / "out" / "analysis" / "aragyoku_top6_historical_average_pace.md"

# docs/aragyoku-ekiden-distance-definitions.md と同一
MEN_BEFORE_2024 = {1: 3.95, 2: 3.05, 3: 2.855, 4: 2.855, 5: 3.00, 6: 4.00}
MEN_FROM_2024 = {1: 3.00, 2: 2.855, 3: 3.00, 4: 3.00, 5: 2.855, 6: 3.00}
WOMEN = {1: 3.00, 2: 1.855, 3: 2.00, 4: 2.00, 5: 3.00}


def fmt_km(km: float) -> str:
    text = f"{km:.3f}".rstrip("0").rstrip(".")
    return f"{text}km"


def parse_time_to_sec(text: str) -> float | None:
    s = (text or "").strip()
    if not s or s in {"—", "-", "DQ", "DNF"}:
        return None
    parts = s.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        return float(parts[0])
    except ValueError:
        return None


def format_pace(sec_per_km: float) -> str:
    total = round(sec_per_km, 1)
    minutes = int(total // 60)
    seconds = total - minutes * 60
    return f"{minutes}:{seconds:04.1f}/km"


def course_distance_km(year: int, gender: str) -> float:
    if gender == "女子":
        return sum(WOMEN.values())
    if year >= 2024:
        return sum(MEN_FROM_2024.values())
    return sum(MEN_BEFORE_2024.values())


def load_rows() -> list[dict]:
    rows: list[dict] = []
    if not TRANSCRIPTS.is_dir():
        return rows
    for path in sorted(TRANSCRIPTS.glob("*-*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        year = data.get("year")
        gender = data.get("gender")
        if not isinstance(year, int) or gender not in {"男子", "女子"}:
            # fallback from filename
            stem = path.stem
            if "-" not in stem:
                continue
            y_s, g = stem.split("-", 1)
            if not y_s.isdigit() or g not in {"男子", "女子"}:
                continue
            year, gender = int(y_s), g
        dist = course_distance_km(year, gender)
        for team in data.get("teams") or []:
            if not isinstance(team, dict):
                continue
            rank = team.get("rank")
            name = (team.get("team") or team.get("school") or "").strip()
            total = (team.get("total") or team.get("time") or "").strip()
            sec = parse_time_to_sec(total)
            if rank is None or not name or sec is None or sec <= 0:
                continue
            try:
                rank_i = int(rank)
            except (TypeError, ValueError):
                continue
            pace = sec / dist
            rows.append(
                {
                    "year": year,
                    "gender": gender,
                    "rank": rank_i,
                    "team": name,
                    "total": total,
                    "sec": sec,
                    "distance_km": dist,
                    "pace_sec": pace,
                    "pace": format_pace(pace),
                }
            )
    rows.sort(key=lambda r: (r["gender"], r["year"], r["rank"], r["team"]))
    return rows


def weighted_pace(items: list[dict]) -> str | None:
    if not items:
        return None
    total_sec = sum(r["sec"] for r in items)
    total_km = sum(r["distance_km"] for r in items)
    if total_km <= 0:
        return None
    return format_pace(total_sec / total_km)


def render_all(rows: list[dict]) -> str:
    lines = [
        "# 荒玉駅伝：全チーム・年度別の平均ペース",
        "",
        "各年度・男女の**全出場チーム**について、総合タイム ÷ 当年コース総距離で平均ペース（分:秒/km）を算出した正本。",
        "距離定義は [`docs/aragyoku-ekiden-distance-definitions.md`](../../docs/aragyoku-ekiden-distance-definitions.md) に従う。",
        "",
        "- **チーム全体の平均ペース** = 総合タイム ÷ コース総距離（区間合算）",
        "- 「〇位の平均ペース」「過去の〇位平均」→ 下記の順位別歴代表",
        "- 「〇〇中の平均ペース（某年）」→ 年度別全チーム表",
        "- 上位6位だけの要約は `aragyoku_top6_historical_average_pace.md`（互換）",
        "",
        "## コース総距離",
        "",
        f"- 男子・2023年以前: {fmt_km(sum(MEN_BEFORE_2024.values()))}",
        f"- 男子・2024年以降: {fmt_km(sum(MEN_FROM_2024.values()))}",
        f"- 女子・全年度: {fmt_km(sum(WOMEN.values()))}",
        "",
    ]

    for gender in ("男子", "女子"):
        g_rows = [r for r in rows if r["gender"] == gender]
        if not g_rows:
            continue
        lines.append(f"## {gender}")
        lines.append("")

        # Rank historical averages (all ranks that appear)
        by_rank: dict[int, list[dict]] = defaultdict(list)
        for r in g_rows:
            by_rank[r["rank"]].append(r)
        lines.append(f"### {gender}・順位別の歴代平均ペース（全順位）")
        lines.append("")
        lines.append("| 総合順位 | 対象年度数 | 平均ペース |")
        lines.append("|---:|---:|---:|")
        for rank in sorted(by_rank):
            items = by_rank[rank]
            pace = weighted_pace(items)
            years = len({r["year"] for r in items})
            lines.append(f"| {rank}位 | {years} | {pace} |")
            # BM25-friendly prose
            lines.append(
                f"{gender}の総合{rank}位の歴代平均ペースは {pace}（{years}年度）。"
            )
        lines.append("")

        overall = weighted_pace(g_rows)
        years_n = len({r["year"] for r in g_rows})
        lines.append(
            f"**{gender}・全チーム期間加重平均：{overall}**（{years_n}年度、"
            f"{len(g_rows)}チーム）"
        )
        lines.append("")

        # Per year full tables
        years = sorted({r["year"] for r in g_rows})
        for year in years:
            y_rows = [r for r in g_rows if r["year"] == year]
            dist = y_rows[0]["distance_km"]
            lines.append(f"### {year}年{gender}（コース {fmt_km(dist)}）")
            lines.append("")
            lines.append("| 順位 | 学校 | 総合タイム | 平均ペース |")
            lines.append("|---:|---|---:|---:|")
            for r in y_rows:
                lines.append(
                    f"| {r['rank']} | {r['team']} | {r['total']} | {r['pace']} |"
                )
                lines.append(
                    f"{year}年荒玉駅伝{gender}{r['rank']}位 {r['team']} の"
                    f"チーム全体平均ペースは {r['pace']}（総合 {r['total']}／{fmt_km(dist)}）。"
                )
            y_avg = weighted_pace(y_rows)
            lines.append("")
            lines.append(
                f"{year}年{gender}の全チーム平均ペース（加重）は {y_avg}（{len(y_rows)}チーム）。"
            )
            lines.append("")

        # Compact year×rank matrix for ranks that appear often (1..max)
        max_rank = max(r["rank"] for r in g_rows)
        show_ranks = list(range(1, min(max_rank, 15) + 1))
        lines.append(f"### {gender}・各年度×順位の平均ペース（抜粋マトリクス）")
        lines.append("")
        header = "| 年度 | " + " | ".join(f"{n}位" for n in show_ranks) + " |"
        sep = "|---:|" + "|".join(["---:"] * len(show_ranks)) + "|"
        lines.append(header)
        lines.append(sep)
        for year in years:
            cells = []
            ymap = {r["rank"]: r["pace"] for r in g_rows if r["year"] == year}
            for n in show_ranks:
                cells.append(ymap.get(n, "—"))
            lines.append(f"| {year} | " + " | ".join(cells) + " |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_top6(rows: list[dict]) -> str:
    """互換用：従来の top6 要約ファイルを同一計算で再生成。"""
    lines = [
        "# 荒玉駅伝：過去総合6位以内の平均ペース",
        "",
        "各年度・男女別に、総合1〜6位チームの総合タイムを当年のコース総距離で換算した平均ペースです。"
        "年度横断の平均は、各チームの総走行時間と走行距離を合算した加重平均です。",
        "",
        "> 全チーム版は `aragyoku_all_teams_average_pace.md` を正本とする。",
        "",
    ]
    for gender in ("男子", "女子"):
        g_rows = [r for r in rows if r["gender"] == gender and r["rank"] <= 6]
        if not g_rows:
            continue
        lines.append(f"## {gender}")
        lines.append("")
        lines.append("| 年度 | 対象チーム数 | コース距離 | 総合1〜6位の平均ペース |")
        lines.append("|---:|---:|---:|---:|")
        years = sorted({r["year"] for r in g_rows})
        for year in years:
            y_rows = [r for r in g_rows if r["year"] == year]
            lines.append(
                f"| {year} | {len(y_rows)} | {fmt_km(y_rows[0]['distance_km'])} | "
                f"{weighted_pace(y_rows)} |"
            )
        overall = weighted_pace(g_rows)
        years_n = len(years)
        lines.append("")
        lines.append(
            f"**期間加重平均：{overall}**（{years_n}年度、総合{len(g_rows)}チーム）"
        )
        lines.append("")
        lines.append("### 順位別の歴代平均ペース")
        lines.append("")
        lines.append("| 総合順位 | 対象年度数 | 平均ペース |")
        lines.append("|---:|---:|---:|")
        for rank in range(1, 7):
            items = [r for r in g_rows if r["rank"] == rank]
            if not items:
                continue
            lines.append(
                f"| {rank}位 | {len({r['year'] for r in items})} | {weighted_pace(items)} |"
            )
        lines.append("")
        lines.append("### 各年度・順位別ペース")
        lines.append("")
        lines.append("| 年度 | 1位 | 2位 | 3位 | 4位 | 5位 | 6位 |")
        lines.append("|---:|---:|---:|---:|---:|---:|---:|")
        for year in years:
            ymap = {r["rank"]: r["pace"] for r in g_rows if r["year"] == year}
            cells = [ymap.get(n, "—") for n in range(1, 7)]
            lines.append(f"| {year} | " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    rows = load_rows()
    if not rows:
        print("error: no transcript teams found", flush=True)
        return 1
    OUT_ALL.parent.mkdir(parents=True, exist_ok=True)
    OUT_ALL.write_text(render_all(rows), encoding="utf-8")
    OUT_TOP6.write_text(render_top6(rows), encoding="utf-8")
    print(
        f"wrote {OUT_ALL.relative_to(ROOT)} ({len(rows)} team-rows) and "
        f"{OUT_TOP6.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
