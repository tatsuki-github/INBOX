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

from ai.coach_sheet import attach_abort_if, build_coach_sheet  # noqa: E402
from ai.practice_generator import generate_practice_auto  # noqa: E402
from ai.session_context import load_session_context  # noqa: E402
from practice_utils import tags_list  # noqa: E402
from yaml_io import load_events_yaml, write_events_yaml  # noqa: E402

ROOT = SCRIPTS_DIR.parent
INPUT_DIR = ROOT / "input"

SESSION_TITLES = {"morning": "岱明朝練", "evening": "岱明夕練"}
SESSION_TAGS = {"morning": "session:morning", "evening": "session:evening"}


def _event_matches(ev: dict, event_date: str, title: str, session: str) -> bool:
    if ev.get("date") != event_date:
        return False
    ev_title = ev.get("title") or ""
    tags = tags_list(ev)
    if SESSION_TAGS[session] in tags:
        return True
    if SESSION_TITLES[session] in ev_title:
        return True
    return title in ev_title


def _apply_to_events(
    year: int,
    event_date: str,
    title: str,
    practice: dict,
    template_id: str | None,
    description: str,
    session: str,
) -> None:
    path = INPUT_DIR / f"events.{year}.yaml"
    data = load_events_yaml(path)
    events = data.setdefault("events", [])
    for ev in events:
        if _event_matches(ev, event_date, title, session):
            ev["practice"] = practice
            ev["description"] = description
            if template_id:
                ev["template_ref"] = template_id
            write_events_yaml(path, data)
            return
    tags = ["practice:daiming", SESSION_TAGS[session]]
    events.append(
        {
            "title": title,
            "date": event_date,
            "all_day": False,
            "category": "予定",
            "tags": tags,
            "template_ref": template_id,
            "description": description,
            "practice": practice,
        }
    )
    write_events_yaml(path, data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Coach natural language request")
    parser.add_argument("--title", default=None)
    parser.add_argument("--session", choices=("morning", "evening"), default="evening")
    parser.add_argument("--format", choices=("sheet", "yaml", "json"), default="sheet")
    parser.add_argument("--dry-run", action="store_true", help="Template-only, no LLM")
    parser.add_argument("--experiment", action="store_true", help="Mark as weekly experiment session")
    parser.add_argument("--t-pace", default="4:01", help="Daniels T pace for Norwegian tables")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--year", type=int)
    parser.add_argument("--date", help="YYYY-MM-DD for context and --apply")
    args = parser.parse_args(argv)

    title = args.title or SESSION_TITLES[args.session]
    year = args.year or (int(args.date[:4]) if args.date else None)

    result = generate_practice_auto(
        args.input,
        title=title,
        dry_run=args.dry_run,
        is_experiment=args.experiment,
        t_pace=args.t_pace,
    )

    ctx = None
    if args.date:
        ctx = load_session_context(args.date, session=args.session, year=year)

    sheet = build_coach_sheet(
        result.practice,
        ctx=ctx,
        session=args.session,
        t_pace=args.t_pace,
        ok=result.ok,
        template_id=result.metadata.template_id,
        is_experiment=args.experiment or result.metadata.is_experiment,
    )
    attach_abort_if(result.practice, sheet.abort_if)

    output = {
        "sheet": sheet.render(),
        "confidence": sheet.confidence,
        "description": sheet.description_for_apply,
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
            "confidence": sheet.confidence,
        },
        "errors": result.errors,
    }

    if args.format == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif args.format == "yaml":
        print(yaml.dump(output, allow_unicode=True, sort_keys=False))
    else:
        print(sheet.render(), end="" if sheet.render().endswith("\n") else "\n")

    if args.apply:
        if not year or not args.date:
            print("error: --apply requires --year or --date", file=sys.stderr)
            return 2
        if not result.ok or sheet.confidence == "withhold":
            print("error: cannot apply invalid or withheld practice", file=sys.stderr)
            return 1
        _apply_to_events(
            year,
            args.date,
            title,
            result.practice,
            result.metadata.template_id,
            sheet.description_for_apply,
            args.session,
        )
        print(f"Applied to events.{year}.yaml", file=sys.stderr)

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
