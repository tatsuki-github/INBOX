#!/usr/bin/env python3
"""crush100-v5: short 「○区は誰」phrasing + legs 4–6 + LINE非衝突の厳格 all_of 100問."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend" / "data" / "eval-gaps" / "questions-crush100-v5.json"
LOG = ROOT / "backend" / "data" / "eval-gaps" / "crush100-v5-rounds.jsonl"
FOCUS = ROOT / "out" / "analysis" / "aragyoku_2024_2025_focus_teams.md"
TEAMS = ROOT / "out" / "analysis" / "aragyoku-teams"
TRANSCRIPTS = ROOT / "input" / "aragyoku" / "transcripts"
TOP2 = ROOT / "out" / "analysis" / "aragyoku_top2_finish_counts.md"
MEET_MD = ROOT / "out" / "analysis" / "aragyoku_meet_records.md"


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

    # --- Rounds 1–40: short 「年+校+性別+区は誰」 (v4 に無い短縮形 / 4–6区) ---
    for team in ["岱明", "玉高附属", "天水", "有明", "菊水", "南関", "荒尾三", "玉陵"]:
        path = TEAMS / f"{team}.md"
        if not path.exists():
            continue
        year = gender = None
        for line in path.read_text(encoding="utf-8").splitlines():
            hm = re.match(r"^## (2024|2025)年 (男子|女子)", line)
            if hm:
                year, gender = hm.group(1), hm.group(2)
                continue
            lm = re.match(r"\| ([1-6]) \| ([^|]+) \|", line.strip())
            if not lm or year is None:
                continue
            leg, name = lm.group(1), lm.group(2).strip()
            if name in {"選手", "unknown", "---"} or "区" in name:
                continue
            # Short phrasing without 「荒玉駅伝」— the discover gap
            add(
                item(
                    f"v5_short_{team}_{year}_{gender[0]}_L{leg}",
                    f"{year}年{team}{gender}{leg}区は誰？",
                    all_of=[name],
                    sources_any=[
                        f"aragyoku-teams/{team}",
                        "aragyoku_2024_2025_focus_teams",
                        f"transcripts/{year}-{gender}",
                        f"ekiden-ocr/{year}-{gender}",
                    ],
                ),
                "short-leg",
            )
            if len(qs) >= 40:
                break
        if len(qs) >= 40:
            break

    # --- Rounds 41–55: 岱明 LINE非衝突の言い回しバリエーション ---
    daimyo_facts = [
        ("v5_d_5", "2025年岱明男子5区は誰？", ["山本哲瑠"], "岱明"),
        ("v5_d_2", "2025年岱明男子2区は誰？", ["松野凛空"], "岱明"),
        ("v5_d_1", "2025年岱明男子1区は誰？", ["倉田裕斗"], "岱明"),
        ("v5_d_4", "2025年岱明男子4区は誰？", ["佐藤央琉"], "岱明"),
        ("v5_d_6", "2025年岱明男子6区は誰？", ["案浦竜士"], "岱明"),
        ("v5_d_5b", "岱明男子5区は誰？（2025）", ["山本哲瑠"], "岱明"),
        ("v5_d_5c", "2025岱明5区誰", ["山本哲瑠"], "岱明"),
        ("v5_d_best", "2025年岱明男子の区間順位ベストは誰？", ["山本哲瑠"], "岱明"),
        ("v5_d_24_4", "2024年岱明男子4区の区間タイムは？", ["田上侑蕾", "14:55"], "岱明"),
        ("v5_line_ok", "荒玉の地点分担で土山はどこ？", ["D地点"], "line-chats"),
        ("v5_line_dist", "荒玉男子2区と5区の距離は？", ["2.855"], "line-chats"),
        ("v5_tensui", "2025年天水男子2区は誰？", ["山本悠斗"], "天水"),
        ("v5_ariake", "2024年有明男子1区は誰？", ["米村和真"], "有明"),
        ("v5_fuzoku", "2025年玉高附属男子3区は誰？", ["草野瑠唯"], "玉高附属"),
        ("v5_imamura", "今村昇磨は2025年荒玉で何区？", ["3区", "今村昇磨"], "岱明"),
    ]
    for fid, q, all_of, src in daimyo_facts:
        sources = (
            ["line-chats"]
            if src == "line-chats"
            else [f"aragyoku-teams/{src}", "aragyoku_2024_2025_focus_teams"]
        )
        add(item(fid, q, all_of=all_of, sources_any=sources), "daimyo-variants")

    # --- Rounds 56–70: top2 / pace / historical winners ---
    hist = [
        ("v5_top2", "荒玉で総合2位以内が最多の学校は？何回？", ["玉名", "15"], ["top2_finish_counts"]),
        ("v5_top2_d", "岱明が荒玉で総合2位以内に入ったのは何回？", ["1"], ["top2_finish_counts"]),
        ("v5_pace", "荒玉男子トップ6の歴代平均ペースは？", ["3:18"], ["average_pace"]),
        ("v5_w23", "2023年荒玉男子の優勝校は？", ["菊水"], ["winners-by-year", "aragyoku-teams/菊水"]),
        ("v5_w22", "2022年荒玉女子の優勝校は？", ["長洲"], ["winners-by-year", "aragyoku-teams/長洲"]),
        ("v5_w20", "2020年荒玉男子の優勝校は？", ["玉南"], ["winners-by-year", "aragyoku-teams/玉南"]),
        ("v5_w19", "2019年荒玉男子2位は？", ["玉東"], ["winners-by-year", "top2_finish_counts"]),
        ("v5_mr12", "2012年荒玉男子の総合大会記録は？", ["63:28", "荒尾海陽"], ["aragyoku_meet_records"]),
        ("v5_mr17", "2017年荒玉男子の総合大会記録の保持校は？", ["62:53", "菊水"], ["aragyoku_meet_records"]),
        ("v5_mr13", "2013年荒玉男子1区の大会区間記録保持者は？", ["田上建", "12:12"], ["aragyoku_meet_records"]),
        ("v5_mr_w2", "女子2区の大会区間記録の保持者は？", ["井上智世", "6:08"], ["aragyoku_meet_records"]),
        ("v5_mr24", "2024年荒玉男子総合の大会記録は？", ["56:38", "南関"], ["aragyoku_meet_records"]),
        ("v5_mr25_3", "2025年荒玉男子3区の大会区間記録は誰？", ["亀井遼希", "9:24"], ["aragyoku_meet_records"]),
        ("v5_dist", "現行コースの荒玉男子合計距離は？", ["17.71"], ["aragyoku-overview", "aragyoku-ekiden-distance"]),
        ("v5_old", "旧コースの荒玉男子合計距離は？", ["19.71"], ["aragyoku-overview", "aragyoku-ekiden-distance"]),
    ]
    for fid, q, all_of, sources in hist:
        add(item(fid, q, all_of=all_of, sources_any=sources), "history")

    # --- Rounds 71–85: SB / athlete / focus YoY ---
    sb = [
        ("v5_sb1", "荒玉地区3000mSBの1位の記録は？", ["8:54"], ["3000m_sb_ranking"]),
        ("v5_sb2", "松浦眞大の3000mSBは？", ["9:08"], ["3000m_sb_ranking", "SB"]),
        ("v5_sb3", "草野瑠唯の3000mSBは？", ["9:28"], ["3000m_sb_ranking", "SB"]),
        ("v5_mana", "高田麻那の1500mSBは？", ["5:21"], ["takada-mana", "SBデータベース"]),
        ("v5_yoy_d", "岱明男子は前年比何分速くなった？", ["6:07"], ["focus_teams", "aragyoku-teams/岱明"]),
        ("v5_yoy_f", "玉高附属女子は前年比何分遅くなった？", ["3:05"], ["focus_teams", "aragyoku-teams/玉高附属"]),
        ("v5_ari_w", "有明女子は2024から2025で何秒速くなった？", ["33"], ["focus_teams", "aragyoku-teams/有明"]),
        ("v5_kik", "2025年菊水男子の総合タイムは？", ["56:17"], ["aragyoku-teams/菊水", "focus_teams"]),
        ("v5_nan", "2024年南関女子の総合タイムは？", ["42:25"], ["aragyoku-teams/南関", "focus_teams"]),
        ("v5_gyu", "2025年玉東女子は何位？", ["3位", "44:24"], ["aragyoku-teams/玉東", "focus_teams"]),
        ("v5_fuz_w", "2025年玉高附属女子の総合タイムは？", ["46:55"], ["aragyoku-teams/玉高附属", "focus_teams"]),
        ("v5_ten_m", "2025年天水男子総合は？", ["63:39"], ["aragyoku-teams/天水", "focus_teams"]),
        ("v5_ari_m", "2025年有明男子総合は？", ["62:31"], ["aragyoku-teams/有明", "focus_teams"]),
        ("v5_kamei", "亀井遼希は何区で大会区間記録？", ["亀井遼希", "3区"], ["aragyoku_meet_records", "玉高附属"]),
        ("v5_nishi", "西川侑里の女子1区大会区間記録は？", ["9:46"], ["aragyoku_meet_records"]),
    ]
    for fid, q, all_of, sources in sb:
        add(item(fid, q, all_of=all_of, sources_any=sources), "sb-focus")

    # --- Fill to 100 from remaining team legs (short form, all 1–6) ---
    for team in ["岱明", "玉高附属", "天水", "有明", "菊水", "南関", "荒尾三", "玉名", "長洲"]:
        if len(qs) >= 100:
            break
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
                    f"v5_fill_{team}_{year}_{gender[0]}_L{leg}",
                    f"{year}年荒玉 {team}{gender}{leg}区の選手は？",
                    all_of=[name],
                    sources_any=[f"aragyoku-teams/{team}", f"ekiden-ocr/{year}-{gender}"],
                ),
                "fill-leg",
            )

    bank = {
        "version": 1,
        "total": len(qs),
        "unique": len(qs),
        "defaultYear": 2026,
        "note": "crush100-v5: short leg-who phrasing + LINE non-collision + history",
        "rounds": [{"id": 1, "theme": "crush100-v5", "questions": qs}],
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
