#!/usr/bin/env python3
"""Normalize machine-readable practice tags on events."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input"
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from practice_utils import is_practice_event, normalize_event_tags
from yaml_io import load_events_yaml, write_events_yaml

DEFAULT_YEARS = [2025, 2026]


def normalize_year(year: int, *, apply: bool) -> int:
    path = INPUT_DIR / f"events.{year}.yaml"
    if not path.exists():
        return 0
    data = load_events_yaml(path)
    changed = 0
    for ev in data.get("events") or []:
        if not is_practice_event(ev):
            continue
        if normalize_event_tags(ev):
            changed += 1
    if apply and changed:
        write_events_yaml(path, data)
        print(f"Updated {path}: {changed} events")
    elif changed:
        print(f"Would update {path}: {changed} events")
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="練習タグを正規化")
    parser.add_argument("--year", type=int, action="append")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    years = args.year or DEFAULT_YEARS
    total = sum(normalize_year(y, apply=args.apply) for y in years)
    print(f"Total changed: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
