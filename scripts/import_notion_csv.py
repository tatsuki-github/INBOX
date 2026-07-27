#!/usr/bin/env python3
"""NotionエクスポートCSVを input/events.YYYY.yaml に取り込む。

対応フォーマット:
- カレンダー系: 名前, 日時, メモ, 場所, URL, タグ
- INBOX系: 名前, 日付, メモ, URL, タグ, 状態, 領域

日付がある行は予定、ない行は日付なしメモとして取り込みます。
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from datetime import date, time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")

STATUS_MAP = {
    "完了": "done",
    "済": "done",
    "done": "done",
    "未着手": "inbox",
    "未対応": "inbox",
    "inbox": "inbox",
    "next": "next",
    "waiting": "waiting",
    "scheduled": "scheduled",
}


class LiteralStr(str):
    """複数行文字列を YAML の | で出すためのマーカー。"""


def literal_representer(dumper: yaml.Dumper, data: LiteralStr):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(LiteralStr, literal_representer)


def maybe_literal(text: str) -> str | LiteralStr:
    if "\n" in text:
        return LiteralStr(text if text.endswith("\n") else text + "\n")
    return text


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


def split_tags(*values: str) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = (value or "").strip()
        if not text:
            continue
        for part in re.split(r"[,、/\n]", text):
            tag = part.strip()
            if tag and tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return tags


def map_status(raw: str, *, is_memo: bool) -> str:
    text = (raw or "").strip()
    if not text:
        return "inbox" if is_memo else "scheduled"
    return STATUS_MAP.get(text, text)


def date_field(row: dict) -> str:
    return (row.get("日時") or row.get("日付") or "").strip()


def row_to_item(row: dict, *, memo_year: int) -> tuple[dict, set[int]] | None:
    title = (row.get("名前") or "").strip()
    if not title:
        return None

    parsed = parse_datetime_field(date_field(row))
    description = (row.get("メモ") or "").strip()
    location = (row.get("場所") or "").strip()
    url = (row.get("URL") or "").strip()
    tags = split_tags(row.get("タグ") or "", row.get("領域") or "")
    status_raw = row.get("状態") or ""

    if parsed is None:
        item: dict = {
            "title": title,
            "category": "メモ",
            "status": map_status(status_raw, is_memo=True),
        }
        if description:
            item["description"] = maybe_literal(description)
        if url:
            item["urls"] = [url]
        if tags:
            item["tags"] = tags
        return item, {memo_year}

    item = {
        "title": title,
        "date": parsed["start_date"].isoformat(),
        "all_day": parsed["all_day"],
        "category": "予定",
        "status": map_status(status_raw, is_memo=False),
    }
    if parsed["end_date"] != parsed["start_date"]:
        item["end_date"] = parsed["end_date"].isoformat()
    if not parsed["all_day"]:
        item["start_time"] = parsed["start_time"].strftime("%H:%M")
        if parsed["end_time"]:
            item["end_time"] = parsed["end_time"].strftime("%H:%M")
    if description:
        item["description"] = maybe_literal(description)
    if location:
        item["location"] = location
    if url:
        item["urls"] = [url]
    if tags:
        item["tags"] = tags

    years = {parsed["start_date"].year, parsed["end_date"].year}
    return item, years


def item_key(item: dict) -> tuple:
    desc = item.get("description") or ""
    if isinstance(desc, str):
        desc = desc.strip()
    return (
        item.get("title", ""),
        item.get("date", ""),
        item.get("end_date", ""),
        item.get("start_time", ""),
        item.get("end_time", ""),
        item.get("location", ""),
        desc,
        tuple(item.get("urls") or []),
    )


def load_existing_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return list(data.get("events") or [])


def write_year_yaml(path: Path, year: int, events: list[dict]) -> None:
    events_sorted = sorted(
        events,
        key=lambda e: (
            e.get("date") is None or e.get("date") == "",
            e.get("date") or "9999-99-99",
            e.get("start_time") or "",
            e.get("title") or "",
        ),
    )
    for event in events_sorted:
        desc = event.get("description")
        if isinstance(desc, str) and "\n" in desc and not isinstance(desc, LiteralStr):
            event["description"] = maybe_literal(desc)

    payload = {
        "year": year,
        "events": events_sorted,
    }
    header = (
        f"# カスタム予定・メモ（{year}年）\n"
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


def import_csv(
    csv_path: Path,
    out_dir: Path,
    *,
    merge: bool,
    memo_year: int,
) -> dict[int, tuple[int, int]]:
    """戻り値: year -> (total_count, newly_added_count)"""
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    incoming: dict[int, list[dict]] = defaultdict(list)
    seen_incoming: dict[int, set[tuple]] = defaultdict(set)

    for row in rows:
        result = row_to_item(row, memo_year=memo_year)
        if not result:
            continue
        item, years = result
        for year in years:
            key = item_key(item)
            if key in seen_incoming[year]:
                continue
            seen_incoming[year].add(key)
            incoming[year].append(item)

    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[int, tuple[int, int]] = {}

    years = set(incoming)
    if merge:
        for path in out_dir.glob("events.*.yaml"):
            suffix = path.name.removeprefix("events.").removesuffix(".yaml")
            if suffix.isdigit():
                years.add(int(suffix))

    for year in sorted(years):
        path = out_dir / f"events.{year}.yaml"
        existing = load_existing_events(path) if merge else []
        existing_keys = {item_key(e) for e in existing}
        added = 0
        merged = list(existing)
        for item in incoming.get(year, []):
            key = item_key(item)
            if key in existing_keys:
                continue
            existing_keys.add(key)
            merged.append(item)
            added += 1
        write_year_yaml(path, year, merged)
        results[year] = (len(merged), added)

    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Notion CSV（予定・INBOXメモ）を年ごとの YAML に変換します。"
    )
    parser.add_argument("--csv", type=Path, required=True, help="NotionエクスポートのCSVパス")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "input",
        help="YAML出力先（デフォルト: input/）",
    )
    parser.add_argument(
        "--merge",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="既存 YAML に追記マージする（デフォルト: する）",
    )
    parser.add_argument(
        "--memo-year",
        type=int,
        default=date.today().year,
        help="日付なしメモの配置年（デフォルト: 今年）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    results = import_csv(
        args.csv,
        args.out_dir,
        merge=args.merge,
        memo_year=args.memo_year,
    )
    added_total = sum(a for _, a in results.values())
    print(
        f"取り込み完了: 新規 {added_total} 件"
        f"（merge={'on' if args.merge else 'off'}, メモ配置年={args.memo_year}）"
    )
    for year, (total, added) in results.items():
        print(
            f"  {year}: 合計 {total} 件（+{added}）"
            f" -> {args.out_dir / f'events.{year}.yaml'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
