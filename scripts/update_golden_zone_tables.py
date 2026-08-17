#!/usr/bin/env python3
"""Update Daiming student memos with Norwegian-method pace tables.

Pace logic (Bakken *The Norwegian Method Applied*):
- T pace: Daniels T-pace adjusted by interval duration (Ch.5 Pace Guide)
- GZ: sub-threshold band below T, also adjusted by interval length (Ch.2)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai.pace_calculator import (  # noqa: E402
    BLOCK_START,
    build_block,
    replace_block,
)
from yaml_io import load_events_yaml, write_events_yaml

ROOT = Path(__file__).resolve().parent.parent
EVENTS_PATH = ROOT / "input" / "events.2026.yaml"


def update_events(data: dict) -> int:
    count = 0
    for ev in data["events"]:
        desc = ev.get("description") or ""
        if not isinstance(desc, str) or BLOCK_START not in desc:
            continue
        t_match = re.search(r"T: (\d+:\d+)/km", desc)
        if not t_match:
            print(f"  skip (no T pace): {ev['title']}")
            continue
        new_block = build_block(t_match.group(1))
        new_desc = replace_block(desc, new_block)
        if new_desc == desc:
            print(f"  skip (no change): {ev['title']}")
            continue
        ev["description"] = new_desc
        count += 1
        print(f"  updated: {ev['title']}")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    path = ROOT / "input" / f"events.{args.year}.yaml"
    data = load_events_yaml(path)
    count = update_events(data)
    print(f"\n{count} memos updated")
    if not args.dry_run and count:
        write_events_yaml(path, data)
        print(f"Written: {path}")


if __name__ == "__main__":
    main()
