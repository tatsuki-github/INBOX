#!/usr/bin/env python3
"""荒玉駅伝の概要 Markdown（区間距離・ペース換算例）を生成する。

正本の距離定義は docs/aragyoku-ekiden-distance-definitions.md と揃える。
出力: out/analysis/aragyoku-overview.md
再生成後は build_idaten_corpus.py で rag_index に載せる。
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "analysis" / "aragyoku-overview.md"

# docs/aragyoku-ekiden-distance-definitions.md と同一
MEN_BEFORE_2024 = {
    1: 3.95,
    2: 3.05,
    3: 2.855,
    4: 2.855,
    5: 3.00,
    6: 4.00,
}
MEN_FROM_2024 = {
    1: 3.00,
    2: 2.855,
    3: 3.00,
    4: 3.00,
    5: 2.855,
    6: 3.00,
}
WOMEN = {
    1: 3.00,
    2: 1.855,
    3: 2.00,
    4: 2.00,
    5: 3.00,
}


def fmt_km(km: float) -> str:
    text = f"{km:.3f}".rstrip("0").rstrip(".")
    return f"{text}km"


def parse_time_to_sec(text: str) -> float:
    parts = text.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return float(parts[0])


def format_pace(sec_per_km: float) -> str:
    total = round(sec_per_km, 1)
    minutes = int(total // 60)
    seconds = total - minutes * 60
    return f"{minutes}:{seconds:04.1f}/km"


def pace_for(distance_km: float, time_text: str) -> str:
    return format_pace(parse_time_to_sec(time_text) / distance_km)


def distance_table(title: str, sections: dict[int, float]) -> str:
    lines = [
        f"### {title}",
        "",
        "| 区間 | 距離 |",
        "|---|---:|",
    ]
    for sec, km in sections.items():
        lines.append(f"| {sec}区 | {fmt_km(km)} |")
    total = sum(sections.values())
    lines.append(f"| 合計 | {fmt_km(total)} |")
    lines.append("")
    return "\n".join(lines)


def pace_examples_table(
    label: str,
    distance_km: float,
    times: list[str],
) -> str:
    lines = [
        f"#### {label}（{fmt_km(distance_km)}）",
        "",
        "| 区間タイム | 平均ペース |",
        "|---:|---:|",
    ]
    for t in times:
        lines.append(f"| {t} | {pace_for(distance_km, t)} |")
    lines.append("")
    return "\n".join(lines)


def build_markdown() -> str:
    men2_new = MEN_FROM_2024[2]
    men2_old = MEN_BEFORE_2024[2]
    women2 = WOMEN[2]
    example_9 = pace_for(men2_new, "9:00")
    example_9_old = pace_for(men2_old, "9:00")

    parts = [
        "# 荒玉駅伝（荒玉中体連駅伝）概要",
        "",
        "荒玉駅伝は、玉名・荒尾地区の中体連駅伝（通称: 荒玉駅伝 / 荒玉中体連駅伝）である。",
        "男子は6区間、女子は5区間。コース距離は年度によって変わる（特に男子は2024年に再編）。",
        "",
        "## このドキュメントの使い方（Q&A）",
        "",
        "- 「区間距離は？」「○区を△分でいくとペースは？」→ **この概要を優先**して答える。",
        "- 年度が無い質問の男子距離は、**現行（2024年以降）**を既定とする。必要なら2023年以前も併記する。",
        "- 優勝校・順位・選手名は優勝校一覧やチーム別記録・文字起こしを使う。",
        "- **2024/2025の岱明・玉高附属（玉名付属）・天水・有明の比較・区間分析** → "
        "`out/analysis/aragyoku_2024_2025_focus_teams.md` を優先。",
        "- コース動画案内・歴代平均ペース分析も参照する。",
        "- 距離の正本はリポジトリの荒玉駅伝区間距離定義に従う。",
        "",
        "## 区間距離",
        "",
        distance_table("男子・2024年以降（現行）", MEN_FROM_2024),
        distance_table("男子・2023年以前", MEN_BEFORE_2024),
        distance_table("女子（全年度共通）", WOMEN),
        "## ペース換算（区間タイム ÷ 区間距離）",
        "",
        "平均ペース（分:秒/km）= 区間タイム（秒）÷ 区間距離（km）。",
        "例: 男子2区（現行 2.855km）を **9:00** で走るとペースは "
        f"**{example_9}**。"
        f" 2023年以前の男子2区（3.05km）なら **{example_9_old}**。",
        "",
        pace_examples_table(
            "男子2区・2024年以降",
            men2_new,
            ["8:00", "8:30", "9:00", "9:30", "10:00", "10:30", "11:00"],
        ),
        pace_examples_table(
            "男子2区・2023年以前",
            men2_old,
            ["8:00", "8:30", "9:00", "9:30", "10:00", "10:30", "11:00"],
        ),
        pace_examples_table(
            "男子1区・2024年以降",
            MEN_FROM_2024[1],
            ["9:00", "9:30", "10:00", "10:30", "11:00"],
        ),
        pace_examples_table(
            "女子2区（全年度）",
            women2,
            ["6:00", "6:30", "7:00", "7:30", "8:00", "9:00"],
        ),
        "## よくある質問への答え方",
        "",
        f"- **Q. 荒玉駅伝の男子2区を9分でいくとペースはどれくらい？**",
        f"  - A. 現行（2024年以降）の男子2区は {fmt_km(men2_new)} なので、9:00 → **{example_9}**。",
        f"    2023年以前なら男子2区 {fmt_km(men2_old)} で 9:00 → **{example_9_old}**。",
        "- **Q. 男子の総距離は？**",
        f"  - A. 現行 {fmt_km(sum(MEN_FROM_2024.values()))}、"
        f"2023年以前 {fmt_km(sum(MEN_BEFORE_2024.values()))}。",
        f"- **Q. 女子の総距離は？** → {fmt_km(sum(WOMEN.values()))}（年度共通）。",
        "",
        "## 関連ソース",
        "",
        "- 区間距離の正本定義（リポジトリ docs の荒玉駅伝区間距離定義）",
        "- 2024–2025 深掘り（岱明・玉高附属・天水・有明）: `aragyoku_2024_2025_focus_teams.md`",
        "- 総合上位の歴代平均ペース分析",
        "- チーム別全年記録（aragyoku-teams）",
        "- 年度別優勝校一覧",
        "- コース動画案内",
        "",
    ]
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT,
        help="output markdown path",
    )
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = build_markdown()
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out.relative_to(ROOT)} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
