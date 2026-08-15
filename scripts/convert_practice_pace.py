#!/usr/bin/env python3
"""岱明練習メニューを k/M:SS 表記に変換して一覧出力・YAML反映する。

薄いラッパー: 実処理は export_practice / practice_parser に委譲。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from backfill_practice import backfill_year
from export_practice import KPACE_PATH, generate_kpace_global

APPLY_YEARS = [2025, 2026]
PRACTICE_YEARS = [2020, 2022, 2023, 2024, 2025, 2026, 2027]

# 後方互換: 他スクリプトから import されるシンボル
from practice_models import LAP_M, LegacyItem  # noqa: E402,F401
from practice_parser import convert_description, parse_event  # noqa: E402,F401
from practice_utils import is_practice_event as is_practice  # noqa: E402,F401
from yaml_io import dump_event, write_events_yaml  # noqa: E402,F401


def apply_to_yaml(years: list[int] | None = None) -> int:
    years = years or APPLY_YEARS
    total = 0
    for year in years:
        updated, _, _ = backfill_year(year, apply=True, embed_comment=True)
        total += updated
    print(f"Descriptions/practice updated: {total}")
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="岱明練習メニューを k/表記に変換")
    parser.add_argument("--apply", action="store_true", help="input/events.*.yaml を更新")
    parser.add_argument("--year", type=int, action="append", help="--apply 時の対象年")
    args = parser.parse_args()

    if args.apply:
        apply_to_yaml(args.year or APPLY_YEARS)

    path = generate_kpace_global(PRACTICE_YEARS)
    print(f"{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
