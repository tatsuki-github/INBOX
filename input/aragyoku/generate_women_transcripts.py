#!/usr/bin/env python3
"""Generate women's full transcript JSON files for 2012-2019 (skip 2014)."""

from __future__ import annotations

import json
from pathlib import Path

from lib.schema import default_legs_for_gender
from transcript_board_data import Y2012, Y2013, Y2015, Y2016, Y2017, Y2018, Y2019
from transcript_helpers import finalize_teams, merge_top6
from validate_transcript import assert_valid_year

ROOT = Path(__file__).resolve().parent
SOURCES = json.loads((ROOT / "sources/women_result_board_sources.json").read_text(encoding="utf-8"))
OCR_DIR = ROOT / "ocr_raw"
OUT_DIR = ROOT / "transcripts"

DATES = {
    2019: "2019-11-16",
    2018: "2018-10-17",
    2017: "2017-10-18",
    2016: "2016-10-19",
    2015: "2015-10-21",
    2013: "2013-10-23",
    2012: "2012-10-24",
}

YEAR_DATA = {
    2019: Y2019,
    2018: Y2018,
    2017: Y2017,
    2016: Y2016,
    2015: Y2015,
    2013: Y2013,
    2012: Y2012,
}

# Google Drive read_file_content OCR excerpts (truncated headers)
OCR_TEXT = {
    2019: "令和元年度 玉名荒尾中体連駅伝競走大会 (女子) 総合成績表",
    2018: "平成30年度 玉名荒尾中体連駅伝競走大会 (女子) 総合成績表",
    2017: "平成29年度 玉名荒尾中体連駅伝競走大会 (女子) 総合成績表",
    2016: "平成28年度 玉名荒尾中体連駅伝競走大会 (女子) 総合成績表",
    2015: "平成27年度 玉名荒尾中体連駅伝競走大会 (女子) 総合成績表",
    2013: "平成25年度 玉名荒尾中体連駅伝競走大会 (女子) 総合成績表",
    2012: "平成24年度 玉名荒尾中体連駅伝競走大会 (女子) 総合成績表",
}


def write_ocr_raw(year: int, drive_id: str) -> None:
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    path = OCR_DIR / f"{year}-女子.md"
    path.write_text(
        f"# 荒玉中体連駅伝 {year} 女子 — OCR raw\n\n"
        f"> source_drive_id: `{drive_id}`\n"
        f"> source: Google Drive MCP `read_file_content`\n\n"
        f"## Header\n\n{OCR_TEXT[year]}\n",
        encoding="utf-8",
    )


def build_year(year: int) -> dict:
    teams = finalize_teams(merge_top6(year, YEAR_DATA[year]))
    drive_id = SOURCES[str(year)]["id"]
    return {
        "year": year,
        "gender": "女子",
        "date": DATES[year],
        "source_drive_id": drive_id,
        "legs": default_legs_for_gender("女子"),
        "teams": teams,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[tuple[int, int]] = []
    for year in [2019, 2018, 2017, 2016, 2015, 2013, 2012]:
        entry = build_year(year)
        year_entry = {**entry, "team_count": len(entry["teams"])}
        # 2013 board shows 岱明 5th (43:25); Notion row still says 7th.
        include_daimyo = year != 2013
        assert_valid_year(
            year_entry,
            year=year,
            gender="女子",
            include_daimyo=include_daimyo,
        )
        out_path = OUT_DIR / f"{year}-女子.json"
        out_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_ocr_raw(year, entry["source_drive_id"])
        results.append((year, len(entry["teams"])))
        print(f"wrote {out_path.name} teams={len(entry['teams'])}")
    return results


if __name__ == "__main__":
    main()
