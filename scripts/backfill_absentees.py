#!/usr/bin/env python3
"""Backfill practice.absentees from description text."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input"
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from practice_utils import extract_absentees_from_text, is_practice_event
from yaml_io import load_events_yaml, write_events_yaml

DEFAULT_YEARS = [2025, 2026]


def backfill_year(year: int, *, apply: bool) -> tuple[int, int]:
    path = INPUT_DIR / f"events.{year}.yaml"
    if not path.exists():
        return 0, 0
    data = load_events_yaml(path)
    updated = skipped = 0
    for ev in data.get("events") or []:
        if not is_practice_event(ev):
            continue
        practice = ev.get("practice")
        if not isinstance(practice, dict):
            continue
        if practice.get("absentees") is not None:
            skipped += 1
            continue
        extracted = extract_absentees_from_text(ev.get("description") or "")
        if extracted is None:
            skipped += 1
            continue
        practice["absentees"] = extracted
        updated += 1
    if apply and updated:
        write_events_yaml(path, data)
        print(f"Updated {path}: {updated} events ({skipped} skipped)")
    elif updated or skipped:
        print(f"Would update {path}: {updated} events ({skipped} skipped)")
    return updated, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="description から practice.absentees をバックフィル")
    parser.add_argument("--year", type=int, action="append")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    apply = args.apply and not args.dry_run
    years = args.year or DEFAULT_YEARS
    total = [0, 0]
    for year in years:
        counts = backfill_year(year, apply=apply)
        total = [a + b for a, b in zip(total, counts)]
    print(f"Total: updated={total[0]} skipped={total[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
