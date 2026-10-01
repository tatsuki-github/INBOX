#!/usr/bin/env python3
"""Generate coach-oriented analysis prepared FAQ from out/analysis facts (ADR 059).

Covers year-over-year focus teams, bottleneck/best legs, winner gaps, 区間新,
top-2 finish counts, trial phrasing, formula short-name asks, and SB school ranks.
Answers are grounded only in analysis markdown/CSV facts (no invented numbers).

Usage:
  python3 scripts/generate_prepared_qa_coach_analysis.py --dry-run
  python3 scripts/generate_prepared_qa_coach_analysis.py
  python3 scripts/generate_prepared_qa_coach_analysis.py && python3 scripts/sync_prepared_qa.py
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import entry  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
FOCUS = ROOT / "out" / "analysis" / "aragyoku_2024_2025_focus_teams.md"
TOP2 = ROOT / "out" / "analysis" / "aragyoku_top2_finish_counts.md"
LEG_AWARDS = ROOT / "out" / "analysis" / "aragyoku_leg_awards.md"
SB1500 = ROOT / "out" / "analysis" / "2026_men_1500m_pb_school_ranking.md"
SB3000 = ROOT / "out" / "analysis" / "2026_aragyoku_men_3000m_sb_ranking.md"
FORMULA_MEN = ROOT / "out" / "analysis" / "aragyoku_2026_formula_男子.csv"
FORMULA_WOMEN = ROOT / "out" / "analysis" / "aragyoku_2026_formula_女子.csv"
ID_PREFIX = "coach-analysis-"

TEAM_ALIASES = {
    "岱明": ["岱明", "岱明中", "いだてん岱明"],
    "玉高附属": ["玉高附属", "玉名付属", "玉名附属", "玉名附中", "付属"],
    "天水": ["天水", "天水中"],
    "有明": ["有明", "有明中"],
}


def load_faq() -> dict:
    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise SystemExit("invalid FAQ yaml")
    return data


def upsert(existing: list[dict], new_entries: list[dict]) -> tuple[int, int]:
    by_id = {e["id"]: i for i, e in enumerate(existing)}
    claimed = {q for e in existing for q in (e.get("questions") or [])}
    added = updated = 0
    for e in new_entries:
        eid = e["id"]
        # drop questions claimed by other ids
        qs = []
        for q in e["questions"]:
            if q in claimed and (eid not in by_id or q not in (existing[by_id[eid]].get("questions") or [])):
                continue
            qs.append(q)
            claimed.add(q)
        if not qs:
            continue
        e["questions"] = qs
        if eid in by_id:
            # merge questions into existing
            old = existing[by_id[eid]]
            merged_q = list(old.get("questions") or [])
            for q in qs:
                if q not in merged_q:
                    merged_q.append(q)
            old["questions"] = merged_q
            old["answer"] = e["answer"]
            old["sources"] = e["sources"]
            tags = list(old.get("tags") or [])
            for t in e.get("tags") or []:
                if t not in tags:
                    tags.append(t)
            old["tags"] = tags
            updated += 1
        else:
            existing.append(e)
            by_id[eid] = len(existing) - 1
            added += 1
    return added, updated


def patch_existing_questions(entries: list[dict]) -> int:
    """Add coach phrasings to known analysis ids without changing answers."""
    extras: dict[str, list[str]] = {
        "aragyoku-daiming-yoy": [
            "2024と2025の荒玉で岱明はどうだった？",
            "岱明の前年比は？",
            "岱明男子と女子の前年比は？",
            "去年と一昨年の岱明の荒玉比較は？",
        ],
        "focus-teams-2024-2025": [
            "2024と2025の荒玉で岱明・玉名付属・天水・有明はどうだった？",
            "深掘り4校の前年比は？",
            "フォーカス4校の分析は？",
        ],
        "aragyoku-top2-counts": [
            "どの学校が2位以内が多い？",
            "荒玉で2位以内が多い学校は？",
            "歴代で2位以内が多いのはどこ？",
            "総合2位以内の回数ランキングは？",
        ],
        "trial-2026-daiming-aragyoku": [
            "岱明の試走タイムは？",
            "岱明の試走結果は？",
            "荒玉試走で岱明はどうだった？",
            "9/29岱明の試走は？",
        ],
        "aragyoku-trial-20260929": [
            "試走の結果を分析して",
        ],
        "formula-2026-男子-岱明中-order": [
            "岱明男子の2026区間予想は？",
            "岱明男子の数式予想は？",
            "今年の岱明男子オーダー予想は？",
            "岱明の2026男子区間予想",
        ],
        "formula-2026-女子-岱明中-order": [
            "岱明女子の2026区間予想は？",
            "岱明女子の数式予想は？",
            "今年の岱明女子オーダー予想は？",
        ],
        "aragyoku-winner-pace": [
            "上位校の平均ペースは？",
            "優勝校の平均ペースは？",
            "2025年荒玉男子優勝の平均ペースは？",
        ],
    }
    claimed = {q for e in entries for q in (e.get("questions") or [])}
    n = 0
    by_id = {e["id"]: e for e in entries}
    for eid, qs in extras.items():
        e = by_id.get(eid)
        if not e:
            continue
        cur = list(e.get("questions") or [])
        for q in qs:
            if q in cur:
                continue
            if q in claimed:
                continue
            cur.append(q)
            claimed.add(q)
            n += 1
        e["questions"] = cur
    return n


def parse_focus_blocks(text: str) -> list[dict]:
    """Parse per-team/gender blocks from focus markdown."""
    blocks: list[dict] = []
    # Split by ## team headers (skip first sections)
    parts = re.split(r"\n##\s+", text)
    for part in parts[1:]:
        header, _, body = part.partition("\n")
        team_m = re.match(r"(.+?)（transcript", header)
        if not team_m:
            continue
        team = team_m.group(1).strip()
        for gm in re.finditer(
            r"\n###\s+(男子|女子)\s*\n(.*?)(?=\n###\s+(?:男子|女子)|\n##\s+|\Z)",
            "\n" + body,
            re.S,
        ):
            gender = gm.group(1)
            gbody = gm.group(2)
            # year table rows
            years = {}
            for ym in re.finditer(
                r"\|\s*(2024|2025)\s*\|\s*(\d+)位\s*\|\s*([0-9:]+)\s*\|\s*([+\-][0-9:.]+)\s*\|\s*(.+?)\s*\|",
                gbody,
            ):
                years[ym.group(1)] = {
                    "rank": int(ym.group(2)),
                    "total": ym.group(3),
                    "gap": ym.group(4),
                    "winner": ym.group(5).strip(),
                }
            yoy = re.search(
                r"\*\*前年比総合\*\*:\s*([+\-][0-9:.]+s?|[+\-][0-9:]+(?:\.\d+)?)"
                r".*?順位\s*(\d+)位\s*→\s*(\d+)位.*?([+\-]\d+)",
                gbody,
            )
            consec = re.search(r"\*\*連続出場（氏名一致）\*\*:\s*(.+)", gbody)
            # per-year best/worst from bullet under each year section
            best = {}
            worst = {}
            records = {}
            for year in ("2024", "2025"):
                # find section after #### {year}年
                sm = re.search(
                    rf"####\s*{year}年.*?(?=####\s*202|\n####\s*読み取り|\Z)",
                    gbody,
                    re.S,
                )
                if not sm:
                    continue
                sec = sm.group(0)
                bm = re.search(
                    r"区間順位ベスト:\s*(\d+)区\s*(.+?)\s*（区間順\s*(\d+)・([0-9:]+)）",
                    sec,
                )
                wm = re.search(
                    r"区間順位ワースト:\s*(\d+)区\s*(.+?)\s*（区間順\s*(\d+)・([0-9:]+)）",
                    sec,
                )
                if bm:
                    best[year] = {
                        "leg": int(bm.group(1)),
                        "name": bm.group(2).strip(),
                        "rank": int(bm.group(3)),
                        "time": bm.group(4),
                    }
                if wm:
                    worst[year] = {
                        "leg": int(wm.group(1)),
                        "name": wm.group(2).strip(),
                        "rank": int(wm.group(3)),
                        "time": wm.group(4),
                    }
                rm = re.findall(
                    r"\*\*区間新\*\*:\s*(\d+)区\s*(.+?)\s*([0-9:]+)",
                    sec,
                )
                if rm:
                    records[year] = [
                        {"leg": int(a), "name": b.strip(), "time": c} for a, b, c in rm
                    ]
            if not years:
                continue
            blocks.append(
                {
                    "team": team,
                    "gender": gender,
                    "years": years,
                    "yoy_delta": yoy.group(1) if yoy else None,
                    "yoy_rank_from": int(yoy.group(2)) if yoy else None,
                    "yoy_rank_to": int(yoy.group(3)) if yoy else None,
                    "yoy_rank_delta": yoy.group(4) if yoy else None,
                    "consecutive": [x.strip() for x in consec.group(1).split(",")]
                    if consec
                    else [],
                    "best": best,
                    "worst": worst,
                    "records": records,
                }
            )
    return blocks


def aliases_for(team: str) -> list[str]:
    return TEAM_ALIASES.get(team, [team, team + "中"])


def gen_focus_entries(blocks: list[dict]) -> list[dict]:
    out: list[dict] = []
    src = ["out/analysis/aragyoku_2024_2025_focus_teams.md"]
    for b in blocks:
        team, gender = b["team"], b["gender"]
        y24, y25 = b["years"].get("2024"), b["years"].get("2025")
        if not (y24 and y25):
            continue
        aliases = aliases_for(team)
        # YoY summary
        delta = b["yoy_delta"] or "?"
        rd = b["yoy_rank_delta"] or "?"
        ans = (
            f"{team}の荒玉駅伝{gender}前年比（2024→2025）です。"
            f" {y24['rank']}位 {y24['total']} → {y25['rank']}位 {y25['total']}"
            f"（総合差 {delta}、順位変動 {rd}）。"
            f" 2025の優勝との差は {y25['gap']}（優勝 {y25['winner']}）。"
        )
        qs = []
        for a in aliases:
            qs.extend(
                [
                    f"{a}{gender}の前年比は？",
                    f"{a}の荒玉{gender}前年比は？",
                    f"2024と2025の{a}{gender}はどうだった？",
                    f"{a}{gender}の2024-2025分析は？",
                ]
            )
        qs.append(f"荒玉駅伝{gender}の{team}前年比")
        out.append(
            entry(
                f"{ID_PREFIX}yoy-{team}-{gender}",
                qs,
                ans,
                src,
                ["aragyoku", "analysis", "yoy", "coach", gender, team, 2024, 2025],
            )
        )
        # bottleneck (worst leg 2025 preferred, else 2024)
        for year in ("2025", "2024"):
            w = b["worst"].get(year)
            if not w:
                continue
            ans_w = (
                f"{year}年荒玉駅伝{gender}・{team}の区間順位ワーストは"
                f"{w['leg']}区 {w['name']}（区間順 {w['rank']}・{w['time']}）です。"
            )
            qs_w = []
            for a in aliases:
                qs_w.extend(
                    [
                        f"{year}年{a}{gender}のボトルネック区間は？",
                        f"{a}{gender}の{year}年ワースト区間は？",
                    ]
                )
            if year == "2025":
                for a in aliases:
                    qs_w.append(f"{a}{gender}のボトルネック区間は？")
            out.append(
                entry(
                    f"{ID_PREFIX}worst-{year}-{team}-{gender}",
                    qs_w,
                    ans_w,
                    src,
                    ["aragyoku", "analysis", "coach", gender, team, int(year)],
                )
            )
            break
        # best leg 2025
        best = b["best"].get("2025")
        if best:
            ans_b = (
                f"2025年荒玉駅伝{gender}・{team}の区間順位ベストは"
                f"{best['leg']}区 {best['name']}（区間順 {best['rank']}・{best['time']}）です。"
            )
            qs_b = []
            for a in aliases:
                qs_b.extend(
                    [
                        f"2025年{a}{gender}で一番よかった区間は？",
                        f"{a}{gender}の2025年ベスト区間は？",
                        f"{a}{gender}の強みの区間は？（2025）",
                    ]
                )
            out.append(
                entry(
                    f"{ID_PREFIX}best-2025-{team}-{gender}",
                    qs_b,
                    ans_b,
                    src,
                    ["aragyoku", "analysis", "coach", gender, team, 2025],
                )
            )
        # winner gap 2025
        ans_g = (
            f"2025年荒玉駅伝{gender}・{team}の優勝との差は {y25['gap']} です"
            f"（優勝 {y25['winner']}、{team}は {y25['rank']}位 {y25['total']}）。"
        )
        qs_g = []
        for a in aliases:
                qs_g.extend(
                    [
                        f"{a}{gender}の優勝との差は？",
                        f"2025年{a}{gender}の優勝差は？",
                        f"{a}{gender}は優勝からどれくらい？",
                    ]
                )
        if team == "岱明" and gender == "男子":
            qs_g.extend(
                [
                    "2025年荒玉男子の優勝差（岱明）は？",
                    "2025年荒玉男子で岱明の優勝差は？",
                    "荒玉男子岱明の優勝との差（2025）",
                ]
            )
        out.append(
            entry(
                f"{ID_PREFIX}gap-2025-{team}-{gender}",
                qs_g,
                ans_g,
                src,
                ["aragyoku", "analysis", "coach", gender, team, 2025],
            )
        )
        # consecutive
        if b["consecutive"]:
            names = "、".join(b["consecutive"])
            ans_c = (
                f"{team}の荒玉駅伝{gender}で2024→2025に連続出場（氏名一致）したのは"
                f"{names}です。"
            )
            qs_c = []
            for a in aliases:
                qs_c.extend(
                    [
                        f"連続出場した{a}{gender}は？",
                        f"{a}{gender}の連続出場メンバーは？",
                        f"{a}{gender}で両年出た選手は？",
                    ]
                )
            out.append(
                entry(
                    f"{ID_PREFIX}consec-{team}-{gender}",
                    qs_c,
                    ans_c,
                    src,
                    ["aragyoku", "analysis", "coach", gender, team],
                )
            )
        # 区間新
        for year, recs in b["records"].items():
            for r in recs:
                ans_r = (
                    f"{year}年荒玉駅伝{gender}・{team}の区間新は"
                    f"{r['leg']}区 {r['name']} {r['time']} です。"
                )
                qs_r = []
                for a in aliases:
                    qs_r.extend(
                        [
                            f"{year}年{a}{gender}の区間新は？",
                            f"{a}の{year}年{gender}区間新",
                        ]
                    )
                if team == "天水" and year == "2025" and gender == "男子":
                    qs_r.append("天水の区間新は？")
                    qs_r.append("天水男子の区間新は？")
                out.append(
                    entry(
                        f"{ID_PREFIX}record-{year}-{team}-{gender}-leg{r['leg']}",
                        qs_r,
                        ans_r,
                        src,
                        ["aragyoku", "analysis", "coach", "record", gender, team, int(year)],
                    )
                )
    return out


def gen_biggest_improver(blocks: list[dict]) -> list[dict]:
    """Among focus blocks, largest rank improvement (positive yoy_rank_delta)."""
    scored = []
    for b in blocks:
        if b["yoy_rank_delta"] is None:
            continue
        try:
            d = int(b["yoy_rank_delta"])
        except ValueError:
            continue
        scored.append((d, b))
    if not scored:
        return []
    scored.sort(key=lambda x: -x[0])
    d, b = scored[0]
    y24, y25 = b["years"]["2024"], b["years"]["2025"]
    ans = (
        f"2024→2025の深掘り4校で順位上昇が最も大きいのは"
        f"{b['team']}{b['gender']}です（{y24['rank']}位→{y25['rank']}位、順位変動 {d:+d}、"
        f"総合 {y24['total']}→{y25['total']}）。"
    )
    return [
        entry(
            f"{ID_PREFIX}biggest-improver-2024-2025",
            [
                "2024から2025で一番伸びたのはどの校？",
                "前年比で最も順位が上がったのは？",
                "深掘り4校で一番伸びたのは？",
                "2024-2025で最も改善したチームは？",
            ],
            ans,
            ["out/analysis/aragyoku_2024_2025_focus_teams.md"],
            ["aragyoku", "analysis", "coach", "yoy", 2024, 2025],
        )
    ]


def gen_highlights(text: str) -> list[dict]:
    rows = re.findall(
        r"\|\s*(2024|2025)\s*\|\s*(男子|女子)\s*\|\s*(.+?)\s*\|\s*([0-9:]+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|",
        text,
    )
    if not rows:
        return []
    bits = []
    for y, g, w, tot, second, third in rows:
        bits.append(f"{y}{g}優勝{w.strip()}（{tot}）／2位{second.strip()}／3位{third.strip()}")
    ans = "荒玉駅伝2024–2025の大会ハイライトです。 " + "。 ".join(bits) + "。"
    return [
        entry(
            f"{ID_PREFIX}highlights-2024-2025",
            [
                "2024と2025の荒玉の優勝校は？",
                "荒玉2024-2025の大会ハイライトは？",
                "直近2年の荒玉優勝と2位3位は？",
            ],
            ans,
            ["out/analysis/aragyoku_2024_2025_focus_teams.md"],
            ["aragyoku", "analysis", "coach", 2024, 2025],
        )
    ]


def gen_top2_detail() -> list[dict]:
    if not TOP2.exists():
        return []
    text = TOP2.read_text(encoding="utf-8")
    rows = re.findall(
        r"\|\s*\d+\s*\|\s*(.+?)\s*\|\s*(\d+)\s*\|",
        text.split("## 男子のみ")[0],
    )
    if not rows:
        return []
    top = rows[:5]
    ans = (
        "荒玉駅伝（2012–2025）で総合2位以内の回数が多い学校は、"
        + "、".join(f"{t}{n}回" for t, n in top)
        + "です。"
    )
    # per-school count asks
    out = [
        entry(
            f"{ID_PREFIX}top2-overview",
            [
                "どの学校が2位以内が多い？",
                "荒玉で2位以内が多い学校は？",
                "歴代2位以内回数の上位は？",
            ],
            ans,
            ["out/analysis/aragyoku_top2_finish_counts.md"],
            ["aragyoku", "analysis", "coach", "top2"],
        )
    ]
    for team, n in rows:
        aliases = aliases_for(team) if team in TEAM_ALIASES else [team, team + "中"]
        qs = [f"{a}は荒玉で2位以内何回？" for a in aliases]
        qs.append(f"{team}の2位以内回数は？")
        out.append(
            entry(
                f"{ID_PREFIX}top2-{team}",
                qs,
                f"{team}は荒玉駅伝（2012–2025・男女合算）で総合2位以内が{n}回です。",
                ["out/analysis/aragyoku_top2_finish_counts.md"],
                ["aragyoku", "analysis", "coach", "top2", team],
            )
        )
    return out


def gen_leg_award_coach() -> list[dict]:
    if not LEG_AWARDS.exists():
        return []
    text = LEG_AWARDS.read_text(encoding="utf-8")
    out: list[dict] = []
    # 2025 men awards from narrative lines
    for m in re.finditer(
        r"(2025)年荒玉駅伝(男子|女子)の(\d+)区区間賞は(.+?)・([0-9:]+)",
        text,
    ):
        year, gender, leg, who, t = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        ans = f"{year}年荒玉駅伝{gender}の{leg}区区間賞は{who}・{t}です。"
        out.append(
            entry(
                f"{ID_PREFIX}legaward-{year}-{gender}-leg{leg}",
                [
                    f"{year}年{gender}{leg}区の区間賞は誰？",
                    f"{year}年荒玉{gender}{leg}区の区間賞",
                    f"{year}荒玉{gender}{leg}区区間賞は？",
                ],
                ans,
                ["out/analysis/aragyoku_leg_awards.md"],
                ["aragyoku", "analysis", "coach", "leg-award", gender, int(year)],
            )
        )
        if len(out) >= 20:
            break
    return out


def gen_sb_school_ranks() -> list[dict]:
    out: list[dict] = []
    if SB1500.exists():
        text = SB1500.read_text(encoding="utf-8")
        # top4 average table first rows
        rows = re.findall(
            r"\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*\d+\s*\|\s*([0-9:.]+)\s*\|",
            text.split("## 上位6人平均")[0],
        )
        if rows:
            top3 = rows[:3]
            ans = (
                "2026年度在籍・男子1500m PBの学校別（上位4人平均）では、"
                + "、".join(f"{r}位{s}（平均{a}）" for r, s, a in top3)
                + f"。岱明中は"
                + next((f"{r}位（平均{a}）" for r, s, a in rows if "岱明" in s), "圏外")
                + "です。"
            )
            out.append(
                entry(
                    f"{ID_PREFIX}sb1500-school-rank",
                    [
                        "1500mの学校別ランキングは？",
                        "男子1500mの学校ランキングは？",
                        "荒玉地区の1500m学校別は？",
                        "1500m上位校はどこ？",
                        "岱明の1500m学校順位は？",
                    ],
                    ans,
                    ["out/analysis/2026_men_1500m_pb_school_ranking.md"],
                    ["aragyoku", "analysis", "coach", "sb", 2026],
                )
            )
    if SB3000.exists():
        text = SB3000.read_text(encoding="utf-8")
        # take first individual ranking lines if table-like
        rows = re.findall(
            r"\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*([0-9:.]+)",
            text,
        )
        if rows:
            top = rows[:5]
            ans = (
                "荒玉地区男子3000m SBランキング（2026年度登録ベース）の上位は、"
                + "、".join(f"{r}位{name}（{school}）{t}" for r, name, school, t in top)
                + "です。"
            )
            out.append(
                entry(
                    f"{ID_PREFIX}sb3000-rank",
                    [
                        "荒玉地区の3000mランキングは？",
                        "男子3000mのSBランキングは？",
                        "3000m上位は誰？",
                        "3000mの地区ランキングを教えて",
                    ],
                    ans,
                    ["out/analysis/2026_aragyoku_men_3000m_sb_ranking.md"],
                    ["aragyoku", "analysis", "coach", "sb", 2026],
                )
            )
    return out


def gen_formula_shortnames() -> list[dict]:
    """Add short-school-name formula overview for focus teams if CSV present."""
    out: list[dict] = []
    for gender, path in (("男子", FORMULA_MEN), ("女子", FORMULA_WOMEN)):
        if not path.exists():
            continue
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        by_team: dict[str, list[dict]] = {}
        for r in rows:
            team = (r.get("team") or r.get("school") or "").strip()
            if not team:
                continue
            by_team.setdefault(team, []).append(r)
        for team_key in ("岱明中", "岱明"):
            rows_t = by_team.get(team_key) or by_team.get("岱明中") or []
            if not rows_t:
                continue
            bits = []
            total = 0.0
            complete = True
            for r in sorted(rows_t, key=lambda x: int(x.get("leg") or 0)):
                leg = r.get("leg")
                name = r.get("name") or "?"
                t = r.get("formula_time") or "?"
                bits.append(f"{leg}区{name}（予想{t}）")
                try:
                    total += float(r.get("formula_sec") or 0)
                except ValueError:
                    complete = False
            if not bits:
                continue
            mins, secs = divmod(int(round(total)), 60) if complete and total else (0, 0)
            total_s = f"{mins}:{secs:02d}" if complete and total else "（区間欠あり）"
            ans = (
                f"2026年荒玉駅伝{gender}・岱明の数式予想（仮オーダー含む）です。"
                f" 合計目安 {total_s}。 " + "、".join(bits) + "。"
                " 断定順位ではなく、直近レース観測に基づく説明可能な予想です。"
            )
            out.append(
                entry(
                    f"{ID_PREFIX}formula-2026-{gender}-岱明",
                    [
                        f"岱明{gender}の2026区間予想は？",
                        f"岱明{gender}の数式予想は？",
                        f"今年の岱明{gender}オーダー予想は？",
                        f"岱明の2026{gender}区間予想",
                    ],
                    ans,
                    [str(path.relative_to(ROOT)), "out/analysis/aragyoku_2026_formula_report.md"],
                    ["aragyoku", "analysis", "coach", "formula", gender, 2026],
                )
            )
            break
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = load_faq()
    entries: list[dict] = data["entries"]
    before = len(entries)

    patched = patch_existing_questions(entries)
    print(f"patched questions on existing ids: {patched}")

    focus_text = FOCUS.read_text(encoding="utf-8") if FOCUS.exists() else ""
    blocks = parse_focus_blocks(focus_text) if focus_text else []
    print(f"parsed focus blocks: {len(blocks)}")

    new_entries: list[dict] = []
    new_entries.extend(gen_focus_entries(blocks))
    new_entries.extend(gen_biggest_improver(blocks))
    new_entries.extend(gen_highlights(focus_text))
    new_entries.extend(gen_top2_detail())
    new_entries.extend(gen_leg_award_coach())
    new_entries.extend(gen_sb_school_ranks())
    new_entries.extend(gen_formula_shortnames())

    # remove old coach-analysis-* then upsert fresh
    kept = [e for e in entries if not str(e.get("id") or "").startswith(ID_PREFIX)]
    removed = before - len(kept)
    added, updated = upsert(kept, new_entries)
    data["entries"] = kept
    data["total"] = len(kept)

    print(f"removed old {ID_PREFIX}*: {removed}")
    print(f"new coach-analysis entries generated: {len(new_entries)}")
    print(f"upserted added={added} updated={updated} total={len(kept)}")

    if args.dry_run:
        # show sample ids
        for e in new_entries[:8]:
            print(" sample", e["id"], e["questions"][:2], "=>", e["answer"][:80].replace("\n", " "))
        print("dry-run: not writing")
        return 0

    FAQ.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    print(f"wrote {FAQ}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
