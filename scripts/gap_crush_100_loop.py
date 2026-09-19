#!/usr/bin/env python3
"""
Discover→crush loop for corpus Q&A gaps.

For each of up to 100 rounds:
  1. Mine a grounded question from corpus digests
  2. Record discover
  3. (Eval happens in TS; this script builds the bank of 100 crush targets)

Targets are athlete rows from each team digest + ranking rows + winners —
phrasings chosen to stress preferred-source routing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend" / "data" / "eval-gaps" / "questions-crush100-loop.json"
LOG = ROOT / "backend" / "data" / "eval-gaps" / "crush100-rounds.jsonl"


def item(qid: str, q: str, any_of: list[str], sources_any: list[str]) -> dict:
    return {
        "id": qid,
        "q": q,
        "expect": {
            "kinds": ["answered", "offline"],
            "any_of": any_of,
            "forbid": ["コーチに直接聞いてください"],
            "sources_any": sources_any,
        },
    }


def main() -> int:
    qs: list[dict] = []
    log: list[dict] = []

    def add(it: dict, theme: str) -> None:
        if len(qs) >= 100:
            return
        qs.append(it)
        log.append(
            {
                "round": len(qs),
                "theme": theme,
                "id": it["id"],
                "q": it["q"],
                "phase": "discover",
            }
        )

    # Team athlete rows (many previously routed to wrong digest / README)
    teams = ROOT / "out" / "analysis" / "arato-tamana-teams"
    for path in sorted(teams.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        team = path.stem
        rows = list(
            re.finditer(
                r"\|\s*(男子|女子)\s*\|\s*(\d+)\s*\|\s*([^|]+)\s*\|\s*([0-9]+\d*:\d{2}(?:\.\d+)?)\s*\|",
                text,
            )
        )
        for i, m in enumerate(rows[:5]):
            name, mark = m.group(3).strip(), m.group(4).strip()
            add(
                item(
                    f"c_team_{team}_{i}",
                    f"{team}所属選手の全記録一覧は？",
                    [name, mark],
                    [f"arato-tamana-teams/{path.name}"],
                ),
                "team-full",
            )
            add(
                item(
                    f"c_ath_{team}_{i}",
                    f"{team}の{name}の記録は？",
                    [name, mark],
                    [f"arato-tamana-teams/{path.name}", "arato-tamana-teams"],
                ),
                "team-athlete",
            )
            if len(qs) >= 100:
                break
        if len(qs) >= 100:
            break

    # Ranking positions
    for fname, label, src in [
        ("2026_aragyoku_men_3000m_sb_ranking.md", "荒玉地区男子3000m", "3000m_sb_ranking"),
        (
            "2026_aragyoku_men_1500m_sb_individual_top20.md",
            "荒玉地区男子1500mSB",
            "1500m_sb_individual_top20",
        ),
    ]:
        text = (ROOT / "out" / "analysis" / fname).read_text(encoding="utf-8")
        for line in text.splitlines():
            m = re.match(r"\| (\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|", line.strip())
            if not m:
                continue
            rank, name, _t, mark = (x.strip() for x in m.groups())
            if not rank.isdigit():
                continue
            add(
                item(
                    f"c_rank_{src}_{rank}",
                    f"{label}で{name}は何位？",
                    [rank, name, mark],
                    [src],
                ),
                "rank-pos",
            )
            if len(qs) >= 100:
                break
        if len(qs) >= 100:
            break

    # Top2 school counts
    top2 = (ROOT / "out" / "analysis" / "aragyoku_top2_finish_counts.md").read_text(
        encoding="utf-8"
    )
    for line in top2.splitlines():
        m = re.match(r"\| \d+ \| ([^|]+) \| (\d+) \|", line.strip())
        if not m:
            continue
        school, count = m.group(1).strip(), m.group(2).strip()
        if not count.isdigit():
            continue
        add(
            item(
                f"c_t2_{school}",
                f"荒玉駅伝で{school}が2位までに入った回数は何回？",
                [school, count],
                ["top2_finish_counts"],
            ),
            "top2",
        )
        if len(qs) >= 100:
            break

    bank = {
        "version": 1,
        "total": len(qs),
        "unique": len(qs),
        "defaultYear": 2026,
        "note": "100 discover/crush loop targets (team/rank/top2)",
        "rounds": [{"id": 1, "theme": "crush100-loop", "questions": qs}],
    }
    OUT.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with LOG.open("w", encoding="utf-8") as f:
        for row in log:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} ({len(qs)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
