#!/usr/bin/env python3
"""厳格な crush100-v4: all_of で偽陽性を防ぎ、未網羅を炙り出す。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend" / "data" / "eval-gaps" / "questions-crush100-v4.json"
LOG = ROOT / "backend" / "data" / "eval-gaps" / "crush100-v4-rounds.jsonl"
FOCUS = ROOT / "out" / "analysis" / "aragyoku_2024_2025_focus_teams.md"
MEET_MD = ROOT / "out" / "analysis" / "aragyoku_meet_records.md"
TEAMS = ROOT / "out" / "analysis" / "aragyoku-teams"
TRANSCRIPTS = ROOT / "input" / "aragyoku" / "transcripts"


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

    # Focus ranks (strict)
    for line in FOCUS.read_text(encoding="utf-8").splitlines() if FOCUS.exists() else []:
        m = re.match(
            r"\| (岱明|玉高附属|天水|有明) \| (男子|女子) \| (\d+)位 ([^|]+) \| (\d+)位 ([^|]+) \|",
            line.strip(),
        )
        if not m:
            continue
        school, gender, r24, t24, r25, t25 = (x.strip() for x in m.groups())
        alias = "玉名付属" if school == "玉高附属" else f"{school}"
        add(
            item(
                f"v4_r25_{school}_{gender}",
                f"2025年荒玉駅伝{gender}の{alias}は何位？総合タイムは？",
                all_of=[f"{r25}位", t25],
                sources_any=["aragyoku_2024_2025_focus_teams", f"aragyoku-teams/{school}"],
            ),
            "focus",
        )
        add(
            item(
                f"v4_r24_{school}_{gender}",
                f"2024年荒玉駅伝{gender}の{school}は何位？",
                all_of=[f"{r24}位", t24],
                sources_any=["aragyoku_2024_2025_focus_teams", f"aragyoku-teams/{school}"],
            ),
            "focus",
        )

    facts = [
        (
            "v4_tensui_sr",
            "天水中の荒玉駅伝で区間新を出したのは誰でタイムは？",
            ["山本悠斗", "8:37"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/天水"],
        ),
        (
            "v4_daimyo_up",
            "岱明男子は2024から2025で何位から何位になった？",
            ["15位", "6位", "59:08"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/岱明"],
        ),
        (
            "v4_fuzoku_w",
            "玉名付属の荒玉女子は2024何位から2025何位？",
            ["5位", "10位"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/玉高附属"],
        ),
        (
            "v4_ariake_rec",
            "2024年荒玉男子1区で区間新の有明の選手は？",
            ["米村和真", "9:01"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/有明"],
        ),
        (
            "v4_kusano",
            "2025年荒玉男子3区区間1位の玉高附属は誰？",
            ["草野瑠唯", "9:14"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/玉高附属"],
        ),
        (
            "v4_kamei",
            "2024年荒玉男子3区区間新の玉高附属は誰？",
            ["亀井遼希", "9:24"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/玉高附属"],
        ),
    ]
    for fid, q, all_of, sources in facts:
        add(item(fid, q, all_of=all_of, sources_any=sources), "focus-fact")

    # Team legs 2024/2025 focus + top schools
    for team in ["岱明", "玉高附属", "天水", "有明", "菊水", "南関"]:
        path = TEAMS / f"{team}.md"
        if not path.exists():
            continue
        year = gender = None
        for line in path.read_text(encoding="utf-8").splitlines():
            hm = re.match(r"^## (2024|2025)年 (男子|女子)", line)
            if hm:
                year, gender = hm.group(1), hm.group(2)
                continue
            lm = re.match(r"\| ([123]) \| ([^|]+) \|", line.strip())
            if not lm or year is None:
                continue
            leg, name = lm.group(1), lm.group(2).strip()
            if name in {"選手", "unknown", "---"}:
                continue
            add(
                item(
                    f"v4_leg_{team}_{year}_{gender[0]}_L{leg}",
                    f"{year}年荒玉駅伝{gender}の{team}の{leg}区は誰？",
                    all_of=[name],
                    sources_any=[f"aragyoku-teams/{team}", f"transcripts/{year}-{gender}"],
                ),
                "team-leg",
            )
            if len(qs) >= 70:
                break
        if len(qs) >= 70:
            break

    # Meet records — prefer recent years, require name+time
    for path in sorted(TRANSCRIPTS.glob("*.json"), reverse=True):
        if len(qs) >= 100:
            break
        data = json.loads(path.read_text(encoding="utf-8"))
        year, gender = data.get("year"), data.get("gender")
        mr = data.get("meet_records")
        if not isinstance(mr, dict) or year is None:
            continue
        # skip very old if we already have enough; prioritize 2020+
        if int(year) < 2018 and len(qs) > 85:
            continue
        total = mr.get("total") or {}
        t_time = str(total.get("time") or "")
        t_school = str(total.get("school") or "").replace("中", "")
        if t_time and t_school:
            add(
                item(
                    f"v4_mr_t_{year}_{gender[0]}",
                    f"{year}年荒玉駅伝{gender}の総合大会記録（ボード上部）は何分でどこの学校？",
                    all_of=[t_time, t_school],
                    sources_any=["aragyoku_meet_records", f"transcripts/{year}-{gender}"],
                ),
                "meet-total",
            )
        for leg in (mr.get("legs") or [])[:3]:
            if not isinstance(leg, dict):
                continue
            holders = leg.get("holders") or []
            if not holders or not isinstance(holders[0], dict):
                continue
            h_name = str(holders[0].get("name") or "")
            h_school = str(holders[0].get("school") or "")
            leg_time = str(leg.get("time") or "")
            if not h_name or not leg_time:
                continue
            add(
                item(
                    f"v4_mr_l_{year}_{gender[0]}_{leg.get('leg')}",
                    f"{year}年荒玉駅伝{gender}の{leg.get('leg')}区の大会区間記録は誰？タイムは？",
                    all_of=[h_name, leg_time],
                    sources_any=["aragyoku_meet_records", f"transcripts/{year}-{gender}"],
                ),
                "meet-leg",
            )
            if len(qs) >= 100:
                break

    # Distance (strict)
    add(
        item(
            "v4_dist_m4",
            "荒玉駅伝の現行男子4区の距離は何km？",
            all_of=["3"],
            any_of=["3km", "3.00", "3.0"],
            sources_any=["aragyoku-overview", "aragyoku-ekiden-distance"],
        ),
        "overview",
    )
    add(
        item(
            "v4_pace_m2",
            "荒玉駅伝の男子2区を9分でいくとペースは？",
            all_of=["3:09"],
            sources_any=["aragyoku-overview", "aragyoku-ekiden-distance"],
        ),
        "overview",
    )

    bank = {
        "version": 1,
        "total": len(qs),
        "unique": len(qs),
        "defaultYear": 2026,
        "note": "crush100-v4 strict all_of: focus+meet_records+team legs",
        "rounds": [{"id": 1, "theme": "crush100-v4", "questions": qs}],
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
