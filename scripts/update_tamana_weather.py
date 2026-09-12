#!/usr/bin/env python3
"""玉名市の天気を保存する。

通常は3時間間隔の予報を保存し、対象日が2日以内なら1時間間隔で更新する。
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from weather_utils import (  # noqa: E402
    TAMANA_LOCATION,
    _fetch_open_meteo,
    _hourly_to_index,
    degrees_to_direction,
    wmo_to_condition,
)

OUT = ROOT / "weather" / "tamana-forecast.json"
CSV_OUT = ROOT / "weather" / "tamana-forecast.csv"


def build_rows(start: date, end: date, interval_hours: int) -> list[dict]:
    data = _fetch_open_meteo(
        "https://api.open-meteo.com/v1/forecast",
        start,
        end,
    )
    index = _hourly_to_index(data)
    rows = []
    current = start
    while current <= end:
        for hour in range(0, 24, interval_hours):
            key = f"{current.isoformat()}T{hour:02d}:00"
            value = index.get(key)
            if not value:
                continue
            rows.append({
                "location": TAMANA_LOCATION,
                "datetime": key,
                "condition": wmo_to_condition(value.get("weather_code")),
                "temperature_c": value.get("temperature_2m"),
                "humidity_pct": value.get("relative_humidity_2m"),
                "precipitation_mm": value.get("precipitation"),
                "wind_direction": degrees_to_direction(value.get("wind_direction_10m")),
                "wind_speed_kmh": value.get("wind_speed_10m"),
                "source": "open-meteo",
                "interval_hours": interval_hours,
            })
        current += timedelta(days=1)
    return rows


def write_outputs(rows: list[dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = [
        "location", "datetime", "condition", "temperature_c", "humidity_pct",
        "precipitation_mm", "wind_direction", "wind_speed_kmh", "source",
        "interval_hours",
    ]
    with CSV_OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--refresh-days",
        type=int,
        default=2,
        help="開始日が今日からこの日数以内なら1時間間隔にする",
    )
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--start must be before or equal to --end")

    today = date.today()
    interval = 1 if (args.start - today).days <= args.refresh_days else 3
    rows = build_rows(args.start, args.end, interval)
    write_outputs(rows)
    print(f"saved {len(rows)} rows ({interval}-hour interval) to {OUT} and {CSV_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
