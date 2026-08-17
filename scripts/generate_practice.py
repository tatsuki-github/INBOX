#!/usr/bin/env python3
"""Generate a single practice menu from natural language."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ai.practice_generator import generate_practice_auto  # noqa: E402
from yaml_io import load_events_yaml, write_events_yaml  # noqa: E402

ROOT = SCRIPTS_DIR.parent
INPUT_DIR = ROOT / "input"


def _apply_to_events(year: int, event_date: str, title: str, practice: dict, template_id: str | None) -> None:
    path = INPUT_DIR / f"events.{year}.yaml"
    data = load_events_yaml(path)
    events = data.setdefault("events", [])
    for ev in events:
        if ev.get("date") == event_date and title in (ev.get("title") or ""):
            ev["practice"] = practice
            if template_id:
                ev["template_ref"] = template_id
            write_events_yaml(path, data)
            return
    events.append(
        {
            "title": title,
            "date": event_date,
            "all_day": False,
            "category": "予定",
            "tags": ["practice:daiming"],
            "template_ref": template_id,
            "practice": practice,
        }
    )
    write_events_yaml(path, data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Coach natural language request")
    parser.add_argument("--title", default="いだてん岱明練習")
    parser.add_argument("--format", choices=("yaml", "json"), default="yaml")
    parser.add_argument("--dry-run", action="store_true", help="Template-only, no LLM")
    parser.add_argument("--experiment", action="store_true", help="Mark as weekly experiment session")
    parser.add_argument("--t-pace", default="4:01", help="Daniels T pace for Norwegian tables")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--year", type=int)
    parser.add_argument("--date", help="YYYY-MM-DD for --apply")
    args = parser.parse_args(argv)

    result = generate_practice_auto(
        args.input,
        title=args.title,
        dry_run=args.dry_run,
        is_experiment=args.experiment,
        t_pace=args.t_pace,
    )

    output = {
        "intensity_header": result.metadata.intensity_header,
        "intensity_role": result.metadata.intensity_role,
        "intensity_minutes": result.metadata.intensity_minutes,
        "practice": result.practice,
        "metadata": {
            "template_id": result.metadata.template_id,
            "template_ids": result.metadata.template_ids,
            "attempts": result.metadata.attempts,
            "llm_used": result.metadata.llm_used,
            "dry_run": result.metadata.dry_run,
            "is_experiment": result.metadata.is_experiment,
        },
        "errors": result.errors,
    }

    if args.format == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(yaml.dump(output, allow_unicode=True, sort_keys=False))

    if args.apply:
        if not args.year or not args.date:
            print("error: --apply requires --year and --date", file=sys.stderr)
            return 2
        if not result.ok:
            print("error: cannot apply invalid practice", file=sys.stderr)
            return 1
        _apply_to_events(args.year, args.date, args.title, result.practice, result.metadata.template_id)
        print(f"Applied to events.{args.year}.yaml", file=sys.stderr)

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
