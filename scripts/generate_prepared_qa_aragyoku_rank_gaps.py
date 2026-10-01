#!/usr/bin/env python3
"""Generate aragyoku rank-to-rank time-gap prepared FAQ.

Covers questions like 「去年の荒玉駅伝の男子の2位と3位の差は？」.

Usage:
  python3 scripts/generate_prepared_qa_aragyoku_rank_gaps.py
  python3 scripts/generate_prepared_qa_aragyoku_rank_gaps.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import entry, load_years  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
MEN_FULL = ROOT / "input" / "idaten-corpus" / "aragyoku" / "men_full_2012_2025.json"
WOMEN_FULL = ROOT / "input" / "idaten-corpus" / "aragyoku" / "women_full_2012_2025.json"
ID_PREFIX = "aragyoku-rankgap-"
DEFAULT_YEAR = 2026
# Adjacent gaps for all ranks + winner vs 2..5
MAX_WINNER_VS = 5


def parse_clock(text: str) -> int | None:
    t = (text or "").strip().replace("．", ".")
    m = re.fullmatch(r"(?:(\d+):)?(\d{1,2}):(\d{2})", t)
    if not m:
        return None
    h = int(m.group(1) or 0)
    mi = int(m.group(2))
    s = int(m.group(3))
    return h * 3600 + mi * 60 + s


def fmt_gap(sec: int) -> str:
    if sec < 0:
        sec = -sec
    if sec < 60:
        return f"{sec}秒"
    m, s = divmod(sec, 60)
    if m < 60:
        return f"{m}分{s:02d}秒" if s else f"{m}分"
    h, m = divmod(m, 60)
    if s:
        return f"{h}時間{m}分{s:02d}秒"
    return f"{h}時間{m}分"


def ranked_teams(yd: dict) -> list[dict]:
    teams = list(yd.get("teams") or [])
    out = []
    for t in teams:
        try:
            rank = int(t.get("rank"))
        except (TypeError, ValueError):
            continue
        total = str(t.get("total") or t.get("time") or "").strip()
        name = str(t.get("team") or t.get("name") or "").strip()
        if not name or not total or parse_clock(total) is None:
            continue
        out.append({"rank": rank, "team": name, "total": total})
    out.sort(key=lambda x: x["rank"])
    # unique by rank
    seen: set[int] = set()
    uniq = []
    for t in out:
        if t["rank"] in seen:
            continue
        seen.add(t["rank"])
        uniq.append(t)
    return uniq


def pair_questions(year: int, gender: str, a: int, b: int) -> list[str]:
    qs = [
        f"{year}年荒玉駅伝{gender}の{a}位と{b}位の差は？",
        f"{year}年荒玉駅伝{gender}の{a}位と{b}位のタイム差",
        f"{year}年荒玉{gender}の{a}位と{b}位の差",
        f"{year}年の荒玉{gender}{a}位と{b}位の差は？",
        f"荒玉駅伝{year}年{gender}の{a}位と{b}位の差",
    ]
    if a == 1 and b == 2:
        qs.extend(
            [
                f"{year}年荒玉駅伝{gender}の優勝と準優勝の差は？",
                f"{year}年荒玉{gender}の優勝と2位の差",
                f"{year}年荒玉{gender}の1位と2位のタイム差",
                f"{year}年荒玉駅伝{gender}の優勝と2位のタイム差は？",
            ]
        )
    if a == 2 and b == 3:
        qs.extend(
            [
                f"{year}年荒玉駅伝{gender}の準優勝と3位の差は？",
                f"{year}年荒玉{gender}の2位と3位の差",
                f"{year}年荒玉{gender}の2位と3位のタイム差",
            ]
        )
    if a == 1 and b >= 3:
        qs.extend(
            [
                f"{year}年荒玉駅伝{gender}の優勝と{b}位の差は？",
                f"{year}年荒玉{gender}の1位と{b}位のタイム差",
            ]
        )
    # relative year for previous fiscal year
    if year == DEFAULT_YEAR - 1:
        qs.extend(
            [
                f"去年の荒玉駅伝の{gender}の{a}位と{b}位の差は？",
                f"昨年の荒玉駅伝{gender}の{a}位と{b}位のタイム差",
                f"去年の荒玉{gender}の{a}位と{b}位の差",
            ]
        )
        if a == 2 and b == 3:
            qs.extend(
                [
                    f"去年の荒玉駅伝の{gender}の2位と3位の差は？",
                    f"昨年の荒玉{gender}の2位と3位の差は？",
                ]
            )
        if a == 1 and b == 2:
            qs.extend(
                [
                    f"去年の荒玉駅伝{gender}の優勝と準優勝の差は？",
                    f"昨年の荒玉{gender}の1位と2位のタイム差",
                ]
            )
    return qs


def build_answer(year: int, gender: str, ta: dict, tb: dict, gap_sec: int) -> str:
    gap = fmt_gap(gap_sec)
    return (
        f"{year}年荒玉駅伝{gender}の{ta['rank']}位・{ta['team']}（{ta['total']}）と"
        f"{tb['rank']}位・{tb['team']}（{tb['total']}）の差は{gap}です。"
    )


def gen_entries() -> list[dict]:
    out: list[dict] = []
    for gender, path, src in (
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
    ):
        years = load_years(path)
        for year_s, yd in sorted(years.items()):
            year = int(year_s)
            teams = ranked_teams(yd)
            if len(teams) < 2:
                continue
            by_rank = {t["rank"]: t for t in teams}
            ranks = sorted(by_rank)
            pairs: list[tuple[int, int]] = []
            # adjacent
            for i in range(len(ranks) - 1):
                pairs.append((ranks[i], ranks[i + 1]))
            # winner vs 3..MAX
            if 1 in by_rank:
                for b in ranks:
                    if 2 < b <= MAX_WINNER_VS:
                        pairs.append((1, b))
            # dedupe
            seen_pairs: set[tuple[int, int]] = set()
            for a, b in pairs:
                if a >= b or (a, b) in seen_pairs:
                    continue
                if a not in by_rank or b not in by_rank:
                    continue
                seen_pairs.add((a, b))
                ta, tb = by_rank[a], by_rank[b]
                sa, sb = parse_clock(ta["total"]), parse_clock(tb["total"])
                if sa is None or sb is None:
                    continue
                gap_sec = abs(sb - sa)
                eid = f"{ID_PREFIX}{year}-{gender}-{a}-{b}"
                ans = build_answer(year, gender, ta, tb, gap_sec)
                out.append(
                    entry(
                        eid,
                        pair_questions(year, gender, a, b),
                        ans,
                        [src, "input/aragyoku/winners-by-year.md"],
                        ["aragyoku", "gap", "rank", gender, year],
                    )
                )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = list(data.get("entries") or [])
    before = len(entries)
    entries = [e for e in entries if not str(e.get("id", "")).startswith(ID_PREFIX)]
    print(f"removed old {ID_PREFIX}* : {before - len(entries)}")

    new_entries = gen_entries()
    print(f"new rank-gap entries: {len(new_entries)}")

    existing_q = {q for e in entries for q in (e.get("questions") or [])}
    cleaned: list[dict] = []
    for e in new_entries:
        qs = [q for q in e["questions"] if q not in existing_q]
        if not qs:
            continue
        e = dict(e)
        e["questions"] = qs
        cleaned.append(e)
        for q in qs:
            existing_q.add(q)
    print(f"after question dedupe: {len(cleaned)}")

    for want in (
        "aragyoku-rankgap-2025-男子-2-3",
        "aragyoku-rankgap-2025-男子-1-2",
        "aragyoku-rankgap-2025-女子-1-2",
    ):
        sample = next((e for e in cleaned if e["id"] == want), None)
        if sample:
            print("SAMPLE", sample["id"])
            print(sample["answer"].strip())
            print("qs", sample["questions"][:4])
            print("---")

    if args.dry_run:
        return 0

    merged = entries + cleaned
    seen: set[str] = set()
    uniq = []
    for e in merged:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        uniq.append(e)
    data["entries"] = uniq
    data["total"] = len(uniq)
    note = data.get("note") or ""
    if "順位間タイム差" not in note:
        data["note"] = note.rstrip() + "\n荒玉駅伝の順位間タイム差（隣接順位・優勝との差）を収録。\n"
    FAQ.write_text(
        yaml.dump(
            data,
            allow_unicode=True,
            sort_keys=False,
            width=120,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {FAQ.relative_to(ROOT)} total={len(uniq)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
