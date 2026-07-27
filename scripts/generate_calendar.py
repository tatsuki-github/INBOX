#!/usr/bin/env python3
"""年次カレンダー / INBOX CSV を生成する（Googleカレンダー / Notion 向け）。

日付付き予定に加え、date を省略した日付なしメモも扱えます。
status / tags / urls などの INBOX 用メタデータも出力します。
メモは Notion / source CSV に含まれ、Googleカレンダー用CSVからは除外されます。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Iterable

import jpholiday
import yaml

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Event:
    title: str
    start_date: date | None = None
    end_date: date | None = None
    all_day: bool = True
    start_time: time | None = None
    end_time: time | None = None
    description: str = ""
    location: str = ""
    category: str = ""
    private: bool = False
    status: str = ""
    tags: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)

    @property
    def is_memo(self) -> bool:
        """日付がないエントリはメモ扱い。"""
        return self.start_date is None

    def sort_key(self) -> tuple:
        # 日付なしメモは末尾にまとめる
        return (
            self.start_date is None,
            self.start_date or date.max,
            self.start_time or time.min,
            self.title,
        )

    def tags_csv(self) -> str:
        return ", ".join(self.tags)

    def urls_csv(self, sep: str = "\n") -> str:
        return sep.join(self.urls)

    def google_description(self) -> str:
        """Google CSV 用。専用列がないメタデータを Description に付与。"""
        parts: list[str] = []
        if self.description:
            parts.append(self.description)
        meta: list[str] = []
        if self.status:
            meta.append(f"Status: {self.status}")
        if self.tags:
            meta.append(f"Tags: {self.tags_csv()}")
        if self.urls:
            meta.append("URLs:\n" + "\n".join(f"- {u}" for u in self.urls))
        if meta:
            parts.append("\n".join(meta))
        return "\n\n".join(parts)


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


def parse_string_list(value: object, field_name: str) -> list[str]:
    """tags / urls 用。文字列（カンマ/改行区切り）またはリストを受け付ける。"""
    if value is None or value == "":
        return []
    if isinstance(value, str):
        parts = re.split(r"[\n,]", value)
        return [p.strip() for p in parts if p.strip()]
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                items.append(text)
        return items
    raise ValueError(f"{field_name} は文字列またはリストで指定してください: {value!r}")


def parse_status(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_inbox_fields(raw: dict) -> tuple[str, list[str], list[str]]:
    status = parse_status(raw.get("status"))
    tags = parse_string_list(raw.get("tags"), "tags")
    urls = parse_string_list(raw.get("urls"), "urls")
    # 単数形 url も許容
    if raw.get("url"):
        for item in parse_string_list(raw.get("url"), "url"):
            if item not in urls:
                urls.append(item)
    return status, tags, urls


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
                status="",
                tags=["holiday"],
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
        if "title" not in raw:
            raise ValueError(f"title は必須です: {raw!r}")

        raw_date = raw.get("date")
        is_memo = raw_date is None or raw_date == ""
        status, tags, urls = parse_inbox_fields(raw)

        # type: memo を明示しても可（date があってもメモ扱いはしない。date 優先）
        explicit_memo = str(raw.get("type") or "").strip().lower() in {
            "memo",
            "note",
            "メモ",
        }
        if explicit_memo and not is_memo:
            print(
                f"警告: type=memo だが date があるため予定として扱います: {raw!r}",
                file=sys.stderr,
            )

        if is_memo:
            if raw.get("start_time") or raw.get("end_time") or raw.get("end_date"):
                raise ValueError(
                    f"日付なしメモには start_time / end_time / end_date を指定できません: {raw!r}"
                )
            events.append(
                Event(
                    title=str(raw["title"]),
                    start_date=None,
                    end_date=None,
                    all_day=True,
                    description=str(raw.get("description") or ""),
                    location=str(raw.get("location") or ""),
                    category=str(raw.get("category") or "メモ"),
                    private=bool(raw.get("private", False)),
                    status=status or "inbox",
                    tags=tags,
                    urls=urls,
                )
            )
            continue

        start = parse_date(raw_date)
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
                status=status,
                tags=tags,
                urls=urls,
            )
        )
    return events


def merge_events(*groups: Iterable[Event]) -> list[Event]:
    merged = [event for group in groups for event in group]
    merged.sort(key=lambda e: e.sort_key())
    return merged


def write_google_csv(path: Path, events: list[Event]) -> int:
    """日付付き予定のみ書き出す。戻り値はスキップしたメモ件数。"""
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
    skipped = 0
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for event in events:
            if event.is_memo or event.start_date is None or event.end_date is None:
                skipped += 1
                continue
            row = {
                "Subject": event.title,
                "Start Date": format_google_date(event.start_date),
                "Start Time": "",
                "End Date": format_google_date(event.end_date),
                "End Time": "",
                "All Day Event": "True" if event.all_day else "False",
                "Description": event.google_description(),
                "Location": event.location,
                "Private": "True" if event.private else "False",
            }
            if not event.all_day:
                if event.start_time:
                    row["Start Time"] = format_google_time(event.start_time)
                if event.end_time:
                    row["End Time"] = format_google_time(event.end_time)
            writer.writerow(row)
    return skipped


def write_notion_csv(path: Path, events: list[Event]) -> None:
    headers = [
        "Name",
        "Date",
        "End Date",
        "Category",
        "Status",
        "Tags",
        "URLs",
        "Description",
        "Location",
        "All Day",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for event in events:
            if event.is_memo or event.start_date is None:
                writer.writerow(
                    {
                        "Name": event.title,
                        "Date": "",
                        "End Date": "",
                        "Category": event.category,
                        "Status": event.status,
                        "Tags": event.tags_csv(),
                        "URLs": event.urls_csv(),
                        "Description": event.description,
                        "Location": event.location,
                        "All Day": "",
                    }
                )
                continue

            date_value = event.start_date.isoformat()
            if not event.all_day and event.start_time:
                date_value = (
                    f"{event.start_date.isoformat()}"
                    f"T{event.start_time.strftime('%H:%M:%S')}"
                )
            end_value = event.end_date.isoformat() if event.end_date else ""
            if not event.all_day and event.end_time and event.end_date:
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
                    "Status": event.status,
                    "Tags": event.tags_csv(),
                    "URLs": event.urls_csv(),
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
        "status",
        "tags",
        "urls",
        "description",
        "location",
        "private",
        "kind",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for event in events:
            writer.writerow(
                {
                    "title": event.title,
                    "date": event.start_date.isoformat() if event.start_date else "",
                    "end_date": event.end_date.isoformat() if event.end_date else "",
                    "all_day": ""
                    if event.is_memo
                    else ("true" if event.all_day else "false"),
                    "start_time": event.start_time.strftime("%H:%M")
                    if event.start_time
                    else "",
                    "end_time": event.end_time.strftime("%H:%M")
                    if event.end_time
                    else "",
                    "category": event.category,
                    "status": event.status,
                    "tags": event.tags_csv(),
                    "urls": event.urls_csv(sep=" | "),
                    "description": event.description,
                    "location": event.location,
                    "private": "true" if event.private else "false",
                    "kind": "memo" if event.is_memo else "event",
                }
            )


def default_input_path(year: int) -> Path:
    return ROOT / "input" / f"events.{year}.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="年次カレンダー / INBOX CSV を Google / Notion 向けに生成します。"
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

    skipped_memos = write_google_csv(google_path, events)
    write_notion_csv(notion_path, events)
    write_source_csv(source_path, events)

    memo_count = sum(1 for e in events if e.is_memo)
    event_count = len(events) - memo_count
    print(f"{year}年: {len(events)} 件（予定 {event_count} / メモ {memo_count}）を出力しました")
    print(f"  Google: {google_path}（メモ {skipped_memos} 件は除外）")
    print(f"  Notion: {notion_path}")
    print(f"  Source: {source_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
