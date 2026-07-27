#!/usr/bin/env python3
"""年次カレンダーCSVを生成する（Googleカレンダー / Notion 向け）。"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Iterable

import jpholiday
import yaml

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Event:
    title: str
    start_date: date
    end_date: date
    all_day: bool = True
    start_time: time | None = None
    end_time: time | None = None
    description: str = ""
    location: str = ""
    category: str = ""
    private: bool = False

    def sort_key(self) -> tuple:
        return (
            self.start_date,
            self.start_time or time.min,
            self.title,
        )


def parse_date(value: str | date) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value))


def parse_time(value: str | time | None) -> time | None:
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    text = str(value).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"時刻を解釈できません: {value!r}（HH:MM 形式で指定）")


def format_google_date(d: date) -> str:
    return d.strftime("%m/%d/%Y")


def format_google_time(t: time) -> str:
    return t.strftime("%I:%M %p").lstrip("0")


def holidays_for_year(year: int) -> list[Event]:
    events: list[Event] = []
    for holiday_date, name in jpholiday.year_holidays(year):
        events.append(
            Event(
                title=name,
                start_date=holiday_date,
                end_date=holiday_date,
                all_day=True,
                description="日本の祝日",
                category="祝日",
            )
        )
    return events


def load_custom_events(path: Path, year: int) -> list[Event]:
    if not path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {path}")

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    file_year = data.get("year")
    if file_year is not None and int(file_year) != year:
        print(
            f"警告: 入力の year={file_year} と --year={year} が一致しません",
            file=sys.stderr,
        )

    events: list[Event] = []
    for raw in data.get("events") or []:
        if "title" not in raw or "date" not in raw:
            raise ValueError(f"title と date は必須です: {raw!r}")

        start = parse_date(raw["date"])
        end = parse_date(raw["end_date"]) if raw.get("end_date") else start
        all_day = bool(raw.get("all_day", True))
        start_t = parse_time(raw.get("start_time"))
        end_t = parse_time(raw.get("end_time"))

        if not all_day and start_t is None:
            raise ValueError(f"終日でない予定には start_time が必要です: {raw!r}")

        if start.year != year and end.year != year:
            continue

        events.append(
            Event(
                title=str(raw["title"]),
                start_date=start,
                end_date=end,
                all_day=all_day,
                start_time=start_t,
                end_time=end_t,
                description=str(raw.get("description") or ""),
                location=str(raw.get("location") or ""),
                category=str(raw.get("category") or "予定"),
                private=bool(raw.get("private", False)),
            )
        )
    return events


def merge_events(*groups: Iterable[Event]) -> list[Event]:
    merged = [event for group in groups for event in group]
    merged.sort(key=lambda e: e.sort_key())
    return merged


def write_google_csv(path: Path, events: list[Event]) -> None:
    headers = [
        "Subject",
        "Start Date",
        "Start Time",
        "End Date",
        "End Time",
        "All Day Event",
        "Description",
        "Location",
        "Private",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for event in events:
            row = {
                "Subject": event.title,
                "Start Date": format_google_date(event.start_date),
                "Start Time": "",
                "End Date": format_google_date(event.end_date),
                "End Time": "",
                "All Day Event": "True" if event.all_day else "False",
                "Description": event.description,
                "Location": event.location,
                "Private": "True" if event.private else "False",
            }
            if not event.all_day:
                if event.start_time:
                    row["Start Time"] = format_google_time(event.start_time)
                if event.end_time:
                    row["End Time"] = format_google_time(event.end_time)
            writer.writerow(row)


def write_notion_csv(path: Path, events: list[Event]) -> None:
    headers = [
        "Name",
        "Date",
        "End Date",
        "Category",
        "Description",
        "Location",
        "All Day",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for event in events:
            date_value = event.start_date.isoformat()
            if not event.all_day and event.start_time:
                date_value = (
                    f"{event.start_date.isoformat()}"
                    f"T{event.start_time.strftime('%H:%M:%S')}"
                )
            end_value = event.end_date.isoformat()
            if not event.all_day and event.end_time:
                end_value = (
                    f"{event.end_date.isoformat()}"
                    f"T{event.end_time.strftime('%H:%M:%S')}"
                )
            writer.writerow(
                {
                    "Name": event.title,
                    "Date": date_value,
                    "End Date": end_value,
                    "Category": event.category,
                    "Description": event.description,
                    "Location": event.location,
                    "All Day": "true" if event.all_day else "false",
                }
            )


def write_source_csv(path: Path, events: list[Event]) -> None:
    headers = [
        "title",
        "date",
        "end_date",
        "all_day",
        "start_time",
        "end_time",
        "category",
        "description",
        "location",
        "private",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for event in events:
            writer.writerow(
                {
                    "title": event.title,
                    "date": event.start_date.isoformat(),
                    "end_date": event.end_date.isoformat(),
                    "all_day": "true" if event.all_day else "false",
                    "start_time": event.start_time.strftime("%H:%M")
                    if event.start_time
                    else "",
                    "end_time": event.end_time.strftime("%H:%M")
                    if event.end_time
                    else "",
                    "category": event.category,
                    "description": event.description,
                    "location": event.location,
                    "private": "true" if event.private else "false",
                }
            )


def default_input_path(year: int) -> Path:
    return ROOT / "input" / f"events.{year}.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="年次カレンダーCSVを Google / Notion 向けに生成します。"
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="対象年（例: 2026）",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="カスタム予定YAML（省略時: input/events.YYYY.yaml があれば使用）",
    )
    parser.add_argument(
        "--include-holidays",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="日本の祝日を含める（デフォルト: 含める）",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="出力ディレクトリ（省略時: out/YYYY）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    year: int = args.year
    out_dir: Path = args.out_dir or (ROOT / "out" / str(year))
    out_dir.mkdir(parents=True, exist_ok=True)

    groups: list[list[Event]] = []
    if args.include_holidays:
        groups.append(holidays_for_year(year))

    input_path: Path | None = args.input
    if input_path is None:
        candidate = default_input_path(year)
        if candidate.exists():
            input_path = candidate

    if input_path is not None:
        groups.append(load_custom_events(input_path, year))

    events = merge_events(*groups)
    if not events:
        print("イベントが0件です。祝日かカスタム予定を追加してください。", file=sys.stderr)
        return 1

    google_path = out_dir / "google.csv"
    notion_path = out_dir / "notion.csv"
    source_path = out_dir / "source.csv"

    write_google_csv(google_path, events)
    write_notion_csv(notion_path, events)
    write_source_csv(source_path, events)

    print(f"{year}年: {len(events)} 件のイベントを出力しました")
    print(f"  Google: {google_path}")
    print(f"  Notion: {notion_path}")
    print(f"  Source: {source_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
