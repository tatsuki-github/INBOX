#!/usr/bin/env python3
"""400mインターバル練習記録CSVを events.YYYY.yaml に登録する。"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TITLE = "遅めの400mインターバル"
TAGS = ["自分の練習"]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


def event_matches_import(raw: dict, description: str) -> bool:
    if raw.get("title") != "自分の練習":
        return False
    existing = str(raw.get("description") or "")
    if "400m" in existing or "400m" in description:
        return True
    return normalize_text(existing) == normalize_text(description)


def make_event(date_iso: str, description: str) -> dict:
    return {
        "title": TITLE,
        "date": date_iso,
        "all_day": True,
        "category": "予定",
        "status": "done",
        "tags": TAGS.copy(),
        "description": description,
    }


def update_header_comment(path: Path, count: int) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"^# 件数: \d+$",
        f"# 件数: {count}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    path.write_text(text, encoding="utf-8")


def import_rows(csv_path: Path) -> dict[int, int]:
    stats: dict[int, int] = {}
    rows: list[tuple[str, str]] = []

    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_date = row["年月日"].strip()
            result = row["結果"].strip()
            date_iso = datetime.strptime(raw_date, "%Y%m%d").date().isoformat()
            rows.append((date_iso, result))

    by_year: dict[int, list[tuple[str, str]]] = {}
    for date_iso, result in rows:
        year = int(date_iso[:4])
        by_year.setdefault(year, []).append((date_iso, result))

    for year, year_rows in sorted(by_year.items()):
        path = ROOT / "input" / f"events.{year}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"入力ファイルが見つかりません: {path}")

        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        events = list(data.get("events") or [])
        updated = 0
        added = 0

        for date_iso, result in year_rows:
            matched = False
            for raw in events:
                if raw.get("date") != date_iso:
                    continue
                if not event_matches_import(raw, result):
                    continue
                raw["title"] = TITLE
                raw["tags"] = TAGS.copy()
                raw["description"] = result
                raw["status"] = "done"
                raw["category"] = raw.get("category") or "予定"
                raw["all_day"] = True
                matched = True
                updated += 1
                break

            if not matched:
                events.append(make_event(date_iso, result))
                added += 1

        data["events"] = events
        data["year"] = year

        header = (
            f"# カスタム予定・メモ（{year}年）\n"
            f"# 祝日は scripts/generate_calendar.py が自動追加します。\n"
            f"# 件数: {len(events)}\n"
        )
        body = yaml.dump(
            data,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=1000,
        )
        path.write_text(header + body, encoding="utf-8")
        stats[year] = updated + added
        print(f"{year}: updated={updated}, added={added}, total={len(events)}")

    return stats


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="400mインターバルCSVをYAMLへ取り込む")
    parser.add_argument("csv", type=Path, help="取り込むCSVファイル")
    args = parser.parse_args()
    import_rows(args.csv)


if __name__ == "__main__":
    main()
