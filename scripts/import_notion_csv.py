#!/usr/bin/env python3
"""NotionエクスポートCSVを input/events.YYYY.yaml に取り込む。"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


class LiteralStr(str):
    """複数行文字列を YAML の | で出すためのマーカー。"""


def literal_representer(dumper: yaml.Dumper, data: LiteralStr):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(LiteralStr, literal_representer)


def parse_datetime_field(raw: str) -> dict | None:
    text = (raw or "").strip()
    if not text:
        return None

    parts = [p.strip() for p in text.split("→")]
    left = parts[0]
    right = parts[1] if len(parts) > 1 else None

    dm = DATE_RE.search(left)
    if not dm:
        return None

    start_date = date(int(dm.group(1)), int(dm.group(2)), int(dm.group(3)))
    tm = TIME_RE.search(left[dm.end() :])
    start_time = time(int(tm.group(1)), int(tm.group(2))) if tm else None

    end_date = start_date
    end_time: time | None = None
    if right:
        dm2 = DATE_RE.search(right)
        if dm2:
            end_date = date(int(dm2.group(1)), int(dm2.group(2)), int(dm2.group(3)))
            tm2 = TIME_RE.search(right[dm2.end() :])
            if tm2:
                end_time = time(int(tm2.group(1)), int(tm2.group(2)))
        else:
            tm2 = TIME_RE.search(right)
            if tm2:
                end_time = time(int(tm2.group(1)), int(tm2.group(2)))

    return {
        "start_date": start_date,
        "end_date": end_date,
        "start_time": start_time,
        "end_time": end_time,
        "all_day": start_time is None,
    }


def build_description(memo: str) -> str:
    return (memo or "").strip()


def row_to_event(row: dict) -> dict | None:
    title = (row.get("名前") or "").strip()
    parsed = parse_datetime_field(row.get("日時") or "")
    if not title or not parsed:
        return None

    event: dict = {
        "title": title,
        "date": parsed["start_date"].isoformat(),
        "all_day": parsed["all_day"],
        "category": "予定",
        "status": "scheduled",
    }

    if parsed["end_date"] != parsed["start_date"]:
        event["end_date"] = parsed["end_date"].isoformat()

    if not parsed["all_day"]:
        event["start_time"] = parsed["start_time"].strftime("%H:%M")
        if parsed["end_time"]:
            event["end_time"] = parsed["end_time"].strftime("%H:%M")

    description = build_description(row.get("メモ") or "")
    if description:
        event["description"] = (
            LiteralStr(description + "\n") if "\n" in description else description
        )

    location = (row.get("場所") or "").strip()
    if location:
        event["location"] = location

    url = (row.get("URL") or "").strip()
    if url:
        event["urls"] = [url]

    tags = (row.get("タグ") or "").strip()
    if tags:
        event["tags"] = [t.strip() for t in re.split(r"[,、]", tags) if t.strip()]

    return event


def years_for_event(event: dict) -> set[int]:
    start = date.fromisoformat(event["date"])
    end = date.fromisoformat(event["end_date"]) if event.get("end_date") else start
    return {start.year, end.year}


def write_year_yaml(path: Path, year: int, events: list[dict]) -> None:
    events_sorted = sorted(
        events,
        key=lambda e: (
            e["date"],
            e.get("start_time") or "",
            e["title"],
        ),
    )
    payload = {
        "year": year,
        "events": events_sorted,
    }
    header = (
        f"# Notionインポート由来のカスタム予定（{year}年）\n"
        "# 祝日は scripts/generate_calendar.py が自動追加します。\n"
        f"# 件数: {len(events_sorted)}\n"
    )
    with path.open("w", encoding="utf-8") as f:
        f.write(header)
        yaml.dump(
            payload,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=1000,
        )


def import_csv(csv_path: Path, out_dir: Path) -> dict[int, int]:
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    by_year: dict[int, list[dict]] = defaultdict(list)
    seen_by_year: dict[int, set[tuple]] = defaultdict(set)

    for row in rows:
        event = row_to_event(row)
        if not event:
            continue
        for year in years_for_event(event):
            key = (
                event["title"],
                event["date"],
                event.get("end_date", ""),
                event.get("start_time", ""),
                event.get("end_time", ""),
                event.get("location", ""),
                event.get("description", ""),
            )
            if key in seen_by_year[year]:
                continue
            seen_by_year[year].add(key)
            by_year[year].append(event)

    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[int, int] = {}
    for year, events in sorted(by_year.items()):
        path = out_dir / f"events.{year}.yaml"
        write_year_yaml(path, year, events)
        counts[year] = len(events)
    return counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="NotionカレンダーCSVを年ごとの YAML に変換します。"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="NotionエクスポートのCSVパス",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "input",
        help="YAML出力先（デフォルト: input/）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    counts = import_csv(args.csv, args.out_dir)
    total = sum(counts.values())
    print(f"取り込み完了: {total} 件（年をまたぐ予定は複数年に重複配置）")
    for year, count in counts.items():
        print(f"  {year}: {count} 件 -> {args.out_dir / f'events.{year}.yaml'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
