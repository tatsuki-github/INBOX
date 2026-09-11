#!/usr/bin/env python3
"""Build men's full transcript JSON files from structured OCR/board data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lib.enrich import enrich_teams
from lib.schema import default_legs_for_gender, normalize_team
from lib.school_aliases import school_key
from validate_transcript import assert_valid_year, notion_anchor

TRANSCRIPTS = ROOT / "transcripts"
OCR_DIR = ROOT / "ocr_raw"
SOURCES = json.loads((ROOT / "sources/men_result_board_sources.json").read_text(encoding="utf-8"))

MEN_DATES = {
    "2025": "2025-10-15",
    "2024": "2024-10-16",
    "2023": "2023-10-18",
    "2022": "2022-10-19",
    "2021": "2021-10-20",
    "2020": "2020-10-21",
    "2019": "2019-10-16",
    "2018": "2018-10-17",
    "2017": "2017-10-18",
    "2016": "2016-10-19",
    "2015": "2015-10-21",
    "2014": "2014-10-22",
    "2013": "2013-10-23",
    "2012": "2012-10-24",
}

SCHOOL_NORMALIZE = {
    "蜀水": "菊水",
    "菜水": "菊水",
    "玉胶": "玉陵",
    "王陵": "玉陵",
    "南閱": "南関",
    "南開": "南関",
    "土木": "岱明",
    "土木之": "岱明",
    "荒鬼四": "荒尾四",
    "見鬼四": "荒尾四",
    "玉高附翼": "玉高附属",
    "五南": "玉南",
    "五名": "玉名",
    "玉陵": "玉陵",
    "Tamamura": "玉陵",
    "Gyoryo": "玉陵",
}


def normalize_school(name: str) -> str:
    key = school_key(name)
    return SCHOOL_NORMALIZE.get(key, key)


def normalize_time(value: str | None) -> str | None:
    if value is None:
        return None
    text = (value or "").strip().replace("'", ":").replace('"', "").replace("''", "")
    text = text.replace("°", ":").replace("′", ":").replace("″", "")
    text = text.replace(" ", "")
    if not text:
        return text
    parts = text.split(":")
    if len(parts) == 3:
        h, m, s = parts
        total_m = int(h) * 60 + int(m)
        return f"{total_m}:{int(s):02d}"
    if len(parts) == 2:
        m, s = parts
        return f"{int(m)}:{int(s):02d}"
    return text


def build_leg(row: dict) -> dict:
    name = row["name"]
    grade = row["grade"]
    split = normalize_time(row["split"])
    cumulative = normalize_time(row["cumulative"])
    out = {
        "leg": row["leg"],
        "name": name,
        "grade": grade,
        "split": split,
        "cumulative": cumulative,
        "passing_rank": row.get("passing_rank"),
        "split_rank": row.get("split_rank"),
        "split_record": row.get("split_record"),
        "status": row.get("status", "ok"),
        "raw_name_grade": row.get("raw_name_grade") or f"{name}({grade})",
    }
    if row.get("notes"):
        out["notes"] = row["notes"]
    return out


def build_team(row: dict) -> dict:
    team_name = normalize_school(row["team"])
    legs = [build_leg(L) for L in row["legs"]]
    return {
        "rank": row["rank"],
        "team": team_name,
        "total": normalize_time(row["total"]),
        "legs": legs,
    }


def mark_split_records(teams: list[dict]) -> None:
    for leg in range(1, 7):
        best: tuple[int, list[str]] | None = None
        for team in teams:
            leg_row = next(L for L in team["legs"] if L["leg"] == leg)
            if leg_row.get("status") in {"dnf", "dns"}:
                continue
            from lib.ranks import parse_time_to_seconds

            sec = parse_time_to_seconds(leg_row.get("split"))
            if sec is None:
                continue
            if best is None or sec < best[0]:
                best = (sec, [team["team"]])
            elif sec == best[0]:
                best[1].append(team["team"])
        if not best:
            continue
        for team in teams:
            leg_row = next(L for L in team["legs"] if L["leg"] == leg)
            leg_row["split_record"] = team["team"] in best[1]


def normalize_finish_ranks(teams: list[dict]) -> list[dict]:
    """Reassign rank 1..N by ascending total time."""
    from lib.ranks import parse_time_to_seconds

    ordered = sorted(
        teams,
        key=lambda t: parse_time_to_seconds(t.get("total")) or 10**9,
    )
    return [{**team, "rank": idx} for idx, team in enumerate(ordered, 1)]


def build_year(year: int, payload: dict) -> dict:
    teams = [build_team(t) for t in payload["teams"]]
    if payload.get("reorder_by_total"):
        teams = normalize_finish_ranks(teams)
    mark_split_records(teams)
    src = SOURCES.get(str(year), {})
    drive_id = src.get("id") if isinstance(src, dict) else src
    entry = {
        "year": year,
        "gender": "男子",
        "date": payload.get("date") or MEN_DATES[str(year)],
        "source_drive_id": drive_id,
        "legs": payload.get("legs") or default_legs_for_gender("男子"),
        "teams": teams,
    }
    if payload.get("ocr_notes"):
        entry["ocr_notes"] = payload["ocr_notes"]
    return entry


def write_ocr_raw(year: int, text: str) -> Path:
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    path = OCR_DIR / f"{year}-男子.md"
    header = (
        f"# 荒玉中体連駅伝 {year} 男子 — OCR raw\n\n"
        f"> Google Drive result board (`men_result_board_sources.json`)\n\n"
    )
    path.write_text(header + text.strip() + "\n", encoding="utf-8")
    return path


def main() -> None:
    from men_data.build_all import main as build_all_main

    build_all_main()


if __name__ == "__main__":
    main()
