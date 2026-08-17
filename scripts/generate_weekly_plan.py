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

from ai.coach_sheet import build_coach_sheet  # noqa: E402
from ai.session_context import load_session_context  # noqa: E402
from ai.weekly_planner import plan_week_auto  # noqa: E402


def _session_for_template(template_id: str | None) -> str:
    tid = template_id or ""
    if tid.startswith("jog"):
        return "morning"
    return "evening"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", required=True, help="Week start date YYYY-MM-DD (Monday)")
    parser.add_argument("--guidance", help="Optional coach guidance for the week")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--format", choices=("yaml", "json", "sheet"), default="yaml")
    parser.add_argument("--t-pace", default="4:01")
    args = parser.parse_args(argv)

    plan = plan_week_auto(args.week, guidance=args.guidance, dry_run=args.dry_run)
    year = int(args.week[:4])
    day_payloads = []
    sheet_blocks: list[str] = [f"# {plan.weekly_theme}", ""]
    for d in plan.days:
        session = _session_for_template(d.template_id)
        ctx = load_session_context(d.date, session=session, year=year)
        sheet_text = None
        if d.generation and d.generation.practice.get("items"):
            sheet = build_coach_sheet(
                d.generation.practice,
                ctx=ctx,
                session=session,
                t_pace=args.t_pace,
                ok=d.generation.ok,
                template_id=d.template_id,
                is_experiment=d.is_experiment,
            )
            sheet_text = sheet.render()
            sheet_blocks.append(sheet_text.rstrip())
            sheet_blocks.append("")
        day_payloads.append(
            {
                "date": d.date,
                "title": d.title,
                "template_id": d.template_id,
                "is_experiment": d.is_experiment,
                "coach_note": d.coach_note,
                "intensity_role": (
                    d.generation.metadata.intensity_role if d.generation else None
                ),
                "intensity_header": (
                    d.generation.metadata.intensity_header if d.generation else None
                ),
                "practice": d.generation.practice if d.generation else None,
                "sheet": sheet_text,
                "errors": d.generation.errors if d.generation else [],
            }
        )
    payload = {
        "week_start": plan.week_start,
        "weekly_theme": plan.weekly_theme,
        "intensity_distribution": (
            plan.intensity.as_dict() if plan.intensity else None
        ),
        "days": day_payloads,
        "errors": plan.errors,
    }

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.format == "sheet":
        print("\n".join(sheet_blocks).strip() + "\n")
    else:
        print(yaml.dump(payload, allow_unicode=True, sort_keys=False))

    return 0 if plan.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
