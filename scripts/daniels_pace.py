#!/usr/bin/env python3
"""Daniels VDOT / training-pace / Golden Zone calculator CLI.

Agents MUST run this (or import daniels_calculator) when answering GZ or sub-threshold
pace questions — do not estimate from 10K pace or generic web tables.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ai.daniels_calculator import (  # noqa: E402
    build_daniels_block,
    calculate_from_race,
    calculate_from_t_pace,
    fmt_pace,
)


def _print_summary(result: dict) -> None:
    p = result["paces"]
    e_lo, e_hi = p["E"]
    print(f"VDOT: {result['vdot']:.1f}")
    print(f"根拠: {result['distance_label']} {result['time_display']}")
    print()
    print("【Daniels トレーニングペース】")
    print(f"  E (Easy):       {fmt_pace(e_lo)}〜{fmt_pace(e_hi)}/km")
    print(f"  M (Marathon):   {fmt_pace(p['M'])}/km")
    print(f"  T (Threshold):  {fmt_pace(p['T'])}/km  ← GZ の基準")
    print(f"  I (Interval):   {fmt_pace(p['I'])}/km")
    print(f"  R (Rep):        {fmt_pace(p['R'])}/km")
    print()
    print("【サブ閾値 / ゴールデンゾーン】")
    print("  Daniels T ペースより遅い（T+8〜25秒/km、インターバル長で変動）")
    print("  詳細は下記 GZ ブロック参照")
    print()
    print(result["golden_zone_block"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Daniels VDOT calculator + Norwegian Golden Zone tables"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--race",
        nargs=2,
        metavar=("DISTANCE", "TIME"),
        help='Race result, e.g. --race 1500m 4:20',
    )
    group.add_argument(
        "--t-pace",
        metavar="PACE",
        help="Known Daniels T pace (min:sec/km), e.g. --t-pace 3:29",
    )
    parser.add_argument(
        "--format",
        choices=("summary", "block", "json"),
        default="summary",
        help="Output format (default: summary)",
    )
    args = parser.parse_args(argv)

    if args.race:
        distance, time_str = args.race
        result = calculate_from_race(distance, time_str)
    else:
        result = calculate_from_t_pace(args.t_pace)

    if args.format == "block":
        print(build_daniels_block(result))
    elif args.format == "json":
        import json

        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
