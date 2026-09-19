#!/usr/bin/env python3
"""Discover→crush bank v3: 未網羅になりやすい質問をコーパスから採掘して 100 問。

重点:
  - 2024–2025 4校深掘り（岱明・玉高附属・天水・有明）
  - meet_records（大会／区間記録）
  - 荒玉チーム別区間選手
  - winners / overview / ranking の言い換え

出力:
  backend/data/eval-gaps/questions-crush100-v3.json
  backend/data/eval-gaps/crush100-v3-rounds.jsonl
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend" / "data" / "eval-gaps" / "questions-crush100-v3.json"
LOG = ROOT / "backend" / "data" / "eval-gaps" / "crush100-v3-rounds.jsonl"
FOCUS = ROOT / "out" / "analysis" / "aragyoku_2024_2025_focus_teams.md"
TEAMS = ROOT / "out" / "analysis" / "aragyoku-teams"
TRANSCRIPTS = ROOT / "input" / "aragyoku" / "transcripts"


def item(qid: str, q: str, any_of: list[str], sources_any: list[str], *, all_of: list[str] | None = None) -> dict:
    expect: dict = {
        "kinds": ["answered", "offline"],
        "any_of": any_of,
        "forbid": ["コーチに直接聞いてください"],
        "sources_any": sources_any,
    }
    if all_of:
        expect["all_of"] = all_of
    return {"id": qid, "q": q, "expect": expect}


def main() -> int:
    qs: list[dict] = []
    log: list[dict] = []
    seen_q: set[str] = set()

    def add(it: dict, theme: str) -> None:
        if len(qs) >= 100:
            return
        if it["q"] in seen_q:
            return
        seen_q.add(it["q"])
        qs.append(it)
        log.append({"round": len(qs), "theme": theme, "id": it["id"], "q": it["q"], "phase": "discover"})

    # --- 1) Focus analysis YoY / ranks / records ---
    focus_text = FOCUS.read_text(encoding="utf-8") if FOCUS.exists() else ""
    # Summary table rows
    for line in focus_text.splitlines():
        m = re.match(
            r"\| (岱明|玉高附属|天水|有明) \| (男子|女子) \| (\d+)位 ([^|]+) \| (\d+)位 ([^|]+) \|",
            line.strip(),
        )
        if not m:
            continue
        school, gender, r24, t24, r25, t25 = (x.strip() for x in m.groups())
        alias = "玉名付属" if school == "玉高附属" else school
        add(
            item(
                f"f_rank25_{school}_{gender}",
                f"2025年荒玉駅伝{gender}の{alias}は何位？",
                [f"{r25}位", t25, school],
                ["aragyoku_2024_2025_focus_teams", f"aragyoku-teams/{school}"],
            ),
            "focus-rank",
        )
        add(
            item(
                f"f_rank24_{school}_{gender}",
                f"2024年荒玉駅伝{gender}の{school}は何位で総合タイムは？",
                [f"{r24}位", t24],
                ["aragyoku_2024_2025_focus_teams", f"aragyoku-teams/{school}"],
            ),
            "focus-rank",
        )
        add(
            item(
                f"f_yoy_{school}_{gender}",
                f"2024から2025で荒玉駅伝{gender}の{alias}はどう変わった？",
                [f"{r24}位", f"{r25}位", t24, t25],
                ["aragyoku_2024_2025_focus_teams", f"aragyoku-teams/{school}"],
            ),
            "focus-yoy",
        )

    # Highlight facts
    facts = [
        (
            "f_daimyo_men_up",
            "2025年荒玉駅伝男子の岱明は前年と比べて何位になった？",
            ["6位", "59:08", "15位"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/岱明"],
        ),
        (
            "f_tensui_record",
            "天水中の荒玉駅伝で区間新を出したのは誰？",
            ["山本悠斗", "8:37"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/天水"],
        ),
        (
            "f_fuzoku_women",
            "玉名付属中の荒玉駅伝女子は2024と2025でどうだった？",
            ["5位", "10位", "43:50", "46:55"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/玉高附属"],
        ),
        (
            "f_ariake_men_rec",
            "2024年荒玉駅伝男子1区の区間新は誰？",
            ["米村和真", "9:01", "有明"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/有明", "transcripts/2024-男子"],
        ),
        (
            "f_fuzoku_kamei",
            "2024年荒玉駅伝男子3区で区間新の玉高附属の選手は？",
            ["亀井遼希", "9:24"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/玉高附属"],
        ),
        (
            "f_fuzoku_kusano",
            "2025年荒玉駅伝男子3区区間1位の玉高附属の選手は？",
            ["草野瑠唯", "9:14"],
            ["aragyoku_2024_2025_focus_teams", "aragyoku-teams/玉高附属"],
        ),
        (
            "f_winner_2025m",
            "2025年荒玉駅伝男子の優勝校は？",
            ["菊水", "56:17"],
            ["aragyoku_2024_2025_focus_teams", "winners-by-year", "transcripts/2025-男子"],
        ),
        (
            "f_winner_2024w",
            "2024年荒玉駅伝女子の優勝校は？",
            ["南関", "42:25"],
            ["aragyoku_2024_2025_focus_teams", "winners-by-year", "transcripts/2024-女子"],
        ),
    ]
    for fid, q, any_of, sources in facts:
        add(item(fid, q, any_of, sources), "focus-fact")

    # --- 2) meet_records from transcripts ---
    for path in sorted(TRANSCRIPTS.glob("*.json")):
        if len(qs) >= 100:
            break
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        year = data.get("year")
        gender = data.get("gender")
        mr = data.get("meet_records") or {}
        if not isinstance(mr, dict) or year is None or gender is None:
            continue
        total = mr.get("total") or {}
        t_time = str(total.get("time") or "").strip()
        t_school = str(total.get("school") or "").strip()
        if t_time and t_school:
            add(
                item(
                    f"mr_total_{year}_{gender[0]}",
                    f"{year}年荒玉駅伝{gender}の大会記録（総合）は？",
                    [t_time, t_school.replace("中", "")],
                    ["meet_records", f"transcripts/{year}-{gender}", "aragyoku/transcripts"],
                ),
                "meet-total",
            )
        for leg in mr.get("legs") or []:
            if not isinstance(leg, dict):
                continue
            leg_n = leg.get("leg")
            leg_time = str(leg.get("time") or "").strip()
            holders = leg.get("holders") or []
            if not leg_n or not leg_time or not holders:
                continue
            h0 = holders[0] if isinstance(holders[0], dict) else {}
            h_name = str(h0.get("name") or "").strip()
            h_school = str(h0.get("school") or "").strip()
            if not h_name:
                continue
            add(
                item(
                    f"mr_leg_{year}_{gender[0]}_{leg_n}",
                    f"{year}年荒玉駅伝{gender}の{leg_n}区の大会区間記録は誰のタイム？",
                    [leg_time, h_name, h_school],
                    ["meet_records", f"transcripts/{year}-{gender}", "aragyoku/transcripts"],
                ),
                "meet-leg",
            )
            if len(qs) >= 100:
                break

    # --- 3) Team digest leg athletes (focus schools + others) ---
    for team in ["岱明", "玉高附属", "天水", "有明", "菊水", "南関", "長洲", "玉名"]:
        path = TEAMS / f"{team}.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        # ## 2025年 男子 ... | 1 | 名前 |
        year = gender = None
        for line in text.splitlines():
            hm = re.match(r"^## (\d{4})年 (男子|女子)", line)
            if hm:
                year, gender = hm.group(1), hm.group(2)
                continue
            lm = re.match(r"\| (\d+) \| ([^|]+) \|", line.strip())
            if not lm or year is None:
                continue
            leg, name = lm.group(1), lm.group(2).strip()
            if name in {"選手", "---"} or name == "unknown":
                continue
            if int(leg) > 2 and team not in {"岱明", "玉高附属", "天水", "有明"}:
                continue
            add(
                item(
                    f"td_{team}_{year}_{gender[0]}_L{leg}",
                    f"{year}年荒玉駅伝{gender}の{team}の{leg}区は誰？",
                    [name, team],
                    [f"aragyoku-teams/{team}", "aragyoku-teams", f"transcripts/{year}-{gender}"],
                ),
                "team-leg",
            )
            if len(qs) >= 100:
                break
        if len(qs) >= 100:
            break

    # --- 4) Distance / pace / overview ---
    overview = (ROOT / "out" / "analysis" / "aragyoku-overview.md").read_text(encoding="utf-8")
    if "17.71" in overview:
        add(
            item(
                "ov_men_dist",
                "荒玉駅伝の男子の総距離（現行）は？",
                ["17.71"],
                ["aragyoku-overview", "aragyoku-ekiden-distance"],
            ),
            "overview",
        )
    if "3:09.1" in overview or "3:09" in overview:
        add(
            item(
                "ov_pace_m2",
                "荒玉駅伝の男子2区を9分でいくとペースは？",
                ["3:09", "2.855"],
                ["aragyoku-overview", "aragyoku-ekiden-distance"],
            ),
            "overview",
        )

    # --- 5) Fill remaining from winners ---
    winners = ROOT / "input" / "idaten-corpus" / "aragyoku" / "winners-by-year.md"
    if winners.exists() and len(qs) < 100:
        for line in winners.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\| (\d{4}) \| (男子|女子) \| ([^|]+) \| ([^|]+) \|", line.strip())
            if not m:
                continue
            year, gender, school, time = (x.strip() for x in m.groups())
            school = school.split()[0]
            add(
                item(
                    f"w_{year}_{gender[0]}",
                    f"{year}年荒玉駅伝{gender}の優勝校とタイムは？",
                    [school, time],
                    ["winners-by-year", "aragyoku"],
                ),
                "winners",
            )
            if len(qs) >= 100:
                break

    bank = {
        "version": 1,
        "total": len(qs),
        "unique": len(qs),
        "defaultYear": 2026,
        "note": "crush100-v3: focus 2024/25 + meet_records + team legs",
        "rounds": [{"id": 1, "theme": "crush100-v3", "questions": qs}],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with LOG.open("w", encoding="utf-8") as f:
        for row in log:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(qs)} questions)")
    themes: dict[str, int] = {}
    for row in log:
        themes[row["theme"]] = themes.get(row["theme"], 0) + 1
    print("themes:", themes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
