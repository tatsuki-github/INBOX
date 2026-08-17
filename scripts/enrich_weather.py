#!/usr/bin/env python3
"""いだてん岱明練習イベントに玉名市の天気データを付与する。"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input"
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from practice_utils import is_practice_event, tags_list  # noqa: E402
from weather_utils import (  # noqa: E402
    build_weather_record,
    fetch_hourly_weather,
    infer_observation_time,
    lookup_hourly,
)
from yaml_io import load_events_yaml, write_events_yaml  # noqa: E402


def is_daiming_practice(ev: dict) -> bool:
    if not is_practice_event(ev):
        return False
    tags = tags_list(ev)
    return "practice:daiming" in tags or "いだてん岱明練習" in tags


def event_date(ev: dict) -> date | None:
    raw = ev.get("date")
    if not raw:
        return None
    return date.fromisoformat(str(raw))


def in_month_range(day: date, year: int, months: tuple[int, ...]) -> bool:
    return day.year == year and day.month in months


def enrich_year(
    year: int,
    *,
    months: tuple[int, ...],
    apply: bool,
    force: bool,
) -> tuple[int, int, int]:
    path = INPUT_DIR / f"events.{year}.yaml"
    if not path.exists():
        return 0, 0, 0

    data = load_events_yaml(path)
    targets: list[dict] = []
    for ev in data.get("events") or []:
        if not is_daiming_practice(ev):
            continue
        day = event_date(ev)
        if day is None or not in_month_range(day, year, months):
            continue
        if ev.get("weather") and not force:
            continue
        targets.append(ev)

    if not targets:
        print(f"{path}: 対象イベントなし")
        return 0, 0, 0

    start = min(event_date(ev) for ev in targets)  # type: ignore[type-var]
    end = max(event_date(ev) for ev in targets)  # type: ignore[type-var]
    print(f"Fetching weather for {start} .. {end} ({len(targets)} events)...")
    hourly_index = fetch_hourly_weather(start, end)
    fetched_at = datetime.now().astimezone()

    updated = skipped = 0
    for ev in targets:
        day = event_date(ev)
        assert day is not None
        at = infer_observation_time(ev)
        hourly = lookup_hourly(hourly_index, day, at)
        if hourly is None:
            skipped += 1
            print(f"  skip (no data): {day} {ev.get('title')}", file=sys.stderr)
            continue
        ev["weather"] = build_weather_record(day, at, hourly, fetched_at=fetched_at)
        updated += 1

    if apply and updated:
        write_events_yaml(path, data)
        print(f"Updated {path}: {updated} events ({skipped} skipped, no data)")
    else:
        print(f"Would update {path}: {updated} events ({skipped} skipped, no data)")

    return updated, skipped, len(targets) - updated - skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="いだてん岱明練習に玉名市の天気を付与")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--months", type=int, nargs="+", default=[7, 8])
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="既存 weather を上書き")
    args = parser.parse_args(argv)

    apply = args.apply and not args.dry_run
    updated, skipped, _ = enrich_year(
        args.year,
        months=tuple(args.months),
        apply=apply,
        force=args.force,
    )
    if skipped and not apply:
        print(f"Note: {skipped} events had no hourly data (dry-run)", file=sys.stderr)
    return 0 if updated or skipped == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
