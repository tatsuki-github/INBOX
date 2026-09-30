#!/usr/bin/env python3
"""Generate prepared FAQ entries for 荒玉（荒尾・玉名）地区 athletes' season-bests.

Sources:
  input/external/sb/middle-school/by-year/{year}-sb-adopted.json
  Affiliation filter: input/arato_tamana_report.yaml keywords (+ 菊水 etc.)

Yearless questions ("○の自己ベストは？") are attached only to the current fiscal year
(default 2026). Past years always include the calendar year in questions (ADR 059).

Usage:
  python3 scripts/generate_aragyoku_athlete_sb_qa.py
  python3 scripts/generate_aragyoku_athlete_sb_qa.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
BY_YEAR = ROOT / "input" / "external" / "sb" / "middle-school" / "by-year"
REPORT = ROOT / "input" / "arato_tamana_report.yaml"

DEFAULT_YEAR = 2026
YEAR_START = 2012
YEAR_END = 2026

# Extra school tokens beyond report keywords (荒玉チームに出る校)
EXTRA_KEYWORDS = ["菊水", "三加和", "腹栄", "和水", "南関"]
EXCLUDE_NAMES = {"有尾明莉", "秀島恋莉", "竹熊紗良"}


def slug(s: str) -> str:
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^\w一-龥ぁ-んァ-ヶー\-]", "-", s)
    return s.strip("-")[:48] or "x"


def load_keywords() -> list[str]:
    keys = list(EXTRA_KEYWORDS)
    if REPORT.exists():
        data = yaml.safe_load(REPORT.read_text(encoding="utf-8")) or {}
        for k in data.get("affiliation_keywords") or []:
            if k not in keys:
                keys.append(k)
        for name in data.get("exclude_name_keywords") or []:
            EXCLUDE_NAMES.add(name)
    return keys


def is_aragyoku(aff: str, name: str, keywords: list[str]) -> bool:
    if not name or name in EXCLUDE_NAMES:
        return False
    aff = aff or ""
    return any(k in aff for k in keywords)


def truthy_adopted(v) -> bool:
    if v is True:
        return True
    s = str(v).strip().upper()
    return s in {"TRUE", "YES", "__YES__", "1", "○", "採用"}


def load_year_records(year: int, keywords: list[str]) -> dict[str, dict]:
    """name -> {aff, gender, distances: {dist: {mark, seconds, meet, date}}}"""
    path = BY_YEAR / f"{year}-sb-adopted.json"
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for r in rows:
        name = (r.get("名前") or "").strip()
        aff = (r.get("所属") or "").strip()
        if not is_aragyoku(aff, name, keywords):
            continue
        if not truthy_adopted(r.get("SB採用")):
            continue
        dist = (r.get("距離") or "").strip()
        mark = (r.get("SB") or r.get("記録") or "").strip()
        if not dist or not mark:
            continue
        try:
            sec = float(r.get("SB秒") or r.get("記録秒") or 1e12)
        except (TypeError, ValueError):
            sec = 1e12
        gender = (r.get("性別") or "").strip()
        meet = (r.get("大会名") or "").strip()
        date = (r.get("日付") or "").strip()
        bucket = out.setdefault(
            name,
            {"aff": aff, "gender": gender, "distances": {}},
        )
        # keep a more specific affiliation if present
        if aff and (not bucket["aff"] or len(aff) > len(bucket["aff"])):
            bucket["aff"] = aff
        if gender:
            bucket["gender"] = gender
        prev = bucket["distances"].get(dist)
        if prev is None or sec < prev["seconds"]:
            bucket["distances"][dist] = {
                "mark": mark,
                "seconds": sec,
                "meet": meet,
                "date": date,
            }
    return out


def dist_sort_key(d: str) -> tuple:
    m = re.match(r"(\d+(?:\.\d+)?)\s*m", d, re.I)
    return (float(m.group(1)) if m else 9999, d)


def build_entries_for_year(year: int, athletes: dict[str, dict]) -> list[dict]:
    entries: list[dict] = []
    current = year == DEFAULT_YEAR
    for name in sorted(athletes.keys()):
        info = athletes[name]
        aff = info["aff"] or "荒玉地区"
        gender = info["gender"] or ""
        dists = info["distances"]
        if not dists:
            continue
        lines = []
        for dist in sorted(dists.keys(), key=dist_sort_key):
            rec = dists[dist]
            bit = f"・{dist}: {rec['mark']}"
            if rec["meet"] or rec["date"]:
                bit += f"（{rec['meet']}、{rec['date']}）" if rec["meet"] else f"（{rec['date']}）"
            lines.append(bit)
        overview_ans = (
            f"{name}（{aff}"
            + (f"/{gender}" if gender else "")
            + f"）の自己ベスト（{year}年度・SB採用）です。\n"
            + "\n".join(lines)
            + "\n"
        )
        src = f"input/external/sb/middle-school/by-year/{year}-sb-adopted.json"
        if current:
            oq = [
                f"{name}の自己ベストは？",
                f"{name}のSBは？",
                f"{name}の記録は？",
                f"{year}年の{name}の自己ベストは？",
                f"今年の{name}の自己ベストは？",
            ]
        else:
            oq = [
                f"{year}年の{name}の自己ベストは？",
                f"{year}年{name}のSBは？",
                f"{year}年{name}の記録は？",
            ]
        entries.append(
            {
                "id": f"sb-{year}-{slug(name)}",
                "questions": oq,
                "answer": overview_ans,
                "sources": [src, "input/arato_tamana_report.yaml"],
                "tags": ["sb", "athlete", "aragyoku", year] + ([gender] if gender else []),
            }
        )
        for dist, rec in sorted(dists.items(), key=lambda kv: dist_sort_key(kv[0])):
            if current:
                dq = [
                    f"{name}の{dist}の自己ベストは？",
                    f"{name}の{dist}SBは？",
                    f"{name}の{dist}記録は？",
                    f"{year}年の{name}の{dist}自己ベストは？",
                ]
            else:
                dq = [
                    f"{year}年の{name}の{dist}の自己ベストは？",
                    f"{year}年{name}の{dist}SBは？",
                    f"{year}年{name}の{dist}記録は？",
                ]
            ans = (
                f"{name}（{aff}"
                + (f"/{gender}" if gender else "")
                + f"）の{dist}自己ベストは {rec['mark']} です。"
            )
            if rec["meet"] or rec["date"]:
                ans += f" 大会: {rec['meet']}（{rec['date']}）。"
            ans += "\n"
            entries.append(
                {
                    "id": f"sb-{year}-{slug(name)}-{slug(dist)}",
                    "questions": dq,
                    "answer": ans,
                    "sources": [src],
                    "tags": ["sb", "athlete", "aragyoku", year, dist]
                    + ([gender] if gender else []),
                }
            )
    return entries


def merge_into_faq(new_entries: list[dict], dry_run: bool) -> int:
    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = data.get("entries") or []
    # Drop previous auto SB athlete entries and known stale hand-written matsuno/tanoue duplicates
    drop_prefixes = ("sb-2026-", "sb-201", "sb-2020", "sb-2021", "sb-2022", "sb-2023", "sb-2024", "sb-2025")
    drop_ids = {
        "sb-matsuno-1500",
        "sb-anpura-1500",
        "sb-sato-1500",
        "sb-murakami-1500",
        "sb-田上颯人",
        "sb-2026-田上颯人-1500m",
        "sb-2026-田上颯人-3000m",
    }
    kept = []
    removed = 0
    for e in entries:
        eid = e.get("id") or ""
        if eid in drop_ids or (eid.startswith("sb-") and re.match(r"sb-20\d{2}-", eid)):
            # keep non-athlete bulk like sb-school-* ? those are sb-school- not sb-YYYY-
            if eid.startswith("sb-school-") or eid in {
                "sb-3000-fastest",
                "sb-1500-top20",
                "sb-atrc",
                "sb-kanaguri-project",
                "sb-nankan",
                "sb-takada-mana",
                "sb-women800-daiming",
                "sb-men1500-school",
                "sb-middle-generic",
                "sb-athlete-generic",
                "sb-how-to-ask",
            }:
                kept.append(e)
                continue
            if eid.startswith("sb-school-"):
                kept.append(e)
                continue
            removed += 1
            continue
        kept.append(e)

    # Also remove any remaining sb-YYYY-name that we regenerate
    new_ids = {e["id"] for e in new_entries}
    kept = [e for e in kept if e.get("id") not in new_ids]

    # Avoid duplicate question strings stealing matches: drop kept entries whose
    # questions fully overlap new yearless athlete SB questions for current year.
    new_yearless_q = set()
    for e in new_entries:
        if f"sb-{DEFAULT_YEAR}-" in e["id"] or e["id"].startswith(f"sb-{DEFAULT_YEAR}-"):
            for q in e["questions"]:
                if not re.search(r"20\d{2}|去年|昨年|一昨年", q):
                    new_yearless_q.add(q)

    filtered_kept = []
    for e in kept:
        qs = [q for q in e.get("questions") or [] if q not in new_yearless_q]
        if not qs:
            removed += 1
            continue
        if len(qs) != len(e["questions"]):
            e = dict(e)
            e["questions"] = qs
        filtered_kept.append(e)

    merged = filtered_kept + new_entries
    # unique ids
    seen = set()
    uniq = []
    for e in merged:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        uniq.append(e)

    data["entries"] = uniq
    data["total"] = len(uniq)
    data["note"] = (
        "想定質問への定型回答（ADR 059）。年なし＝今年度。"
        "荒玉（荒尾・玉名）地区選手の年度別SBを by-year sb-adopted から生成。\n"
        "ヒット時は本文をほぼそのまま返す。未ヒット時のみ RAG/LLM。\n"
    )
    print(f"removed {removed}, added {len(new_entries)}, total {len(uniq)}")
    if dry_run:
        return len(uniq)
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
    print(f"wrote {FAQ.relative_to(ROOT)}")
    return len(uniq)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--year-start", type=int, default=YEAR_START)
    parser.add_argument("--year-end", type=int, default=YEAR_END)
    args = parser.parse_args()

    keywords = load_keywords()
    all_new: list[dict] = []
    for year in range(args.year_start, args.year_end + 1):
        athletes = load_year_records(year, keywords)
        year_entries = build_entries_for_year(year, athletes)
        print(f"{year}: athletes={len(athletes)} entries={len(year_entries)}")
        all_new.extend(year_entries)

    # sanity: 松野凛空 2026
    mats = [e for e in all_new if e["id"].startswith("sb-2026-松野凛空")]
    for e in mats:
        print("CHECK", e["id"], e["answer"].split("\n")[0][:80])
        assert "4:22.33" in e["answer"] or "9:37.84" in e["answer"] or "自己ベスト" in e["answer"]

    merge_into_faq(all_new, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
