#!/usr/bin/env python3
"""Discover corpus-grounded Q&A gaps and emit an eval bank of 100+ cases.

Each emitted question has expect anchors mined from the repo so offline
eval can prove the answer came from corpus (not coach-redirect).
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_BANK = ROOT / "backend" / "data" / "eval-gaps" / "questions-crush100.json"
OUT_LOG = ROOT / "backend" / "data" / "eval-gaps" / "crush100-discover-log.jsonl"


def _forbid_coach() -> list[str]:
    return ["コーチに直接聞いてください"]


def _q(
    qid: str,
    q: str,
    *,
    any_of: list[str] | None = None,
    all_of: list[str] | None = None,
    sources_any: list[str] | None = None,
    kinds: list[str] | None = None,
) -> dict:
    expect: dict = {
        "kinds": kinds or ["answered", "offline"],
        "forbid": _forbid_coach(),
    }
    if any_of:
        expect["any_of"] = any_of
    if all_of:
        expect["all_of"] = all_of
    if sources_any:
        expect["sources_any"] = sources_any
    return {"id": qid, "q": q, "expect": expect}


def from_winners() -> list[dict]:
    path = ROOT / "input" / "idaten-corpus" / "aragyoku" / "winners-by-year.md"
    if not path.exists():
        return []
    out: list[dict] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        m = re.match(
            r"\| (\d{4}) \| (男子|女子) \| ([^|]+) \| ([^|]+) \|",
            line.strip(),
        )
        if not m:
            continue
        year, gender, school, time = (x.strip() for x in m.groups())
        school = school.split()[0]
        time = time.strip()
        if not school or school in {"優勝校", "---"}:
            continue
        out.append(
            _q(
                f"w{year}{gender[0]}{i}",
                f"{year}年荒玉駅伝{gender}の優勝校は？",
                any_of=[school, time],
                sources_any=["winners-by-year", "aragyoku"],
            )
        )
    return out


def from_top2() -> list[dict]:
    path = ROOT / "out" / "analysis" / "aragyoku_top2_finish_counts.md"
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| \d+ \| ([^|]+) \| (\d+) \|", line.strip())
        if not m:
            continue
        school, count = m.group(1).strip(), m.group(2).strip()
        if school in {"学校", "---"} or not count.isdigit():
            continue
        out.append(
            _q(
                f"t2_{school}_{count}",
                f"荒玉駅伝で{school}が2位までに入った回数は？",
                all_of=[school, count],
                sources_any=["top2_finish_counts"],
            )
        )
    return out


def from_3000_ranking() -> list[dict]:
    path = ROOT / "out" / "analysis" / "2026_aragyoku_men_3000m_sb_ranking.md"
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(
            r"\| (\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|",
            line.strip(),
        )
        if not m:
            continue
        rank, name, team, mark = (x.strip() for x in m.groups())
        if not rank.isdigit() or name in {"選手", "---"}:
            continue
        if int(rank) == 1:
            out.append(
                _q(
                    "r3000_1",
                    "荒玉地区で3000mが一番速いのは誰？",
                    any_of=[name, mark],
                    sources_any=["3000m_sb_ranking"],
                )
            )
        if int(rank) <= 5:
            out.append(
                _q(
                    f"r3000_{rank}",
                    f"荒玉地区男子3000m SBランキングで{rank}位は誰？",
                    any_of=[name, mark],
                    sources_any=["3000m_sb_ranking"],
                )
            )
    return out


def from_1500_top20() -> list[dict]:
    path = ROOT / "out" / "analysis" / "2026_aragyoku_men_1500m_sb_individual_top20.md"
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(
            r"\| (\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|",
            line.strip(),
        )
        if not m:
            continue
        rank, name, _team, mark = (x.strip() for x in m.groups())
        if not rank.isdigit() or name in {"選手", "---"}:
            continue
        if int(rank) <= 10:
            out.append(
                _q(
                    f"r1500_{rank}",
                    f"今年の荒玉地区男子1500mSBランキング{rank}位は？",
                    any_of=[name, mark],
                    sources_any=["1500m_sb_individual_top20"],
                )
            )
    return out


def from_team_digests() -> list[dict]:
    d = ROOT / "out" / "analysis" / "arato-tamana-teams"
    if not d.is_dir():
        return []
    out: list[dict] = []
    for path in sorted(d.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        # First athlete+mark in a table row
        m = re.search(
            r"\|[^|]*\|\s*\d+\s*\|\s*([^|]+)\s*\|\s*([0-9:.\-DNS]+)\s*\|",
            text,
        )
        if not m:
            continue
        athlete, mark = m.group(1).strip(), m.group(2).strip()
        if athlete in {"選手", "---"} or mark in {"記録", "---"}:
            continue
        team = path.stem
        out.append(
            _q(
                f"team_{team}",
                f"{team}の選手の記録を教えて",
                any_of=[athlete, mark, team.replace("中", "")],
                sources_any=[f"arato-tamana-teams/{path.name}", "arato-tamana-teams"],
            )
        )
    return out


def from_sb_sample(limit: int = 40) -> list[dict]:
    path = ROOT / "input" / "idaten-corpus" / "sb" / "中学生SB.csv"
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            name = (row.get("名前") or "").strip()
            if not name or len(name) < 2:
                continue
            # Prefer middle-school-ish or local affiliation tokens for relevance
            aff = (row.get("所属") or "").strip()
            mark = ""
            dist = ""
            for col, label in (
                ("1500mSB", "1500m"),
                ("3000mSB", "3000m"),
                ("800mSB", "800m"),
                ("5000mSB", "5000m"),
            ):
                v = (row.get(col) or "").strip()
                if v and re.match(r"^\d+:\d+", v):
                    mark = v
                    dist = label
                    break
            if not mark:
                continue
            if i % 5 != 0:
                continue
            # Prefer 荒玉地区 schools when possible, else accept any
            out.append(
                _q(
                    f"sb_{i}_{name}",
                    f"{name}の{dist}自己ベストは？",
                    any_of=[name, mark],
                    sources_any=["sb/", "中学生SB", "SBデータベース"],
                )
            )
            if len(out) >= limit:
                break
    return out


def from_line_chats() -> list[dict]:
    specs = [
        (
            "line-chats/daiming-staff.md",
            "岱明の朝練の集合時間は？",
            ["7:20", "7時20", "朝練"],
        ),
        (
            "line-chats/arita-taisho.md",
            "有田先輩の補強メニューの考え方は？",
            ["手押し車", "犬歩き", "補強", "分割走"],
        ),
        (
            "line-chats/daiming-parents.md",
            "銀マットのサイズは？",
            ["マット", "銀", "合同"],
        ),
    ]
    out: list[dict] = []
    for src, q, any_of in specs:
        path = ROOT / "out" / "analysis" / src
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        anchors = [a for a in any_of if a in text] or any_of[:1]
        out.append(
            _q(
                f"line_{Path(src).stem}",
                q,
                any_of=anchors,
                sources_any=[src, "line-chats"],
            )
        )
    return out


def from_overview_pace() -> list[dict]:
    out: list[dict] = []
    overview = ROOT / "out" / "analysis" / "aragyoku-overview.md"
    if overview.exists():
        text = overview.read_text(encoding="utf-8", errors="replace")
        if "2区" in text or "区間" in text:
            out.append(
                _q(
                    "ov_dist",
                    "荒玉駅伝の男子2区の距離は？",
                    any_of=["2区", "km", "区間"],
                    sources_any=["aragyoku-overview", "aragyoku-ekiden-distance"],
                )
            )
    pace = ROOT / "out" / "analysis" / "aragyoku_top6_historical_average_pace.md"
    if pace.exists():
        text = pace.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"\| 2025 \|[^|]*\|", text)
        if m:
            out.append(
                _q(
                    "pace_2025",
                    "2025年荒玉駅伝の上位平均ペースは？",
                    any_of=["2025", "ペース", "/km", "分"],
                    sources_any=["average_pace", "aragyoku_top6"],
                )
            )
    return out


def from_weather_ops() -> list[dict]:
    path = ROOT / "docs" / "tamana-weather.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    anchors = []
    for a in ["Open-Meteo", "weather", "1時間", "玉名", "forecast"]:
        if a in text:
            anchors.append(a)
    return [
        _q(
            "wx_ops",
            "玉名の天気データはどう更新する？",
            any_of=anchors or ["Open-Meteo"],
            sources_any=["tamana-weather"],
        )
    ]


def from_takada() -> list[dict]:
    path = ROOT / "out" / "analysis" / "athletes" / "takada-mana.md"
    if not path.exists():
        return []
    return [
        _q(
            "mana",
            "高田麻那の記録",
            any_of=["5:21.76", "11:05.84", "文徳"],
            sources_any=["takada-mana", "SBデータベース"],
        )
    ]


def from_school_rankings() -> list[dict]:
    out: list[dict] = []
    for name, q in [
        (
            "2026_men_1500m_pb_school_ranking.md",
            "荒玉地区の男子1500m学校別ランキングは？",
        ),
        (
            "2026_women_800m_1500m_pb_school_ranking.md",
            "荒玉地区の女子800m・1500m学校別ランキングは？",
        ),
    ]:
        path = ROOT / "out" / "analysis" / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"\| 1 \| ([^|]+) \|", text)
        school = m.group(1).strip() if m else "岱明"
        out.append(
            _q(
                f"sch_{name[:12]}",
                q,
                any_of=[school, "順位", "記録"],
                sources_any=[name.replace(".md", ""), "pb_school_ranking"],
            )
        )
    return out


def from_aragyoku_teams() -> list[dict]:
    d = ROOT / "out" / "analysis" / "aragyoku-teams"
    if not d.is_dir():
        return []
    out: list[dict] = []
    for path in sorted(d.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        team = path.stem
        # look for a year result
        m = re.search(r"(20\d{2}).{0,40}(\d+位|順位)", text)
        year = m.group(1) if m else "2025"
        out.append(
            _q(
                f"agy_{team}",
                f"荒玉駅伝の{team}の歴代成績は？",
                any_of=[team, year, "位"],
                sources_any=[f"aragyoku-teams/{path.name}", "aragyoku-teams"],
            )
        )
    return out


def main() -> int:
    pools = [
        ("winners", from_winners()),
        ("top2", from_top2()),
        ("3000", from_3000_ranking()),
        ("1500", from_1500_top20()),
        ("teams", from_team_digests()),
        ("sb", from_sb_sample(35)),
        ("line", from_line_chats()),
        ("overview", from_overview_pace()),
        ("weather", from_weather_ops()),
        ("mana", from_takada()),
        ("school", from_school_rankings()),
        ("agy_teams", from_aragyoku_teams()),
    ]
    seen_q: set[str] = set()
    questions: list[dict] = []
    log_rows: list[dict] = []
    round_id = 1
    for theme, items in pools:
        for item in items:
            key = item["q"]
            if key in seen_q:
                continue
            seen_q.add(key)
            questions.append(item)
            log_rows.append(
                {
                    "round": len(questions),
                    "theme": theme,
                    "id": item["id"],
                    "q": item["q"],
                    "phase": "discover",
                }
            )
            if len(questions) >= 100:
                break
        if len(questions) >= 100:
            break

    # pad if short
    while len(questions) < 100 and from_winners():
        # shouldn't happen often
        break

    bank = {
        "version": 1,
        "total": len(questions),
        "unique": len(questions),
        "defaultYear": 2026,
        "note": "100 discover/crush corpus-grounded gap bank (auto-mined)",
        "rounds": [
            {
                "id": round_id,
                "theme": "crush100",
                "questions": questions[:100],
            }
        ],
    }
    OUT_BANK.parent.mkdir(parents=True, exist_ok=True)
    OUT_BANK.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_LOG.open("w", encoding="utf-8") as f:
        for row in log_rows[:100]:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {OUT_BANK} ({len(questions[:100])} questions)")
    print(f"wrote {OUT_LOG}")
    for theme, items in pools:
        print(f"  {theme}: {len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
