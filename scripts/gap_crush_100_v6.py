#!/usr/bin/env python3
"""crush100-v6: 学校別PB平均・優勝差・LINE/親・1500m 等の v5 外ギャップを厳格 all_of 100問."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend" / "data" / "eval-gaps" / "questions-crush100-v6.json"
LOG = ROOT / "backend" / "data" / "eval-gaps" / "crush100-v6-rounds.jsonl"
TEAMS = ROOT / "out" / "analysis" / "aragyoku-teams"
WOMEN_RANK = ROOT / "out" / "analysis" / "2026_women_800m_1500m_pb_school_ranking.md"
MEN_RANK = ROOT / "out" / "analysis" / "2026_men_1500m_pb_school_ranking.md"
FOCUS = ROOT / "out" / "analysis" / "aragyoku_2024_2025_focus_teams.md"
SB1500 = ROOT / "out" / "analysis" / "2026_aragyoku_men_1500m_sb_individual_top20.md"


def item(
    qid: str,
    q: str,
    *,
    all_of: list[str],
    sources_any: list[str],
    any_of: list[str] | None = None,
) -> dict:
    expect: dict = {
        "kinds": ["answered", "offline"],
        "all_of": all_of,
        "forbid": ["コーチに直接聞いてください"],
        "sources_any": sources_any,
    }
    if any_of:
        expect["any_of"] = any_of
    return {"id": qid, "q": q, "expect": expect}


def main() -> int:
    qs: list[dict] = []
    log: list[dict] = []
    seen: set[str] = set()

    def add(it: dict, theme: str) -> None:
        if len(qs) >= 100 or it["q"] in seen:
            return
        seen.add(it["q"])
        qs.append(it)
        log.append({"round": len(qs), "theme": theme, "id": it["id"], "q": it["q"]})

    # --- discover gap core (rounds 1–20) ---
    core = [
        (
            "v6_w800_avg",
            "女子800mで岱明の上位3人平均は？",
            ["2:28"],
            ["women_800m_1500m_pb_school_ranking"],
        ),
        (
            "v6_w800_1",
            "女子800m学校別で1位は？",
            ["長洲"],
            ["women_800m_1500m_pb_school_ranking"],
        ),
        (
            "v6_w800_ari",
            "女子800mPB学校別で荒尾三は何位？",
            ["2"],
            ["women_800m_1500m_pb_school_ranking"],
        ),
        (
            "v6_margin_d25",
            "2025年岱明男子の優勝との差は？",
            ["2:51"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/岱明"],
        ),
        (
            "v6_margin_d24",
            "2024年岱明男子の優勝差は？",
            ["8:37"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/岱明"],
        ),
        (
            "v6_margin_phr",
            "岱明男子2025は優勝から何分離れている？",
            ["2:51"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/岱明"],
        ),
        (
            "v6_m1500_1",
            "男子1500m学校別ランキング1位は？",
            ["玉陵"],
            ["men_1500m_pb_school_ranking"],
        ),
        (
            "v6_m1500_d",
            "男子1500m上位4人平均で岱明は何位？",
            ["5"],
            ["men_1500m_pb_school_ranking"],
        ),
        (
            "v6_sb1500_1",
            "荒玉地区1500mSBの1位は誰？",
            ["隈部", "4:11"],
            ["1500m_sb_individual_top20"],
        ),
        (
            "v6_sb1500_2",
            "荒玉地区1500mトップ20の2位は？",
            ["石川", "4:15"],
            ["1500m_sb_individual_top20"],
        ),
        (
            "v6_arita_m",
            "有田先輩のメンタルの考え方は？",
            ["楽しさ", "本気度"],
            ["arita-taisho", "line-chats"],
        ),
        (
            "v6_arita_r",
            "有田先輩の補強メニューは？",
            ["手押し車", "犬歩き"],
            ["arita-taisho", "line-chats"],
        ),
        (
            "v6_43",
            "女子荒玉のタイム目安は？",
            ["43分"],
            ["arita-taisho", "line-chats"],
        ),
        (
            "v6_mat",
            "銀マットの厚みは？",
            ["15"],
            ["line-chats", "daiming-parents"],
        ),
        (
            "v6_goudou",
            "玉名市合同練習会はいつどこ？",
            ["おおはま"],
            ["line-chats", "daiming-parents"],
        ),
        (
            "v6_fee",
            "合同練習会の会費は？",
            ["1000"],
            ["line-chats", "daiming-parents"],
        ),
        (
            "v6_nagomi",
            "なごみ駅伝の集合場所は？",
            ["和水"],
            ["line-chats"],
        ),
        (
            "v6_c_pt",
            "地点分担で熊澤先生はどこ？",
            ["C地点"],
            ["line-chats", "daiming-staff"],
        ),
        (
            "v6_b_pt",
            "地点分担で土本先生はどこ？",
            ["B地点"],
            ["line-chats", "daiming-staff"],
        ),
        (
            "v6_murakami",
            "村上咲稀の800mPBは？",
            ["2:20"],
            ["women_800m_1500m_pb_school_ranking", "SB"],
        ),
    ]
    for fid, q, all_of, sources in core:
        add(item(fid, q, all_of=all_of, sources_any=sources), "core-gap")

    # --- women 800m school averages from ranking table ---
    if WOMEN_RANK.exists():
        section = False
        for line in WOMEN_RANK.read_text(encoding="utf-8").splitlines():
            if "800m・上位3人平均" in line:
                section = True
                continue
            if section and line.startswith("## ") and "800m" not in line:
                break
            m = re.match(
                r"\| (\d+) \| ([^|]+) \| \d+ \| ([0-9:]+) \|",
                line.strip(),
            )
            if not m or not section:
                continue
            rank, school, avg = m.group(1), m.group(2).strip().replace("中", ""), m.group(3)
            add(
                item(
                    f"v6_w800_r{rank}",
                    f"女子800m上位3人平均で{school}は何位？平均は？",
                    all_of=[f"{rank}位" if False else rank, avg[:4]],  # use avg prefix
                    sources_any=["women_800m_1500m_pb_school_ranking"],
                ),
                "w800-rank",
            )
            # Fix: all_of should be school-identifying avg + rank carefully
            qs[-1]["expect"]["all_of"] = [avg[:4], school[:2] if len(school) >= 2 else school]
            if len(qs) >= 35:
                break

    # --- men 1500 school averages ---
    if MEN_RANK.exists():
        section = False
        for line in MEN_RANK.read_text(encoding="utf-8").splitlines():
            if "上位4人平均" in line and line.startswith("##"):
                section = True
                continue
            if section and line.startswith("## ") and "上位4" not in line:
                break
            m = re.match(
                r"\| (\d+) \| ([^|]+) \| \d+ \| ([0-9:]+) \|",
                line.strip(),
            )
            if not m or not section:
                continue
            rank, school, avg = m.group(1), m.group(2).strip().replace("中", ""), m.group(3)
            add(
                item(
                    f"v6_m1500_r{rank}_{school}",
                    f"男子1500m上位4人平均で{school}の平均は？",
                    all_of=[avg[:4]],
                    sources_any=["men_1500m_pb_school_ranking"],
                ),
                "m1500-rank",
            )
            if len(qs) >= 50:
                break

    # --- focus winner margins ---
    if FOCUS.exists():
        school = None
        gender = None
        for line in FOCUS.read_text(encoding="utf-8").splitlines():
            sm = re.match(r"^## (岱明|玉高附属|天水|有明)", line)
            if sm:
                school = sm.group(1)
                continue
            gm = re.match(r"^### (男子|女子)", line)
            if gm and school:
                gender = gm.group(1)
                continue
            rm = re.match(
                r"\| (2024|2025) \| (\d+)位 \| ([0-9:]+) \| \+?([0-9:.]+) \|",
                line.strip(),
            )
            if not rm or not school or not gender:
                continue
            year, _rank, _total, margin = rm.groups()
            margin_s = margin.rstrip("0").rstrip(".") if "." in margin else margin
            # keep + prefix style from doc: +2:51.00 → need 2:51
            core_m = re.match(r"(\d+:\d+)", margin)
            if not core_m:
                continue
            mtime = core_m.group(1)
            add(
                item(
                    f"v6_mg_{school}_{year}_{gender[0]}",
                    f"{year}年{school}{gender}の優勝との差は？",
                    all_of=[mtime],
                    sources_any=[
                        "aragyoku_2024_2025_focus_teams",
                        f"aragyoku-teams/{school}",
                    ],
                ),
                "winner-margin",
            )
            if len(qs) >= 70:
                break

    # --- 1500m individual top ---
    if SB1500.exists():
        for line in SB1500.read_text(encoding="utf-8").splitlines():
            m = re.match(
                r"\| (\d+) \| ([^|]+) \| ([^|]+) \| ([0-9:.]+) \|",
                line.strip(),
            )
            if not m:
                continue
            rank, name, _aff, t = m.groups()
            name, t = name.strip(), t.strip()
            add(
                item(
                    f"v6_1500_{rank}",
                    f"荒玉地区1500mSBの{rank}位は誰？記録は？",
                    all_of=[name[:2], t[:4]],
                    sources_any=["1500m_sb_individual_top20"],
                ),
                "sb1500",
            )
            if len(qs) >= 85:
                break

    # --- short leg regression (v5 gap) ---
    for team in ["岱明", "天水", "有明"]:
        path = TEAMS / f"{team}.md"
        if not path.exists():
            continue
        year = gender = None
        for line in path.read_text(encoding="utf-8").splitlines():
            if len(qs) >= 100:
                break
            hm = re.match(r"^## (2024|2025)年 (男子|女子)", line)
            if hm:
                year, gender = hm.group(1), hm.group(2)
                continue
            lm = re.match(r"\| ([1-6]) \| ([^|]+) \|", line.strip())
            if not lm or year is None:
                continue
            leg, name = lm.group(1), lm.group(2).strip()
            if name in {"選手", "unknown", "---"}:
                continue
            add(
                item(
                    f"v6_leg_{team}_{year}_{gender[0]}_L{leg}",
                    f"{year}年{team}{gender}{leg}区は誰？",
                    all_of=[name],
                    sources_any=[f"aragyoku-teams/{team}", "aragyoku_2024_2025_focus_teams"],
                ),
                "short-leg",
            )

    bank = {
        "version": 1,
        "total": len(qs),
        "unique": len(qs),
        "defaultYear": 2026,
        "note": "crush100-v6: school PB avg + winner margin + LINE/parents + 1500m",
        "rounds": [{"id": 1, "theme": "crush100-v6", "questions": qs}],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with LOG.open("w", encoding="utf-8") as f:
        for row in log:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    themes: dict[str, int] = {}
    for row in log:
        themes[row["theme"]] = themes.get(row["theme"], 0) + 1
    print(f"wrote {OUT.relative_to(ROOT)} ({len(qs)}) themes={themes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
