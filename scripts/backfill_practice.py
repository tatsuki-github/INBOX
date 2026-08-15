#!/usr/bin/env python3
"""Backfill practice field from description for 2025-2026 daiming practice."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input"
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from practice_parser import parse_event
from practice_renderer import render_description
from practice_utils import is_practice_event, normalize_event_tags
from yaml_io import load_events_yaml, write_events_yaml

DEFAULT_YEARS = [2025, 2026]


def should_backfill(ev: dict) -> bool:
    if not is_practice_event(ev):
        return False
    if ev.get("practice"):
        return False
    desc = (ev.get("description") or "").strip()
    return bool(desc) and len(desc) <= 8000


def backfill_year(year: int, *, apply: bool, embed_comment: bool = True) -> tuple[int, int, int]:
    path = INPUT_DIR / f"events.{year}.yaml"
    if not path.exists():
        return 0, 0, 0
    data = load_events_yaml(path)
    updated = skipped = partial = 0
    for ev in data.get("events") or []:
        if not should_backfill(ev):
            continue
        parsed = parse_event(ev)
        items = parsed.practice.get("items") or []
        if not items:
            skipped += 1
            continue
        ev["practice"] = parsed.practice
        normalize_event_tags(ev)
        new_desc = render_description(
            parsed.practice,
            note_lines=parsed.note_lines,
            legacy_items=parsed.legacy_items,
            embed_comment=embed_comment,
        )
        if new_desc:
            ev["description"] = new_desc
        if parsed.confidence == "partial":
            partial += 1
        updated += 1
    if apply and updated:
        write_events_yaml(path, data)
        print(f"Updated {path}: {updated} events ({partial} partial, {skipped} skipped)")
    elif updated or skipped:
        print(f"Would update {path}: {updated} events ({partial} partial, {skipped} skipped)")
    return updated, partial, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="description から practice をバックフィル")
    parser.add_argument("--year", type=int, action="append")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    apply = args.apply and not args.dry_run
    years = args.year or DEFAULT_YEARS
    total = [0, 0, 0]
    for year in years:
        counts = backfill_year(year, apply=apply)
        total = [a + b for a, b in zip(total, counts)]
    print(f"Total: updated={total[0]} partial={total[1]} skipped={total[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
