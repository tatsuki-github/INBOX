#!/usr/bin/env python3
"""Validate canonical women's transcripts without rewriting image-checked data."""

from __future__ import annotations

import json
from pathlib import Path

from validate_transcript import assert_valid_year

ROOT = Path(__file__).resolve().parent
YEARS = [2012, 2013, *range(2015, 2026)]


def main() -> list[tuple[int, int]]:
    results: list[tuple[int, int]] = []
    for year in YEARS:
        path = ROOT / "transcripts" / f"{year}-女子.json"
        entry = json.loads(path.read_text(encoding="utf-8"))
        assert_valid_year(
            entry,
            year=year,
            gender="女子",
            include_daimyo=year != 2013,
        )
        results.append((year, len(entry["teams"])))
        print(f"{path.name}: {len(entry['teams'])} teams (validated; unchanged)")
    return results


if __name__ == "__main__":
    main()
