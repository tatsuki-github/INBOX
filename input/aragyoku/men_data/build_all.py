#!/usr/bin/env python3
"""Validate canonical men's transcripts without regenerating them from legacy OCR."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validate_transcript import assert_valid_year  # noqa: E402

YEARS = list(range(2012, 2026))


def main() -> None:
    summary: list[tuple[int, int]] = []
    for year in YEARS:
        path = ROOT / "transcripts" / f"{year}-男子.json"
        entry = json.loads(path.read_text(encoding="utf-8"))
        assert_valid_year(entry, year=year, gender="男子")
        summary.append((year, len(entry["teams"])))
        print(f"{path.name}: {len(entry['teams'])} teams (validated; unchanged)")
    print("done", summary)


if __name__ == "__main__":
    main()
