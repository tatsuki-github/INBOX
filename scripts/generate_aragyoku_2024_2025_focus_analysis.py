#!/usr/bin/env python3
"""2024–2025 荒玉駅伝の深掘り分析（岱明・玉高附属・天水・有明）を生成する。

出力:
  out/analysis/aragyoku_2024_2025_focus_teams.md

正本データは input/aragyoku/transcripts/{year}-{gender}.json。
再生成後は build_idaten_corpus.py / build_knowledge_graph.py で検索・KG に載せる。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTS = ROOT / "input" / "aragyoku" / "transcripts"
OUT = ROOT / "out" / "analysis" / "aragyoku_2024_2025_focus_teams.md"

# ユーザー向け表記 → transcript 上の正式チーム名
FOCUS_TEAMS: list[tuple[str, str, list[str]]] = [
    ("岱明", "岱明", ["岱明中", "岱明"]),
    ("玉高附属", "玉高附属", ["玉名付属中", "玉名附属", "玉名高校附属", "玉高附属", "玉名附"]),
    ("天水", "天水", ["天水中", "天水"]),
    ("有明", "有明", ["有明中", "有明"]),
]
YEARS = (2024, 2025)
GENDERS = ("男子", "女子")


def parse_time(text: str | None) -> float | None:
    if not text:
        return None
    parts = str(text).strip().replace("'", ":").split(":")
    parts = [p for p in parts if p != ""]
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except (TypeError, ValueError):
        return None
    return None


def fmt_delta(sec: float) -> str:
    if abs(sec) < 0.05:
        return "±0"
    sign = "+" if sec > 0 else "-"
    sec = abs(sec)
    minutes = int(sec) // 60
    rem = sec - minutes * 60
    if minutes:
        return f"{sign}{minutes}:{rem:05.2f}"
    return f"{sign}{rem:.2f}s"


def load_year_gender(year: int, gender: str) -> dict[str, Any]:
    path = TRANSCRIPTS / f"{year}-{gender}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def team_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(t["team"]): t for t in data.get("teams") or [] if isinstance(t, dict)}


def best_worst_legs(team: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    legs = [L for L in (team.get("legs") or []) if isinstance(L, dict)]
    ranked = sorted(legs, key=lambda L: int(L.get("split_rank") or 99))
    return ranked[0], ranked[-1]


def leg_row(L: dict[str, Any]) -> str:
    rec = " ★区間新" if L.get("split_record") else ""
    grade = L.get("grade")
    grade_s = f"{grade}" if grade not in (None, "") else "—"
    return (
        f"| {L.get('leg')} | {L.get('name') or 'unknown'} | {grade_s} | "
        f"{L.get('split') or '—'} | {L.get('split_rank') or '—'} | "
        f"{L.get('passing_rank') or '—'} | {L.get('cumulative') or '—'}{rec} |"
    )


def returning_names(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    n24 = {str(L.get("name")) for L in (a.get("legs") or []) if L.get("name") and L.get("name") != "unknown"}
    n25 = {str(L.get("name")) for L in (b.get("legs") or []) if L.get("name") and L.get("name") != "unknown"}
    return sorted(n24 & n25)


def narrative_for(
    display: str,
    canonical: str,
    aliases: list[str],
    bundles: dict[tuple[int, str], dict[str, Any]],
) -> list[str]:
    lines: list[str] = [
        f"## {display}（transcript 表記: {canonical}）",
        "",
        f"別名・呼び方: {', '.join(aliases)}",
        "",
    ]

    for gender in GENDERS:
        t24 = bundles[(2024, gender)].get(canonical)
        t25 = bundles[(2025, gender)].get(canonical)
        w24 = bundles[(2024, gender, "winner")]  # type: ignore[index]
        w25 = bundles[(2025, gender, "winner")]  # type: ignore[index]
        if not t24 or not t25:
            lines.append(f"### {gender}: データ不足")
            lines.append("")
            continue

        sec24 = parse_time(str(t24.get("total")))
        sec25 = parse_time(str(t25.get("total")))
        delta = (sec25 - sec24) if sec24 is not None and sec25 is not None else None
        gap24 = (
            parse_time(str(t24.get("total"))) - parse_time(str(w24.get("total")))
            if parse_time(str(t24.get("total"))) is not None and parse_time(str(w24.get("total"))) is not None
            else None
        )
        gap25 = (
            parse_time(str(t25.get("total"))) - parse_time(str(w25.get("total")))
            if parse_time(str(t25.get("total"))) is not None and parse_time(str(w25.get("total"))) is not None
            else None
        )

        lines.append(f"### {gender}")
        lines.append("")
        lines.append("| 年 | 順位 | 総合 | 優勝との差 | 優勝校 |")
        lines.append("|---:|---:|---:|---:|---|")
        lines.append(
            f"| 2024 | {t24.get('rank')}位 | {t24.get('total')} | "
            f"{fmt_delta(gap24) if gap24 is not None else '—'} | "
            f"{w24.get('team')} {w24.get('total')} |"
        )
        lines.append(
            f"| 2025 | {t25.get('rank')}位 | {t25.get('total')} | "
            f"{fmt_delta(gap25) if gap25 is not None else '—'} | "
            f"{w25.get('team')} {w25.get('total')} |"
        )
        lines.append("")
        if delta is not None:
            rank_delta = int(t24.get("rank") or 0) - int(t25.get("rank") or 0)
            faster = "短縮（速くなった）" if delta < 0 else ("悪化（遅くなった）" if delta > 0 else "ほぼ同タイム")
            lines.append(
                f"- **前年比総合**: {fmt_delta(delta)}（{faster}）、順位 {int(t24.get('rank'))}位 → "
                f"{int(t25.get('rank'))}位（順位変動 {rank_delta:+d}）"
            )
        ret = returning_names(t24, t25)
        if ret:
            lines.append(f"- **連続出場（氏名一致）**: {', '.join(ret)}")
        lines.append("")

        for year, team in ((2024, t24), (2025, t25)):
            best, worst = best_worst_legs(team)
            lines.append(f"#### {year}年 区間明細")
            lines.append("")
            lines.append("| 区 | 選手 | 学年 | 区間 | 区間順 | 通過順 | 累計 |")
            lines.append("|---:|---|---:|---:|---:|---:|---:|")
            for L in sorted(team.get("legs") or [], key=lambda x: int(x.get("leg") or 0)):
                lines.append(leg_row(L))
            lines.append("")
            lines.append(
                f"- 区間順位ベスト: {best.get('leg')}区 {best.get('name')} "
                f"（区間順 {best.get('split_rank')}・{best.get('split')}）"
            )
            lines.append(
                f"- 区間順位ワースト: {worst.get('leg')}区 {worst.get('name')} "
                f"（区間順 {worst.get('split_rank')}・{worst.get('split')}）"
            )
            records = [
                L
                for L in (team.get("legs") or [])
                if isinstance(L, dict) and L.get("split_record")
            ]
            if records:
                for L in records:
                    lines.append(
                        f"- **区間新**: {L.get('leg')}区 {L.get('name')} {L.get('split')}"
                    )
            lines.append("")

        # 短い読み取り
        lines.append("#### 読み取り")
        lines.append("")
        lines.extend(reading_notes(display, gender, t24, t25, delta))
        lines.append("")

    return lines


def reading_notes(
    display: str,
    gender: str,
    t24: dict[str, Any],
    t25: dict[str, Any],
    delta: float | None,
) -> list[str]:
    """チーム×性別ごとの要約コメント（transcript 根拠の事実に限定）。"""
    notes: list[str] = []
    r24, r25 = int(t24.get("rank") or 0), int(t25.get("rank") or 0)

    if display == "岱明" and gender == "男子":
        notes.append(
            "- 2024は15位・65:15（4区が区間順15位のボトルネック）から、2025は6位・59:08へ大幅上昇。"
            " 総合約6分短縮、優勝差も約8:37→約2:51まで縮まった。"
        )
        notes.append(
            "- 2025は5区・山本哲瑠が区間順2位（9:37）。中盤〜後半の底上げが順位浮上の主因。"
        )
        notes.append("- 連続出場: 倉田裕斗・松野凛空・今村昇磨が学年進行で再出場。")
    elif display == "岱明" and gender == "女子":
        notes.append(
            "- 2024:6位45:06 → 2025:7位45:22。順位・タイムともわずかに後退（+16秒）。"
        )
        notes.append(
            "- 2025は2区・増岡里俐が区間順3位（7:01）と強み。5区に移った高田麻由は区間順6位。"
        )
        notes.append("- 連続出場: 村上咲稀・高田麻由。")
    elif display == "玉高附属" and gender == "男子":
        notes.append(
            "- 2024は準優勝（2位58:13、優勝南関から+1:35）。2025は3位58:37（+24秒、順位-1）。"
        )
        notes.append(
            "- 3区で2年連続区間新級の強み: 2024亀井遼希9:24（区間1・区間新）、"
            "2025草野瑠唯9:14（区間1・区間新）。"
        )
        notes.append("- 2025は1区が区間順11位スタート。中盤の巻き返しで3位を確保。")
        notes.append("- 連続出場: 草野瑠唯・秋原康秀。")
    elif display == "玉高附属" and gender == "女子":
        notes.append(
            "- 2024:5位43:50 → 2025:10位46:55。総合+3:05・順位-5と大きく後退。"
        )
        notes.append(
            "- 1区・鹿子木歩は両年とも好位置（2024区間1、2025区間2・同タイム10:16）。"
            " 中間区（2〜4区）の区間順が2025で悪化し総合を押し下げた。"
        )
        notes.append(
            "- 2025アンカー大木莉子は区間1位（10:30）だが、通過順は10位のままフィニッシュ。"
        )
        notes.append("- 連続出場: 鹿子木歩・大木莉子。")
    elif display == "天水" and gender == "男子":
        notes.append(
            "- 両年とも14位前後（2024:63:40、2025:63:39）。総合はほぼ横ばい。"
        )
        notes.append(
            "- ハイライトは2025・2区山本悠斗の8:37（区間1・区間新）。通過順も1位まで押し上げた。"
            " その後4〜5区が区間順14〜15位となり、総合は再び下位に沈んだ。"
        )
        notes.append("- 連続出場: 山本悠斗・木村幹太・田上遥睦。")
    elif display == "天水" and gender == "女子":
        notes.append(
            "- 2024:14位49:41 → 2025:15位51:29（+1:48）。全区間で区間順が下位帯。"
        )
        notes.append(
            "- メンバー継続率が高い（浦田咲希・竹原奈緒美・竹原晴美・花谷明優・荒木優里）が、"
            " タイム短縮にはつながっていない。"
        )
    elif display == "有明" and gender == "男子":
        notes.append(
            "- 2024:11位61:49 → 2025:12位62:31（+42秒）。"
        )
        notes.append(
            "- 2024は1区・米村和真が区間新9:01で首位通過。その後中盤で後退し11位。"
        )
        notes.append(
            "- 2025は竹下響佑が1区（区間順9）。全体に区間順が一桁後半〜二桁で、飛び道具が少ない布陣。"
        )
        notes.append("- 連続出場: 竹下響佑。")
    elif display == "有明" and gender == "女子":
        notes.append(
            "- 2024:13位47:57 → 2025:12位47:24（-33秒）。わずかに改善し順位も+1。"
        )
        notes.append(
            "- 2区は両年とも7:08前後（2024上土井咲輝区間順9、2025溝江杏梨区間順6）。"
            " 短区間の貢献が相対的な強み。"
        )
        notes.append("- 連続出場: 上土井咲輝・杉本琉遙。")
    else:
        if delta is not None:
            notes.append(f"- 前年比総合 {fmt_delta(delta)}、順位 {r24}位 → {r25}位。")
    return notes


def build_overview_section(bundles: dict[tuple[int, str], dict[str, Any]]) -> list[str]:
    lines = [
        "## 大会ハイライト（2024–2025）",
        "",
        "| 年 | 性別 | 優勝 | 総合 | 2位 | 3位 |",
        "|---:|---|---|---:|---|---|",
    ]
    for year in YEARS:
        for gender in GENDERS:
            data = bundles[(year, gender, "raw")]  # type: ignore[index]
            teams = data.get("teams") or []
            top = teams[:3]
            while len(top) < 3:
                top.append({"team": "—", "total": "—"})
            lines.append(
                f"| {year} | {gender} | {top[0].get('team')} | {top[0].get('total')} | "
                f"{top[1].get('team')} {top[1].get('total')} | "
                f"{top[2].get('team')} {top[2].get('total')} |"
            )
    lines.append("")
    lines.append(
        "- 男子コースは2024年以降の現行距離（合計17.71km）。本分析の両年は同一コース時代。"
    )
    lines.append(
        "- 「玉名付属中」は transcript / チーム別 MD では **玉高附属** と表記する。"
    )
    lines.append("")
    return lines


def build_comparison_table(bundles: dict[tuple[int, str], dict[str, Any]]) -> list[str]:
    lines = [
        "## 4校サマリー（前年比）",
        "",
        "| チーム | 性別 | 2024 | 2025 | 総合差 | 順位差 |",
        "|---|---|---|---|---:|---:|",
    ]
    for _display, canonical, _aliases in FOCUS_TEAMS:
        for gender in GENDERS:
            a = bundles[(2024, gender)].get(canonical)
            b = bundles[(2025, gender)].get(canonical)
            if not a or not b:
                continue
            sec_a = parse_time(str(a.get("total")))
            sec_b = parse_time(str(b.get("total")))
            delta = (sec_b - sec_a) if sec_a is not None and sec_b is not None else None
            rank_d = int(a.get("rank") or 0) - int(b.get("rank") or 0)
            lines.append(
                f"| {canonical} | {gender} | {a.get('rank')}位 {a.get('total')} | "
                f"{b.get('rank')}位 {b.get('total')} | "
                f"{fmt_delta(delta) if delta is not None else '—'} | {rank_d:+d} |"
            )
    lines.append("")
    lines.append(
        "※ 総合差は 2025−2024（負＝短縮）。順位差は 2024順位−2025順位（正＝順位上昇）。"
    )
    lines.append("")
    return lines


def build_markdown() -> str:
    bundles: dict[Any, Any] = {}
    for year in YEARS:
        for gender in GENDERS:
            raw = load_year_gender(year, gender)
            bundles[(year, gender)] = team_map(raw)
            bundles[(year, gender, "winner")] = (raw.get("teams") or [{}])[0]
            bundles[(year, gender, "raw")] = raw

    parts: list[str] = [
        "# 荒玉駅伝 2024–2025 深掘り分析（岱明・玉高附属・天水・有明）",
        "",
        "玉名荒尾中体連駅伝（荒玉駅伝）の 2024年・2025年について、",
        "**岱明中・玉名付属中（玉高附属）・天水中・有明中** を中心に区間・前年比・優勝差を整理した。",
        "",
        "## このドキュメントの使い方（Q&A）",
        "",
        "- 「2024/2025の荒玉で岱明はどうだった？」「玉名付属の女子は？」「天水の区間新は？」→ **この分析を優先**。",
        "- 区間選手の全年一覧は `out/analysis/aragyoku-teams/{チーム}.md`。",
        "- 区間距離・ペース換算は `out/analysis/aragyoku-overview.md`。",
        "- 正本データ: `input/aragyoku/transcripts/2024-*.json` / `2025-*.json`。",
        "",
    ]
    parts.extend(build_overview_section(bundles))
    parts.extend(build_comparison_table(bundles))

    for display, canonical, aliases in FOCUS_TEAMS:
        parts.extend(narrative_for(display, canonical, aliases, bundles))

    parts.extend(
        [
            "## 関連ソース",
            "",
            "- `input/aragyoku/transcripts/2024-男子.json` / `2024-女子.json`",
            "- `input/aragyoku/transcripts/2025-男子.json` / `2025-女子.json`",
            "- `out/analysis/aragyoku-teams/岱明.md` / `玉高附属.md` / `天水.md` / `有明.md`",
            "- `out/analysis/aragyoku-overview.md`",
            "- `out/analysis/aragyoku_top2_finish_counts.md`",
            "",
            "生成: `scripts/generate_aragyoku_2024_2025_focus_analysis.py`",
            "",
        ]
    )
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = build_markdown()
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out.relative_to(ROOT)} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
