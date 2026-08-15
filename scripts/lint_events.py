#!/usr/bin/env python3
"""Validate events YAML against JSON Schema and practice conventions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input"
SCHEMAS_DIR = ROOT / "schemas"
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from practice_models import INTENSITIES, MACHINE_TAG_PREFIXES, PRACTICE_TYPES
from practice_utils import is_practice_event, tags_list

PRACTICE_ITEM_SCHEMA = json.loads((SCHEMAS_DIR / "practice-item.schema.json").read_text(encoding="utf-8"))


def load_event_schema() -> dict:
    return json.loads((SCHEMAS_DIR / "event.schema.json").read_text(encoding="utf-8"))


def schema_store() -> dict:
    return {
        "event.schema.json": load_event_schema(),
        "practice-item.schema.json": PRACTICE_ITEM_SCHEMA,
    }


def validate_event(ev: dict) -> None:
    store = schema_store()
    resolver = jsonschema.RefResolver.from_schema(store["event.schema.json"], store=store)
    jsonschema.validate(ev, store["event.schema.json"], resolver=resolver)


def validate_tags(tags: list[str], title: str) -> list[str]:
    errors: list[str] = []
    for tag in tags:
        if any(tag.startswith(p) for p in MACHINE_TAG_PREFIXES):
            if tag.startswith("practice:") and tag not in {
                "practice:daiming",
                "practice:personal",
            }:
                errors.append(f"{title}: 未知の practice タグ {tag}")
            if tag.startswith("session:") and tag not in {"session:morning", "session:evening"}:
                errors.append(f"{title}: 未知の session タグ {tag}")
    return errors


def validate_practice_block(title: str, practice: dict) -> list[str]:
    errors: list[str] = []
    for idx, item in enumerate(practice.get("items") or []):
        try:
            jsonschema.validate(item, PRACTICE_ITEM_SCHEMA)
        except jsonschema.ValidationError as exc:
            errors.append(f"{title}: practice.items[{idx}] — {exc.message}")
        itype = item.get("type")
        if itype and itype not in PRACTICE_TYPES:
            errors.append(f"{title}: 未知の type {itype}")
        intensity = item.get("intensity")
        if intensity and intensity not in INTENSITIES:
            errors.append(f"{title}: 未知の intensity {intensity}")
        pace = item.get("pace")
        if pace and not re.fullmatch(r"k/\d+:\d{2}", pace):
            errors.append(f"{title}: pace 形式不正 {pace}")
    absentees = practice.get("absentees")
    if absentees is not None:
        if not isinstance(absentees, list):
            errors.append(f"{title}: absentees は配列である必要があります")
        else:
            for idx, name in enumerate(absentees):
                if not isinstance(name, str) or not name.strip():
                    errors.append(f"{title}: absentees[{idx}] が空です")
    return errors


def lint_year(year: int, *, strict_practice: bool = True) -> list[str]:
    path = INPUT_DIR / f"events.{year}.yaml"
    if not path.exists():
        return [f"ファイルなし: {path}"]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for ev in data.get("events") or []:
        title = ev.get("title", "?")
        try:
            validate_event(ev)
        except jsonschema.ValidationError as exc:
            errors.append(f"{title}: {exc.message}")
        errors.extend(validate_tags(tags_list(ev), title))
        if ev.get("practice") and strict_practice:
            errors.extend(validate_practice_block(title, ev["practice"]))
        if is_practice_event(ev) and ev.get("practice") and ev.get("description"):
            # warn if description lacks any pace from practice items
            for item in ev["practice"].get("items") or []:
                pace = item.get("pace")
                if pace and pace not in ev.get("description", ""):
                    errors.append(f"{title}: description に pace {pace} が見つかりません（警告）")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="events YAML を lint")
    parser.add_argument("--year", type=int, action="append")
    parser.add_argument("--all-years", action="store_true")
    args = parser.parse_args(argv)

    years = args.year or []
    if args.all_years or not years:
        years = sorted(
            int(p.name.split(".")[1])
            for p in INPUT_DIR.glob("events.*.yaml")
            if p.name.split(".")[1].isdigit()
        )

    exit_code = 0
    for year in years:
        errors = lint_year(year)
        if errors:
            print(f"=== {year} ===")
            for err in errors:
                print(err)
            exit_code = 1
        else:
            print(f"{year}: OK")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
