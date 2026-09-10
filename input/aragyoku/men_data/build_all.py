#!/usr/bin/env python3
"""Generate men's transcript JSON and OCR raw from structured year modules."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from build_men_transcripts import (  # noqa: E402
    MEN_DATES,
    build_year,
    write_ocr_raw,
)
from lib.enrich import apply_board_ranks_from_computed, enrich_teams  # noqa: E402
from validate_transcript import assert_valid_year, notion_anchor  # noqa: E402

TRANSCRIPTS = ROOT / "transcripts"
SOURCES = json.loads((ROOT / "sources/men_result_board_sources.json").read_text(encoding="utf-8"))
YEARS = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018]


def load_year_module(year: int):
    return importlib.import_module(f"men_data.y{year}")


def main() -> None:
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    summary = []
    for year in YEARS:
        mod = load_year_module(year)
        write_ocr_raw(year, mod.OCR_RAW)
        entry = build_year(year, {"teams": mod.TEAMS, "ocr_notes": getattr(mod, "NOTES", None)})
        enriched = apply_board_ranks_from_computed(
            enrich_teams(entry["teams"], 6), 6
        )
        year_entry = {**entry, "teams": enriched}
        anchor = notion_anchor(year, "男子")
        if anchor:
            year_entry["daimyo"] = {
                "rank": anchor.get("岱明の順位"),
                "total": anchor.get("岱明の記録"),
            }
        assert_valid_year(year_entry, year=year, gender="男子")
        out = TRANSCRIPTS / f"{year}-男子.json"
        out.write_text(json.dumps(year_entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary.append((year, len(enriched)))
        print(f"{out.name}: {len(enriched)} teams")
    print("done", summary)


if __name__ == "__main__":
    main()
