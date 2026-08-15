#!/usr/bin/env python3
"""Export practice data to JSON, CSV, and Markdown summaries."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from practice_models import LegacyItem, ParseResult
from practice_parser import parse_event
from practice_renderer import render_description, render_legacy_item
from practice_utils import is_practice_event, tags_list

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "input"
TEMPLATES_PATH = INPUT_DIR / "practice_templates.yaml"
KPACE_PATH = ROOT / "out" / "daiming-practice-menus-kpace.md"
PRACTICE_YEARS = [2020, 2022, 2023, 2024, 2025, 2026, 2027]


def load_templates() -> list[dict[str, Any]]:
    if not TEMPLATES_PATH.exists():
        return []
    with TEMPLATES_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("templates") or []


def practice_records_from_events(events: list[dict], year: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for ev in events:
        if not is_practice_event(ev):
            continue
        parsed = parse_event(ev)
        if ev.get("practice"):
            practice = ev["practice"]
            source = "practice_field"
            confidence = "full"
        else:
            practice = parsed.practice
            source = parsed.source
            confidence = parsed.confidence
        if not practice.get("items") and not parsed.skipped and not (ev.get("description") or "").strip():
            continue
        records.append(
            {
                "year": year,
                "date": ev.get("date"),
                "title": ev.get("title"),
                "start_time": ev.get("start_time"),
                "end_time": ev.get("end_time"),
                "status": ev.get("status"),
                "tags": tags_list(ev),
                "practice": practice,
                "parse": {
                    "source": source,
                    "confidence": confidence,
                    "skipped": parsed.skipped,
                },
                "template_ref": ev.get("template_ref"),
            }
        )
    return records


def flatten_items(record: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    practice = record.get("practice") or {}
    parse = record.get("parse") or {}
    absentees = practice.get("absentees")
    absentees_str = "、".join(absentees) if absentees else ""
    for item in practice.get("items") or []:
        rows.append(
            {
                "year": record.get("year"),
                "date": record.get("date") or "",
                "title": record.get("title") or "",
                "type": item.get("type"),
                "group": item.get("group") or "",
                "distance_m": item.get("distance_m") or "",
                "distance_km": item.get("distance_km") or "",
                "laps": item.get("laps") or "",
                "reps": item.get("reps") or "",
                "pace": item.get("pace") or "",
                "intensity": item.get("intensity") or "",
                "rest_sec": item.get("rest_sec") or "",
                "rest": item.get("rest") or "",
                "label": item.get("label") or "",
                "absentees": absentees_str,
                "parse_source": parse.get("source") or "",
                "parse_confidence": parse.get("confidence") or "",
            }
        )
    return rows


def flatten_absentees(record: dict[str, Any]) -> list[dict[str, Any]]:
    practice = record.get("practice") or {}
    absentees = practice.get("absentees")
    if not absentees:
        return []
    return [
        {
            "year": record.get("year"),
            "date": record.get("date") or "",
            "title": record.get("title") or "",
            "name": name,
        }
        for name in absentees
    ]


def write_practice_json(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_practice_items_csv(path: Path, records: list[dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    for rec in records:
        rows.extend(flatten_items(rec))
    headers = [
        "year", "date", "title", "type", "group", "distance_m", "distance_km",
        "laps", "reps", "pace", "intensity", "rest_sec", "rest", "label",
        "absentees", "parse_source", "parse_confidence",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def write_practice_absentees_csv(path: Path, records: list[dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    for rec in records:
        rows.extend(flatten_absentees(rec))
    headers = ["year", "date", "title", "name"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def render_kpace_markdown(all_records: list[dict[str, Any]]) -> str:
    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for rec in all_records:
        by_year[rec["year"]].append(rec)

    lines = [
        "# 岱明練習メニュー一覧（k/表記）",
        "",
        "- トラック1周 = **560m**",
        "- 距離と時間の両方が判明する項目のみ k/M:SS に変換",
        "- **parsed**: full / partial / none",
        "",
    ]
    for year in PRACTICE_YEARS:
        lines += ["", f"## {year}年", ""]
        year_records = sorted(by_year.get(year, []), key=lambda r: (r.get("date") or "9999", r.get("title") or ""))
        if not year_records:
            lines += ["（岱明練習メニューの記録なし）", ""]
            continue
        for rec in year_records:
            date = rec.get("date") or "（日付なし）"
            title = rec.get("title") or ""
            parse = rec.get("parse") or {}
            conf = parse.get("confidence") or "none"
            absentees = (rec.get("practice") or {}).get("absentees")
            absentee_note = ""
            if absentees is not None:
                absentee_note = "なし" if not absentees else "、".join(absentees)
            lines += [f"### {date} {title}", "", f"- **parsed**: {conf} ({parse.get('source', 'none')})"]
            if absentee_note:
                lines += [f"- **absentees**: {absentee_note}"]
            lines += [""]
            items = (rec.get("practice") or {}).get("items") or []
            if items:
                lines += ["| type | group | detail | pace |", "|---|---|---|---|"]
                for item in items:
                    detail = item.get("label") or ""
                    if item.get("distance_m"):
                        detail = f"{item['distance_m']}m"
                    elif item.get("distance_km"):
                        detail = f"{item['distance_km']}km"
                    elif item.get("segments"):
                        detail = "+".join(str(s.get("distance_m")) + "m" for s in item["segments"])
                    lines.append(
                        f"| {item.get('type','')} | {item.get('group') or ''} | {detail} | {item.get('pace') or item.get('intensity') or ''} |"
                    )
            for sk in parse.get("skipped") or []:
                lines.append(f"- ※ skipped: {sk}")
            if not items and not parse.get("skipped"):
                lines.append("（換算対象なし）")
            lines.append("")
    return "\n".join(lines)


def render_summary_md(records: list[dict[str, Any]], year: int, templates: list[dict]) -> str:
    by_month: dict[str, list[dict]] = defaultdict(list)
    type_counter: Counter[str] = Counter()
    unparsed: list[str] = []

    for rec in records:
        if rec.get("year") != year:
            continue
        date = rec.get("date") or ""
        month = date[:7] if date else "（日付なし）"
        by_month[month].append(rec)
        parse = rec.get("parse") or {}
        items = (rec.get("practice") or {}).get("items") or []
        if not items:
            unparsed.append(f"{date} {rec.get('title')} — {parse.get('confidence', 'none')}")
        for item in items:
            type_counter[str(item.get("type") or "other")] += 1

    lines = [
        f"# {year}年 練習サマリー",
        "",
        "## 距離種別頻度",
        "",
        "| type | count |",
        "|---|---|",
    ]
    for t, c in sorted(type_counter.items()):
        lines.append(f"| {t} | {c} |")

    lines += ["", "## 月別セッション", ""]
    for month in sorted(by_month.keys()):
        lines += [f"### {month}", ""]
        for rec in sorted(by_month[month], key=lambda r: (r.get("date") or "", r.get("title") or "")):
            n = len((rec.get("practice") or {}).get("items") or [])
            conf = (rec.get("parse") or {}).get("confidence", "none")
            lines.append(f"- {rec.get('date') or '—'} {rec.get('title')} ({n} items, {conf})")
        lines.append("")

    if unparsed:
        lines += ["## 未パース / 項目なし", ""]
        for row in unparsed:
            lines.append(f"- {row}")
        lines.append("")

    if templates:
        lines += ["## テンプレート一覧", ""]
        for tmpl in templates:
            lines.append(f"- `{tmpl.get('id')}` — {tmpl.get('label')}")
        lines.append("")

    return "\n".join(lines)


def generate_for_year(year: int, *, out_dir: Path | None = None) -> dict[str, Path]:
    path = INPUT_DIR / f"events.{year}.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    records = practice_records_from_events(data.get("events") or [], year)
    target = out_dir or (ROOT / "out" / str(year))
    target.mkdir(parents=True, exist_ok=True)
    outputs = {
        "practice_json": target / "practice.json",
        "practice_csv": target / "practice_items.csv",
        "practice_absentees_csv": target / "practice_absentees.csv",
        "summary_md": target / "practice-summary.md",
    }
    write_practice_json(outputs["practice_json"], records)
    write_practice_items_csv(outputs["practice_csv"], records)
    write_practice_absentees_csv(outputs["practice_absentees_csv"], records)
    templates = load_templates()
    outputs["summary_md"].write_text(render_summary_md(records, year, templates), encoding="utf-8")
    return outputs


def generate_kpace_global(years: list[int] | None = None) -> Path:
    years = years or PRACTICE_YEARS
    all_records: list[dict[str, Any]] = []
    for year in years:
        path = INPUT_DIR / f"events.{year}.yaml"
        if not path.exists():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        all_records.extend(practice_records_from_events(data.get("events") or [], year))
    KPACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    KPACE_PATH.write_text(render_kpace_markdown(all_records), encoding="utf-8")
    return KPACE_PATH


def generate_all(out_root: Path | None = None) -> None:
    for year in PRACTICE_YEARS:
        path = INPUT_DIR / f"events.{year}.yaml"
        if path.exists():
            generate_for_year(year, out_dir=(out_root or ROOT / "out") / str(year))
    generate_kpace_global()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="練習データを JSON/CSV/Markdown にエクスポート")
    parser.add_argument("--year", type=int, action="append")
    parser.add_argument("--all-years", action="store_true")
    args = parser.parse_args(argv)

    if args.all_years or not args.year:
        generate_all()
    else:
        for year in args.year:
            generate_for_year(year)
        generate_kpace_global(args.year)
    print("Export complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
