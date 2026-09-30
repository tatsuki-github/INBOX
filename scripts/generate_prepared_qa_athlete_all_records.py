#!/usr/bin/env python3
"""Add per-athlete all-records prepared FAQ (past 3 years, aragyoku district).

Covers questions like 「南本幸治郎の今年度の全ての記録」 with every race
row and meet result URL. Sources: Drive single-table CSVs for 2024–2026.

Usage:
  python3 scripts/generate_prepared_qa_athlete_all_records.py
  python3 scripts/generate_prepared_qa_athlete_all_records.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import entry, slug  # noqa: E402
from generate_prepared_qa_knowledge_1000 import load_keywords  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
BY_YEAR_CSV = ROOT / "input" / "external" / "drive" / "personal" / "t-tsuchiyama" / "sb" / "by-year"
YEARS = (2024, 2025, 2026)
DEFAULT_YEAR = 2026


def _truthy_sb(val: object) -> bool:
    s = str(val or "").strip().upper()
    return s in {"TRUE", "__YES__", "YES", "1", "○", "採用"}


def load_year_rows(year: int) -> list[dict[str, str]]:
    path = BY_YEAR_CSV / f"{year}-single-table.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def affiliation_match(aff: str, keywords: list[str]) -> bool:
    return any(k in aff for k in keywords)


def group_by_athlete(
    rows: list[dict[str, str]], keywords: list[str]
) -> dict[str, list[dict[str, str]]]:
    by: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        aff = (r.get("所属") or "").strip()
        name = (r.get("名前") or "").strip()
        if not name or not aff:
            continue
        if not affiliation_match(aff, keywords):
            continue
        dist = (r.get("距離") or "").strip()
        mark = (r.get("記録") or "").strip()
        if not dist or not mark:
            continue
        by[name].append(r)
    return by


def sort_races(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    def key(r: dict[str, str]) -> tuple:
        return (
            r.get("日付") or "",
            r.get("距離") or "",
            float(r.get("記録秒") or 1e12),
        )

    return sorted(rows, key=key)


def meet_url(r: dict[str, str]) -> str:
    for key in ("参考", "url", "URL"):
        u = (r.get(key) or "").strip()
        if u.startswith("http") and "notion.com" not in u and "notion.so" not in u:
            return u
    return ""


def shorten_meet(meet: str) -> str:
    m = re.sub(r"\s+", " ", (meet or "").strip())
    # drop leading YYYY.M.D style noise already covered by date
    m = re.sub(r"^\d{4}\.\d{1,2}\.\d{1,2}\s*", "", m)
    if len(m) > 40:
        m = m[:39] + "…"
    return m


def format_race_line(r: dict[str, str]) -> str:
    date = (r.get("日付") or "").strip() or "?"
    dist = (r.get("距離") or "").strip()
    mark = (r.get("記録") or "").strip()
    meet = shorten_meet(r.get("大会名") or "")
    url = meet_url(r)
    bit = f"{date} {dist} {mark}"
    if meet:
        bit += f"（{meet}）"
    if _truthy_sb(r.get("SB採用")):
        bit += "【SB】"
    if url:
        bit += f" 大会結果: {url}"
    return bit


def sb_summary(rows: list[dict[str, str]]) -> str:
    best: dict[str, dict[str, str]] = {}
    for r in rows:
        if not _truthy_sb(r.get("SB採用")):
            continue
        dist = (r.get("距離") or "").strip()
        try:
            sec = float(r.get("SB秒") or r.get("記録秒") or 1e12)
        except (TypeError, ValueError):
            continue
        prev = best.get(dist)
        if prev is None or sec < float(prev.get("_sec") or 1e12):
            best[dist] = {**r, "_sec": str(sec)}
    if not best:
        return ""
    parts = []
    for dist in sorted(best.keys()):
        r = best[dist]
        mark = (r.get("SB") or r.get("記録") or "").strip()
        parts.append(f"{dist} {mark}")
    return "SB採用: " + "、".join(parts) + "。"


def build_year_answer(
    name: str, year: int, rows: list[dict[str, str]], *, yearless: bool = False
) -> str:
    races = sort_races(rows)
    aff = (races[0].get("所属") or "").strip()
    gender = (races[0].get("性別") or "").strip()
    who = f"{name}（{aff}" + (f"/{gender}" if gender else "") + "）"
    label = "今年度" if yearless else f"{year}年度"
    lines = [format_race_line(r) for r in races]
    ans = f"{who}の{label}の記録は全{len(lines)}件です。\n" + "\n".join(lines)
    sb = sb_summary(races)
    if sb:
        ans += "\n" + sb
    return ans


def build_3y_answer(
    name: str, by_year: dict[int, list[dict[str, str]]]
) -> str:
    years = sorted(by_year.keys())
    aff = ""
    gender = ""
    for y in reversed(years):
        if by_year[y]:
            aff = (by_year[y][0].get("所属") or "").strip()
            gender = (by_year[y][0].get("性別") or "").strip()
            break
    who = f"{name}（{aff}" + (f"/{gender}" if gender else "") + "）"
    chunks = [f"{who}の過去3年（{years[0]}–{years[-1]}）の記録です。"]
    total = 0
    for y in years:
        races = sort_races(by_year[y])
        total += len(races)
        chunks.append(f"【{y}年度・{len(races)}件】")
        chunks.extend(format_race_line(r) for r in races)
        sb = sb_summary(races)
        if sb:
            chunks.append(sb)
    chunks[0] = f"{who}の過去3年（{years[0]}–{years[-1]}）の記録は全{total}件です。"
    return "\n".join(chunks)


def gen_entries(existing_ids: set[str]) -> list[dict]:
    keywords = load_keywords()
    # Ensure club spellings covered
    for extra in ("ＮＪＡＣ", "NJAC", "玉東クラブ", "玉名アスリーツ"):
        if extra not in keywords:
            keywords.append(extra)

    per_year: dict[int, dict[str, list[dict[str, str]]]] = {}
    for year in YEARS:
        per_year[year] = group_by_athlete(load_year_rows(year), keywords)

    out: list[dict] = []
    src_base = "input/external/drive/personal/t-tsuchiyama/sb/by-year"

    # 1) athlete × year
    for year in YEARS:
        for name, rows in sorted(per_year[year].items()):
            eid = f"records-athlete-{year}-{slug(name)}"
            if eid in existing_ids:
                continue
            qs = [
                f"{year}年{name}の全ての記録",
                f"{name}の{year}年の全ての記録",
                f"{year}年の{name}の全記録は？",
                f"{name}の{year}年度の記録一覧",
                f"{year}年度{name}のレース結果一覧",
            ]
            if year == DEFAULT_YEAR:
                qs.extend(
                    [
                        f"{name}の今年度の全ての記録",
                        f"{name}の今年の全ての記録",
                        f"{name}の全ての記録",
                        f"{name}の全記録は？",
                        f"{name}の記録一覧",
                        f"{name}の今季の全記録",
                    ]
                )
            ans = build_year_answer(
                name, year, rows, yearless=(year == DEFAULT_YEAR)
            )
            # For dated entries keep 「2026年度」 wording even on current year
            if year == DEFAULT_YEAR:
                # Dual: yearless questions use 「今年度」 answer; keep one entry
                # with 今年度 label since yearless maps to current year.
                ans = build_year_answer(name, year, rows, yearless=True)
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [f"{src_base}/{year}-single-table.csv"],
                    ["records", "athlete", "all", year, name],
                )
            )

    # 2) past-3-years combined (only athletes with any rows)
    names = sorted({n for ymap in per_year.values() for n in ymap})
    for name in names:
        by_year = {y: per_year[y][name] for y in YEARS if name in per_year[y]}
        if not by_year:
            continue
        eid = f"records-athlete-3y-{slug(name)}"
        if eid in existing_ids:
            continue
        qs = [
            f"{name}の過去3年の全ての記録",
            f"{name}の直近3年の記録一覧",
            f"{name}の3年分の全記録は？",
            f"{name}の過去三年のレース結果",
        ]
        out.append(
            entry(
                eid,
                qs,
                build_3y_answer(name, by_year),
                [f"{src_base}/{y}-single-table.csv" for y in sorted(by_year)],
                ["records", "athlete", "all", "3y", name],
            )
        )

    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = data.get("entries") or []
    existing_ids = {e["id"] for e in entries}
    print(f"existing entries: {len(entries)}")

    new_entries = gen_entries(existing_ids)
    print(f"new athlete-all-records: {len(new_entries)}")

    # drop empty-question / id collisions after question dedupe
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

    sample = next((e for e in cleaned if "南本幸治郎" in e["id"]), None)
    if sample:
        print("SAMPLE", sample["id"])
        print(sample["answer"][:500])
        print("questions:", sample["questions"][:6])

    if args.dry_run:
        return 0

    merged = list(entries) + cleaned
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
    if "選手全記録" not in note:
        data["note"] = (
            note.rstrip()
            + "\n選手の年度別・過去3年全記録（荒玉地区・大会リンク付き）を収録。\n"
        )
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
    print(f"wrote {FAQ.relative_to(ROOT)} total={len(uniq)} (+{len(cleaned)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
