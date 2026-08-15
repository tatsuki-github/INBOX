#!/usr/bin/env python3
"""年次カレンダー / INBOX CSV を生成する（Googleカレンダー / Notion 向け）。

日付付き予定に加え、date を省略した日付なしメモも扱えます。
status / tags / urls などの INBOX 用メタデータも出力します。
メモは Notion / source CSV に含まれ、Googleカレンダー用CSVからは除外されます。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Iterable

import jpholiday
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from practice_renderer import render_description as render_practice_description  # noqa: E402


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
    practice: dict[str, Any] | None = None
    template_ref: str = ""

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


def resolve_description(raw: dict) -> str:
    """description と description_file を解決して本文を返す。"""
    description = str(raw.get("description") or "")
    practice = raw.get("practice")
    if practice and isinstance(practice, dict) and (practice.get("items") or practice.get("warmup")):
        if not description.strip():
            description = render_practice_description(practice)
    description_file = str(raw.get("description_file") or "").strip()
    if not description_file:
        return description

    file_path = Path(description_file)
    if not file_path.is_absolute():
        file_path = ROOT / file_path
    if not file_path.exists():
        raise FileNotFoundError(
            f"description_file が見つかりません: {description_file} ({file_path})"
        )

    file_content = file_path.read_text(encoding="utf-8")
    if description:
        return f"{description.rstrip()}\n\n{file_content}"
    return file_content


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
                    description=resolve_description(raw),
                    location=str(raw.get("location") or ""),
                    category=str(raw.get("category") or "メモ"),
                    private=bool(raw.get("private", False)),
                    status=status or "inbox",
                    tags=tags,
                    urls=urls,
                    practice=raw.get("practice") if isinstance(raw.get("practice"), dict) else None,
                    template_ref=str(raw.get("template_ref") or ""),
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
                description=resolve_description(raw),
                location=str(raw.get("location") or ""),
                category=str(raw.get("category") or "予定"),
                private=bool(raw.get("private", False)),
                status=status,
                tags=tags,
                urls=urls,
                practice=raw.get("practice") if isinstance(raw.get("practice"), dict) else None,
                template_ref=str(raw.get("template_ref") or ""),
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


def write_events_json(path: Path, events: list[Event]) -> None:
    payload = []
    for event in events:
        payload.append(
            {
                "title": event.title,
                "date": event.start_date.isoformat() if event.start_date else None,
                "end_date": event.end_date.isoformat() if event.end_date else None,
                "all_day": event.all_day,
                "start_time": event.start_time.strftime("%H:%M") if event.start_time else None,
                "end_time": event.end_time.strftime("%H:%M") if event.end_time else None,
                "category": event.category,
                "status": event.status,
                "tags": event.tags,
                "urls": event.urls,
                "description": event.description,
                "location": event.location,
                "private": event.private,
                "kind": "memo" if event.is_memo else "event",
                "practice": event.practice,
                "template_ref": event.template_ref or None,
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


WEEKDAY_JA = ("月", "火", "水", "木", "金", "土", "日")
MONTH_NAMES_JA = (
    "",
    "1月",
    "2月",
    "3月",
    "4月",
    "5月",
    "6月",
    "7月",
    "8月",
    "9月",
    "10月",
    "11月",
    "12月",
)


def month_anchor_id(month: int) -> str:
    """月見出し用のアンカー ID（GitHub 互換）。"""
    return f"month-{month:02d}"


def page_top_anchor_id() -> str:
    """ページ先頭へ戻るアンカー ID。"""
    return "page-top"


def format_back_to_top_link() -> str:
    """ページ先頭へのリンク。"""
    return f"[↑ページトップ](#{page_top_anchor_id()})"


def format_back_to_month_link(year: int, month: int) -> str:
    """月見出し（カレンダー表）へのリンク。"""
    return f"[↑{year}年{month}月](#{month_anchor_id(month)})"


def format_month_navigation_footer(year: int, month: int) -> str:
    """月セクション末尾の戻りリンク。"""
    return " | ".join(
        [
            format_back_to_month_link(year, month),
            format_back_to_top_link(),
        ]
    )


EMPTY_LABEL = "（なし）"


def display_text(value: str) -> str:
    """空文字はプレースホルダーに置き換える。"""
    text = value.strip()
    return text if text else EMPTY_LABEL


def format_list_value(items: list[str]) -> str:
    """リスト項目を表示用テキストに整形する。"""
    cleaned = [item.strip() for item in items if item.strip()]
    return ", ".join(cleaned) if cleaned else EMPTY_LABEL


def format_time_value(value: time | None) -> str:
    """時刻を表示用テキストに整形する。"""
    return value.strftime("%H:%M") if value else EMPTY_LABEL


def format_bool_label(value: bool) -> str:
    """真偽値を日本語ラベルに変換する。"""
    return "はい" if value else "いいえ"


def format_metadata_lines(pairs: list[tuple[str, str]]) -> list[str]:
    """メタデータの箇条書き行を生成する。"""
    return [f"- **{label}**: {display_text(value)}" for label, value in pairs]


def escape_markdown_table_cell(text: str) -> str:
    """Markdown 表セル内のパイプ・改行をエスケープする。"""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def escape_html(text: str) -> str:
    """HTML 属性・summary 内の特殊文字をエスケープする。"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def event_anchor_id(day: date, index: int) -> str:
    """1日の予定一覧から詳細セクションへ飛ぶアンカー ID。"""
    return f"event-{day.strftime('%Y%m%d')}-{index:02d}"


def memo_anchor_id(index: int) -> str:
    """日付なしメモの詳細セクションへ飛ぶアンカー ID。"""
    return f"memo-{index:04d}"


def event_occurrence_dates(event: Event, year: int) -> list[date]:
    """イベントが表示される日付の一覧（複数日イベントは各日を展開）。"""
    if event.is_memo or event.start_date is None or event.end_date is None:
        return []

    start = max(event.start_date, date(year, 1, 1))
    end = min(event.end_date, date(year, 12, 31))
    if start > end:
        return []

    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def format_markdown_event_summary(event: Event) -> str:
    """予定の短い表示名（リンクテキスト・details の summary 用）。"""
    title = event.title.strip()
    if not event.all_day and event.start_time:
        return f"{event.start_time.strftime('%H:%M')} {title}"
    return title


def format_markdown_event_line(event: Event) -> str:
    """後方互換用。短い表示名のみ返す。"""
    return format_markdown_event_summary(event)


def format_markdown_event_link(event: Event, day: date, index: int) -> str:
    """表セル内の予定リンク。"""
    summary = format_markdown_event_summary(event)
    return f"[{escape_markdown_table_cell(summary)}](#{event_anchor_id(day, index)})"


def format_markdown_event_details_body(event: Event, day: date) -> str:
    """予定 1 件分の詳細本文（Markdown）。全フィールドを常に表示する。"""
    lines = format_metadata_lines(
        [
            ("件名", event.title.strip()),
            ("表示日", day.isoformat()),
            ("開始日", event.start_date.isoformat() if event.start_date else ""),
            ("終了日", event.end_date.isoformat() if event.end_date else ""),
            ("終日", format_bool_label(event.all_day)),
            ("開始時刻", format_time_value(event.start_time)),
            ("終了時刻", format_time_value(event.end_time)),
            ("カテゴリ", event.category),
            ("ステータス", event.status),
            ("タグ", format_list_value(event.tags)),
            ("場所", event.location),
            ("URL", format_list_value(event.urls)),
            ("非公開", format_bool_label(event.private)),
        ]
    )
    lines.extend(["", "**説明**", "", display_text(event.description)])
    return "\n".join(lines)


def format_markdown_event_details_block(event: Event, day: date, index: int) -> str:
    """アンカー付きの予定詳細ブロック（details で折りたたみ）。"""
    summary = format_markdown_event_summary(event)
    body = format_markdown_event_details_body(event, day)
    return (
        f'<a id="{event_anchor_id(day, index)}"></a>\n'
        f"<details>\n"
        f"<summary>{escape_html(summary)}</summary>\n\n"
        f"{body}\n\n"
        f"</details>"
    )


def format_markdown_memo_details_body(memo: Event) -> str:
    """日付なしメモ 1 件分の詳細本文（Markdown）。全フィールドを常に表示する。"""
    lines = format_metadata_lines(
        [
            ("件名", memo.title.strip()),
            ("カテゴリ", memo.category),
            ("ステータス", memo.status),
            ("タグ", format_list_value(memo.tags)),
            ("URL", format_list_value(memo.urls)),
        ]
    )
    lines.extend(["", "**内容**", "", display_text(memo.description)])
    return "\n".join(lines)


def format_markdown_memo_details_block(memo: Event, index: int) -> str:
    """アンカー付きのメモ詳細ブロック（details で折りたたみ）。"""
    body = format_markdown_memo_details_body(memo)
    return (
        f'<a id="{memo_anchor_id(index)}"></a>\n'
        f"<details>\n"
        f"<summary>{escape_html(memo.title.strip())}</summary>\n\n"
        f"{body}\n\n"
        f"</details>"
    )


def group_events_by_date(events: list[Event], year: int) -> dict[date, list[Event]]:
    """年の各日付に、その日に表示すべきイベントを割り当てる。"""
    grouped: dict[date, list[Event]] = {}
    for event in events:
        for day in event_occurrence_dates(event, year):
            grouped.setdefault(day, []).append(event)

    for day_events in grouped.values():
        day_events.sort(
            key=lambda event: (
                event.all_day,
                event.start_time or time.min,
                event.title,
            )
        )
    return grouped


def render_markdown_calendar(events: list[Event], year: int) -> str:
    """年次 Markdown カレンダー本文を生成する。"""
    grouped = group_events_by_date(events, year)
    memos = [event for event in events if event.is_memo]

    months_with_events = sorted(
        {
            day.month
            for day in grouped
            if day.year == year
        }
    )

    lines = [
        f'<a id="{page_top_anchor_id()}"></a>',
        f"# {year}年カレンダー",
        "",
    ]

    if months_with_events:
        month_links = " | ".join(
            f"[{MONTH_NAMES_JA[month]}](#{month_anchor_id(month)})"
            for month in months_with_events
        )
        lines.append(month_links)
        lines.append("")

    for month in months_with_events:
        month_days = [
            day
            for day in sorted(grouped)
            if day.year == year and day.month == month
        ]

        lines.append(f'<a id="{month_anchor_id(month)}"></a>')
        lines.append(f"## {year}年{month}月")
        lines.append("")
        lines.append("| 日 | 曜 | 予定 |")
        lines.append("| --- | --- | --- |")

        for day in month_days:
            weekday = WEEKDAY_JA[day.weekday()]
            entries = " / ".join(
                format_markdown_event_link(event, day, index)
                for index, event in enumerate(grouped[day])
            )
            lines.append(
                f"| {day.day} | {weekday} | {entries} |"
            )
        lines.append("")

        month_detail_blocks: list[str] = []
        for day in month_days:
            for index, event in enumerate(grouped[day]):
                month_detail_blocks.append(
                    format_markdown_event_details_block(event, day, index)
                )
        if month_detail_blocks:
            lines.append("### 予定詳細")
            lines.append("")
            lines.append("\n\n---\n\n".join(month_detail_blocks))
            lines.append("")
            lines.append(format_month_navigation_footer(year, month))
            lines.append("")

    if memos:
        lines.append('<a id="memos"></a>')
        lines.append("## 日付なしメモ")
        lines.append("")
        for index, memo in enumerate(memos):
            lines.append(f"- [{escape_markdown_table_cell(memo.title)}](#{memo_anchor_id(index)})")
        lines.append("")
        lines.append("### メモ詳細")
        lines.append("")
        lines.append("\n\n---\n\n".join(
            format_markdown_memo_details_block(memo, index)
            for index, memo in enumerate(memos)
        ))
        lines.append("")
        lines.append(format_back_to_top_link())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_markdown_calendar(path: Path, events: list[Event], year: int) -> None:
    path.write_text(render_markdown_calendar(events, year), encoding="utf-8")


def root_calendar_path() -> Path:
    """リポジトリルートの今年用 calendar.md。"""
    return ROOT / "calendar.md"


def maybe_write_root_calendar(
    events: list[Event],
    year: int,
    *,
    calendar_path: Path,
    root_path: Path | None = None,
) -> Path | None:
    """対象年が今年なら、ルートにも calendar.md を出力する。"""
    if year != date.today().year:
        return None

    destination = root_path or root_calendar_path()
    destination.write_text(calendar_path.read_text(encoding="utf-8"), encoding="utf-8")
    return destination


def default_input_path(year: int) -> Path:
    return ROOT / "input" / f"events.{year}.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="年次カレンダー / INBOX CSV を Google / Notion 向けに生成します。"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="対象年（例: 2026）。--all-years 指定時は不要",
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
    parser.add_argument(
        "--all-years",
        action="store_true",
        help="input/events.*.yaml があるすべての年を生成（--year 不要）",
    )
    return parser


def discover_years() -> list[int]:
    years: list[int] = []
    for path in sorted((ROOT / "input").glob("events.*.yaml")):
        suffix = path.name.removeprefix("events.").removesuffix(".yaml")
        if suffix.isdigit():
            years.append(int(suffix))
    return years


def generate_year(
    year: int,
    *,
    input_path: Path | None,
    include_holidays: bool,
    out_dir: Path,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)

    groups: list[list[Event]] = []
    if include_holidays:
        groups.append(holidays_for_year(year))

    resolved_input = input_path
    if resolved_input is None:
        candidate = default_input_path(year)
        if candidate.exists():
            resolved_input = candidate

    if resolved_input is not None:
        groups.append(load_custom_events(resolved_input, year))

    events = merge_events(*groups)
    if not events:
        print(
            f"{year}年: イベントが0件です。祝日かカスタム予定を追加してください。",
            file=sys.stderr,
        )
        return 1

    google_path = out_dir / "google.csv"
    notion_path = out_dir / "notion.csv"
    source_path = out_dir / "source.csv"
    events_json_path = out_dir / "events.json"
    calendar_path = out_dir / "calendar.md"

    skipped_memos = write_google_csv(google_path, events)
    write_notion_csv(notion_path, events)
    write_source_csv(source_path, events)
    write_events_json(events_json_path, events)
    write_markdown_calendar(calendar_path, events, year)
    root_calendar = maybe_write_root_calendar(events, year, calendar_path=calendar_path)

    try:
        from export_practice import generate_for_year, generate_kpace_global

        generate_for_year(year, out_dir=out_dir)
        generate_kpace_global([year])
    except Exception as exc:
        print(f"警告: 練習エクスポートに失敗: {exc}", file=sys.stderr)

    memo_count = sum(1 for e in events if e.is_memo)
    event_count = len(events) - memo_count
    print(f"{year}年: {len(events)} 件（予定 {event_count} / メモ {memo_count}）を出力しました")
    print(f"  Google: {google_path}（メモ {skipped_memos} 件は除外）")
    print(f"  Notion: {notion_path}")
    print(f"  Source: {source_path}")
    print(f"  Events JSON: {events_json_path}")
    print(f"  Practice: {out_dir / 'practice.json'}")
    print(f"  Calendar: {calendar_path}")
    if root_calendar is not None:
        print(f"  Root calendar: {root_calendar}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.all_years:
        years = discover_years()
        if not years:
            print("input/events.YYYY.yaml が見つかりません。", file=sys.stderr)
            return 1
        exit_code = 0
        for year in years:
            code = generate_year(
                year,
                input_path=args.input,
                include_holidays=args.include_holidays,
                out_dir=(args.out_dir / str(year))
                if args.out_dir
                else (ROOT / "out" / str(year)),
            )
            exit_code = exit_code or code
        return exit_code

    if args.year is None:
        print("--year または --all-years を指定してください。", file=sys.stderr)
        return 2

    return generate_year(
        args.year,
        input_path=args.input,
        include_holidays=args.include_holidays,
        out_dir=args.out_dir or (ROOT / "out" / str(args.year)),
    )


if __name__ == "__main__":
    raise SystemExit(main())
