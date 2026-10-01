#!/usr/bin/env python3
"""Rebuild aragyoku-*-leg*-board prepared FAQ with 去年/語順バリエーション.

Usage:
  python3 scripts/refresh_prepared_qa_leg_boards.py
  python3 scripts/refresh_prepared_qa_leg_boards.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_aragyoku_3000 import (  # noqa: E402
    DEFAULT_YEAR,
    LAST_YEAR,
    gen_leg_rank_board,
)

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
BOARD_RE = re.compile(r"^aragyoku-\d{4}-(男子|女子)-leg\d+-board$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = list(data.get("entries") or [])
    before = len(entries)
    kept = [e for e in entries if not BOARD_RE.match(str(e.get("id") or ""))]
    removed = before - len(kept)
    print(f"removed leg-board entries: {removed}")

    existing_ids = {e["id"] for e in kept}
    # regenerate all boards (no existing board ids)
    new_boards = gen_leg_rank_board(existing_ids, limit=2000)
    print(f"new leg-board entries: {len(new_boards)}")

    existing_q = {q for e in kept for q in (e.get("questions") or [])}
    cleaned = []
    for e in new_boards:
        qs = [q for q in e["questions"] if q not in existing_q]
        if not qs:
            continue
        e = dict(e)
        e["questions"] = qs
        cleaned.append(e)
        for q in qs:
            existing_q.add(q)
    print(f"after question dedupe: {len(cleaned)}")

    sample = next(
        (e for e in cleaned if e["id"] == "aragyoku-2025-男子-leg2-board"),
        None,
    )
    if sample:
        print("SAMPLE", sample["id"])
        print(sample["answer"][:220])
        print("has 去年男子2区語順?", any("去年の男子2区の荒玉" in q for q in sample["questions"]))
        print("qs:", sample["questions"])

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
    print(f"wrote {FAQ.relative_to(ROOT)} total={len(uniq)} (DEFAULT={DEFAULT_YEAR}, LAST={LAST_YEAR})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
