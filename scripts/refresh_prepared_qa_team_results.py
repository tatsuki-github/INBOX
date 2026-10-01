#!/usr/bin/env python3
"""Rebuild aragyoku-*-team-*-rank FAQ with 去年/結果は？ phrasings (transcript-grounded).

Also refreshes core daiming 2025 men/women result entries.

Usage:
  python3 scripts/refresh_prepared_qa_team_results.py
  python3 scripts/refresh_prepared_qa_team_results.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import (  # noqa: E402
    MEN_FULL,
    WOMEN_FULL,
    format_team_result_answer,
    gen_aragyoku_team_ranks,
    load_years,
)

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
TEAM_RANK_RE = re.compile(r"^aragyoku-\d{4}-(男子|女子)-team-.+-rank$")


def refresh_daiming_core(entries: list[dict], years_men: dict, years_women: dict) -> None:
    """Keep short canonical ids but ground answers in transcript totals/legs."""
    mapping = {
        "aragyoku-2025-daiming-women": ("2025", "女子", years_women),
        "aragyoku-2025-daiming-men": ("2025", "男子", years_men),
    }
    for e in entries:
        eid = e.get("id")
        if eid not in mapping:
            continue
        year_s, gender, years = mapping[eid]
        yd = years.get(year_s) or {}
        team = next((t for t in (yd.get("teams") or []) if t.get("team") == "岱明"), None)
        if not team:
            continue
        year = int(year_s)
        e["answer"] = format_team_result_answer(year, gender, team) + "\n"
        # Natural 去年/結果 phrasings only（team-rank 側の「何位？」定型は残す）
        qs = list(e.get("questions") or [])
        extras = [
            f"去年の岱明の{gender}の結果は？",
            f"昨年の岱明の{gender}の結果は？",
            f"去年の岱明{gender}の結果は？",
            f"昨年の岱明{gender}の結果",
            f"去年の荒玉駅伝の岱明の{gender}の結果は？",
            f"{year}年の岱明の{gender}の結果は？",
            f"{year}年岱明{gender}の結果は？",
        ]
        for q in extras:
            if q not in qs:
                qs.append(q)
        e["questions"] = qs
        srcs = list(e.get("sources") or [])
        for s in (
            f"input/aragyoku/transcripts/{year}-{gender}.json",
            "out/analysis/aragyoku-teams/岱明.md",
        ):
            if s not in srcs:
                srcs.append(s)
        e["sources"] = srcs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = list(data.get("entries") or [])
    before = len(entries)
    kept = [e for e in entries if not TEAM_RANK_RE.match(str(e.get("id") or ""))]
    print(f"removed team-rank entries: {before - len(kept)}")

    years_men = load_years(MEN_FULL)
    years_women = load_years(WOMEN_FULL)
    refresh_daiming_core(kept, years_men, years_women)

    existing_ids = {e["id"] for e in kept}
    new_ranks = gen_aragyoku_team_ranks(existing_ids, limit=5000)
    print(f"new team-rank entries: {len(new_ranks)}")

    existing_q = {q for e in kept for q in (e.get("questions") or [])}
    cleaned = []
    for e in new_ranks:
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
        "aragyoku-2025-女子-team-岱明-rank",
        "aragyoku-2025-男子-team-岱明-rank",
        "aragyoku-2024-女子-team-岱明-rank",
    ):
        sample = next((e for e in cleaned if e["id"] == want), None)
        if sample:
            print("SAMPLE", sample["id"])
            print(sample["answer"].strip())
            print("has 去年の岱明の女子?", "去年の岱明の女子の結果は？" in sample["questions"])
            print("---")

    daiming_w = next((e for e in kept if e.get("id") == "aragyoku-2025-daiming-women"), None)
    if daiming_w:
        print("CORE daiming-women:", daiming_w["answer"].strip())
        print("core has user q?", "去年の岱明の女子の結果は？" in (daiming_w.get("questions") or []))

    if args.dry_run:
        return 0

    merged = kept + cleaned
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
    if "チーム結果（荒玉）" not in note:
        data["note"] = (
            note.rstrip()
            + "\n荒玉駅伝のチーム結果（順位・総合・区間選手）は transcripts 根拠。去年=2025。\n"
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
    print(f"wrote {FAQ.relative_to(ROOT)} total={len(uniq)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
