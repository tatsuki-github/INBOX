#!/usr/bin/env python3
"""Generate a weekly practice plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ai.weekly_planner import plan_week_auto  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", required=True, help="Week start date YYYY-MM-DD (Monday)")
    parser.add_argument("--guidance", help="Optional coach guidance for the week")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--format", choices=("yaml", "json"), default="yaml")
    args = parser.parse_args(argv)

    plan = plan_week_auto(args.week, guidance=args.guidance, dry_run=args.dry_run)
    payload = {
        "week_start": plan.week_start,
        "weekly_theme": plan.weekly_theme,
        "days": [
            {
                "date": d.date,
                "title": d.title,
                "template_id": d.template_id,
                "is_experiment": d.is_experiment,
                "coach_note": d.coach_note,
                "practice": d.generation.practice if d.generation else None,
                "errors": d.generation.errors if d.generation else [],
            }
            for d in plan.days
        ],
        "errors": plan.errors,
    }

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(yaml.dump(payload, allow_unicode=True, sort_keys=False))

    return 0 if plan.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
