#!/usr/bin/env python3
"""Discover hard corpus-grounded questions that currently fail offline Q&A.

Emits questions-crush100-hard.json for eval, and a discover log.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend" / "data" / "eval-gaps" / "questions-crush100-hard.json"


def q(qid: str, text: str, any_of: list[str], sources_any: list[str] | None = None) -> dict:
    e: dict = {
        "kinds": ["answered", "offline"],
        "any_of": any_of,
        "forbid": ["コーチに直接聞いてください"],
    }
    if sources_any:
        e["sources_any"] = sources_any
    return {"id": qid, "q": text, "expect": e}


def main() -> int:
    items: list[dict] = []
    seen: set[str] = set()

    def add(item: dict) -> None:
        if item["q"] in seen:
            return
        seen.add(item["q"])
        items.append(item)

    # Winner times (often truncated / wrong year window)
    winners = (ROOT / "input" / "idaten-corpus" / "aragyoku" / "winners-by-year.md").read_text(
        encoding="utf-8"
    )
    for line in winners.splitlines():
        m = re.match(r"\| (\d{4}) \| (男子|女子) \| ([^|]+) \| ([^|]+) \|", line.strip())
        if not m:
            continue
        year, gender, school, time = (x.strip() for x in m.groups())
        school = school.split()[0]
        add(
            q(
                f"wt_{year}_{gender[0]}",
                f"{year}年荒玉駅伝{gender}の優勝タイムは？",
                [time, school],
                ["winners-by-year"],
            )
        )

    # Top2 counts phrased differently
    top2 = (ROOT / "out" / "analysis" / "aragyoku_top2_finish_counts.md").read_text(encoding="utf-8")
    for line in top2.splitlines():
        m = re.match(r"\| \d+ \| ([^|]+) \| (\d+) \|", line.strip())
        if not m:
            continue
        school, count = m.group(1).strip(), m.group(2).strip()
        if not count.isdigit():
            continue
        add(
            q(
                f"t2b_{school}",
                f"荒玉駅伝で総合2位以内になった回数が多い学校は？{school}は何回？",
                [school, count],
                ["top2_finish_counts"],
            )
        )

    # Notion athlete SB questions (name + distance)
    nr = json.loads((ROOT / "out" / "analysis" / "notion_records_2026.json").read_text(encoding="utf-8"))
    by_key: dict[tuple[str, str], dict] = {}
    for row in nr:
        name = str(row.get("name") or "").strip()
        dist = str(row.get("distance") or "").strip()
        sb = str(row.get("sb_text") or row.get("time_text") or "").strip()
        aff = str(row.get("affiliation") or "").strip()
        if not name or not dist or not sb or not re.match(r"^\d", sb):
            continue
        key = (name, dist)
        prev = by_key.get(key)
        if prev is None or (row.get("sb_adopted") and not prev.get("sb_adopted")):
            by_key[key] = row
    for i, ((name, dist), row) in enumerate(sorted(by_key.items())[:80]):
        sb = str(row.get("sb_text") or row.get("time_text") or "").strip()
        aff = str(row.get("affiliation") or "").strip()
        add(
            q(
                f"nr_{i}_{name}_{dist}",
                f"{name}（{aff}）の{dist}自己ベストは？",
                [name, sb],
                ["notion_records", "arato-tamana-teams", "sb/", "3000m_sb", "1500m_sb"],
            )
        )

    # Team full-record phrasings
    teams_dir = ROOT / "out" / "analysis" / "arato-tamana-teams"
    for path in sorted(teams_dir.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        m = re.search(
            r"\|\s*(?:男子|女子)\s*\|\s*\d+\s*\|\s*([^|]+)\s*\|\s*([0-9:.\-]+)\s*\|",
            text,
        )
        if not m:
            continue
        athlete, mark = m.group(1).strip(), m.group(2).strip()
        team = path.stem
        add(
            q(
                f"tf_{team}",
                f"{team}所属選手の全記録一覧は？",
                [athlete, mark],
                [f"arato-tamana-teams/{path.name}", "arato-tamana-teams"],
            )
        )

    # Ranking position reverse questions
    for rank_path, label, src in [
        (
            "2026_aragyoku_men_3000m_sb_ranking.md",
            "荒玉地区男子3000m",
            "3000m_sb_ranking",
        ),
        (
            "2026_aragyoku_men_1500m_sb_individual_top20.md",
            "荒玉地区男子1500mSB",
            "1500m_sb_individual_top20",
        ),
    ]:
        text = (ROOT / "out" / "analysis" / rank_path).read_text(encoding="utf-8")
        for line in text.splitlines():
            m = re.match(r"\| (\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|", line.strip())
            if not m:
                continue
            rank, name, _team, mark = (x.strip() for x in m.groups())
            if not rank.isdigit() or int(rank) > 8:
                continue
            add(
                q(
                    f"rp_{src}_{rank}",
                    f"{label}で{name}は何位？",
                    [rank, name, mark],
                    [src],
                )
            )

    # Course / distance / pace
    add(
        q(
            "dist_m2",
            "荒玉駅伝男子2区は何キロ？",
            ["2区", "km", "キロ"],
            ["aragyoku-overview", "aragyoku-ekiden-distance"],
        )
    )
    add(
        q(
            "pace_hist",
            "荒玉駅伝の歴代上位平均ペースの表はどこ？2023年の数字は？",
            ["2023", "ペース"],
            ["average_pace", "aragyoku_top6"],
        )
    )

    # Practice / weather / ADR
    add(
        q(
            "trk_len",
            "岱明のトラック1周は何メートル？",
            ["560"],
            ["practice", "daiming"],
        )
    )
    add(
        q(
            "wx",
            "玉名の天気データの保存先と更新方法は？",
            ["Open-Meteo", "weather", "tamana"],
            ["tamana-weather"],
        )
    )
    add(
        q(
            "mana2",
            "高田麻那の1500mSBは？",
            ["5:21.76", "文徳"],
            ["takada-mana", "SBデータベース"],
        )
    )

    # Aragyoku team history
    agy = ROOT / "out" / "analysis" / "aragyoku-teams"
    for path in sorted(agy.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        years = re.findall(r"20\d{2}", text)
        if not years:
            continue
        team = path.stem
        add(
            q(
                f"ah_{team}",
                f"{team}の荒玉駅伝の過去の順位を教えて",
                [team, years[0]],
                [f"aragyoku-teams/{path.name}", "aragyoku-teams"],
            )
        )

    bank = {
        "version": 1,
        "total": len(items),
        "unique": len(items),
        "defaultYear": 2026,
        "note": "Hard crush bank — expect many initial failures for discover/crush loop",
        "rounds": [{"id": 1, "theme": "crush100-hard", "questions": items}],
    }
    OUT.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(items)} questions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
