#!/usr/bin/env python3
"""Build women/men full JSON and athletes CSV from per-year transcript files."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from lib.enrich import enrich_teams
from lib.schema import (
    ATHLETE_CSV_COLUMNS,
    default_legs_for_gender,
    leg_count_for_gender,
    men_leg_distances_for_year,
    normalize_team,
)
from validate_transcript import assert_valid_year, notion_anchor

ROOT = Path(__file__).resolve().parent
TRANSCRIPTS = ROOT / "transcripts"
SOURCES_WOMEN = ROOT / "sources/women_result_board_sources.json"
SOURCES_MEN = ROOT / "sources/men_result_board_sources.json"
CSV_RECONCILIATIONS = ROOT / "reconciliations/women_csv_reconciliations.json"

TOP6_VERIFICATION = {
    "method": "原画像との全セル目視照合",
    "verified_years": [
        2012,
        2013,
        2015,
        2016,
        2017,
        2018,
        2019,
        2020,
        2021,
        2022,
        2023,
        2024,
        2025,
    ],
    "cells_per_year": 138,
    "checked_cells": 1794,
    "unreadable_cells": 0,
    "corrected_cells": 9,
    "csv_reconciled_cells": 33,
    "csv_reconciliation_rule": (
        "同年度CSVの女子・中学生を学校・学年・継続年度・走力で照合し、"
        "一意に本人と判断できる表記はCSVを優先"
    ),
    "csv_reconciliation_source": "input/aragyoku/reconciliations/women_csv_reconciliations.json",
}

WOMEN_MISSING = [2014]
MEN_YEARS = list(range(2012, 2026))


def _load_sources(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _event_dates() -> dict[str, dict[str, str]]:
    """Known event dates by year/gender."""
    women_dates = {
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
        "2013": "2013-10-23",
        "2012": "2012-10-24",
    }
    men_dates = {
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
    return {"女子": women_dates, "男子": men_dates}


def load_transcript(year: int, gender: str) -> dict | None:
    path = TRANSCRIPTS / f"{year}-{gender}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_year_entry(year: int, gender: str, transcript: dict, source_id: str | None) -> dict:
    leg_count = leg_count_for_gender(gender)
    teams = enrich_teams(transcript["teams"], leg_count)
    anchor = notion_anchor(year, gender)
    entry: dict = {
        "year": year,
        "gender": gender,
        "date": transcript.get("date") or _event_dates()[gender].get(str(year)),
        "source_drive_id": transcript.get("source_drive_id") or source_id,
        "team_count": len(teams),
        "legs": transcript.get("legs") or (men_leg_distances_for_year(year) if gender == "男子" else default_legs_for_gender(gender)),
        "teams": teams,
    }
    if anchor:
        entry["weather"] = {"temperature_c": anchor.get("スタート時間付近の気温")}
        entry["pace"] = {"second_place_avg": anchor.get("2位の平均ペース")}
        if anchor.get("岱明の順位") is not None:
            entry["daimyo"] = {
                "rank": anchor["岱明の順位"],
                "total": anchor.get("岱明の記録"),
            }
    if transcript.get("ocr_notes"):
        entry["ocr_notes"] = transcript["ocr_notes"]
    return entry


def build_dataset(gender: str) -> dict:
    sources = _load_sources(SOURCES_WOMEN if gender == "女子" else SOURCES_MEN)
    years_range = range(2012, 2026)
    missing: list[int] = list(WOMEN_MISSING) if gender == "女子" else []
    years: dict[str, dict] = {}

    for year in years_range:
        if year in missing:
            continue
        transcript = load_transcript(year, gender)
        if not transcript:
            key = str(year)
            if key not in sources:
                missing.append(year)
            continue
        src = sources.get(str(year), {})
        drive_id = src.get("id") if isinstance(src, dict) else src
        entry = build_year_entry(year, gender, transcript, drive_id)
        assert_valid_year(entry, year=year, gender=gender)
        years[str(year)] = entry

    return {
        "meta": {
            "event": "玉名荒尾中体連駅伝",
            "gender": gender,
            "legs": men_leg_distances_for_year(years[next(iter(years))]["year"]) if gender == "男子" and years else default_legs_for_gender(gender),
            "schema": "full-transcript-v1",
        },
        "years": years,
        "missing_years": sorted(set(missing)),
    }


def write_athletes_csv(dataset: dict, path: Path) -> None:
    gender = dataset["meta"]["gender"]
    rows: list[dict] = []
    for year, entry in sorted(dataset["years"].items(), key=lambda x: int(x[0]), reverse=True):
        drive_id = entry.get("source_drive_id")
        for team in entry["teams"]:
            for leg_row in team["legs"]:
                rows.append(
                    {
                        "year": year,
                        "gender": gender,
                        "rank": team["rank"],
                        "team": team["team"],
                        "total": team["total"],
                        "leg": leg_row["leg"],
                        "name": leg_row.get("name"),
                        "grade": leg_row.get("grade"),
                        "split": leg_row.get("split"),
                        "cumulative": leg_row.get("cumulative"),
                        "passing_rank": leg_row.get("passing_rank"),
                        "split_rank": leg_row.get("split_rank"),
                        "split_record": leg_row.get("split_record"),
                        "status": leg_row.get("status", "ok"),
                        "source_drive_id": drive_id,
                    }
                )
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ATHLETE_CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def apply_csv_reconciliations(top6: dict) -> None:
    """Apply name/grade corrections from women_csv_reconciliations.json to top-6 teams."""
    if not CSV_RECONCILIATIONS.exists():
        return
    audit = json.loads(CSV_RECONCILIATIONS.read_text(encoding="utf-8"))
    for item in audit.get("items") or []:
        year_block = top6["years"].get(str(item["year"]))
        if not year_block:
            continue
        team = next((t for t in year_block["teams"] if t["rank"] == item["rank"]), None)
        if not team or team["team"] != item["team"]:
            continue
        leg_row = next((L for L in team["legs"] if L["leg"] == item["leg"]), None)
        if not leg_row:
            continue
        leg_row[item["field"]] = item["to"]


def derive_top6(dataset: dict) -> dict:
    out_years: dict[str, dict] = {}
    for year, entry in dataset["years"].items():
        top = [normalize_team(t) for t in entry["teams"] if t["rank"] <= 6]
        out_years[year] = {
            "date": entry.get("date"),
            "source_drive_id": entry.get("source_drive_id"),
            "teams": top,
            "confidence": "verified",
        }
        if entry.get("ocr_notes"):
            out_years[year]["ocr_notes"] = entry["ocr_notes"]
    meta = {
        **dataset["meta"],
        "note": (
            "Google Drive「荒玉駅伝歴代」の各年結果画像を、"
            "順位・校名・総合・選手名・学年・区間・累積の全セルで目視照合"
        ),
        "verification": TOP6_VERIFICATION,
    }
    top6 = {
        "meta": meta,
        "years": out_years,
        "missing_years": dataset.get("missing_years", []),
    }
    apply_csv_reconciliations(top6)
    return top6


def derive_top4(top6: dict) -> dict:
    top4 = json.loads(json.dumps(top6, ensure_ascii=False))
    for entry in top4["years"].values():
        entry["teams"] = [team for team in entry["teams"] if team["rank"] <= 4]
    return top4


def write_top_athletes_csv(dataset: dict, path: Path) -> None:
    columns = ["year", "rank", "team", "total", "leg", "name", "grade", "split", "cumulative", "source_drive_id"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for year, entry in sorted(dataset["years"].items(), key=lambda item: int(item[0]), reverse=True):
            for team in entry["teams"]:
                for leg in team["legs"]:
                    writer.writerow({
                        "year": year,
                        "rank": team["rank"],
                        "team": team["team"],
                        "total": team["total"],
                        "leg": leg["leg"],
                        "name": leg.get("name"),
                        "grade": leg.get("grade"),
                        "split": leg.get("split"),
                        "cumulative": leg.get("cumulative"),
                        "source_drive_id": entry.get("source_drive_id"),
                    })


def main() -> None:
    women = build_dataset("女子")
    men = build_dataset("男子")

    women_path = ROOT / "women_full_2012_2025.json"
    men_path = ROOT / "men_full_2012_2025.json"
    women_path.write_text(json.dumps(women, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    men_path.write_text(json.dumps(men, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    write_athletes_csv(women, ROOT / "women_full_athletes.csv")
    write_athletes_csv(men, ROOT / "men_full_athletes.csv")

    top6 = derive_top6(women)
    top6_path = ROOT / "women_top6_2012_2025.json"
    top6_path.write_text(json.dumps(top6, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_top_athletes_csv(top6, ROOT / "women_top6_athletes.csv")

    top4 = derive_top4(top6)
    (ROOT / "women_top4_2012_2025.json").write_text(
        json.dumps(top4, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_top_athletes_csv(top4, ROOT / "women_top4_athletes.csv")

    print("women years", len(women["years"]), "missing", women["missing_years"])
    print("men years", len(men["years"]), "missing", men["missing_years"])
    print("wrote", women_path, men_path, top6_path)


if __name__ == "__main__":
    main()
