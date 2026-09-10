#!/usr/bin/env python3
"""Validation rules V-1 through V-9 for Aragyoku full transcripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lib.ranks import parse_time_to_seconds, rank_mismatches
from lib.schema import leg_count_for_gender, normalize_team
from lib.school_aliases import school_key

ROOT = Path(__file__).resolve().parents[2]
NOTION_ROWS = ROOT / "input/external/notion/databases/荒玉中体連駅伝歴代/rows.json"
CSV_RECONCILIATIONS = (
    Path(__file__).resolve().parent / "reconciliations/women_csv_reconciliations.json"
)


def _load_notion_rows() -> list[dict[str, Any]]:
    return json.loads(NOTION_ROWS.read_text(encoding="utf-8"))


def notion_anchor(year: int, gender: str) -> dict[str, Any] | None:
    label = f"{year} {gender}"
    for row in _load_notion_rows():
        if row.get("名前") == label:
            return row
    return None


def validate_times(year_entry: dict, leg_count: int) -> list[str]:
    """V-1 cumulative consistency, V-2 final total match."""
    notes: list[str] = []
    for team in year_entry["teams"]:
        prev = 0
        for leg_row in team["legs"]:
            cum_s = parse_time_to_seconds(leg_row.get("cumulative"))
            split_s = parse_time_to_seconds(leg_row.get("split"))
            if cum_s is None or split_s is None:
                if leg_row.get("status") not in {"dnf", "dns"}:
                    notes.append(f"{team['team']} leg{leg_row['leg']}: missing time")
                continue
            if prev and cum_s != prev + split_s:
                notes.append(
                    f"{team['team']} leg{leg_row['leg']}: "
                    f"cum {leg_row['cumulative']} != prev+split"
                )
            prev = cum_s
        total_s = parse_time_to_seconds(team.get("total"))
        if prev and total_s is not None and prev != total_s:
            notes.append(f"{team['team']}: final cum != total {team['total']}")
    return notes


def validate_team_order(year_entry: dict) -> list[str]:
    """V-3 rank sequence and total monotonicity."""
    notes: list[str] = []
    teams = year_entry["teams"]
    ranks = [t["rank"] for t in teams]
    expected = list(range(1, len(teams) + 1))
    if ranks != expected:
        notes.append(f"ranks not 1..N: {ranks}")
    totals = []
    for team in teams:
        final_leg = team["legs"][-1]
        if final_leg.get("status") in {"dnf", "dns"}:
            continue
        total_s = parse_time_to_seconds(team.get("total"))
        if total_s is not None:
            totals.append((team["rank"], total_s))
    for i in range(1, len(totals)):
        if totals[i][1] < totals[i - 1][1]:
            notes.append(
                f"total not monotonic: rank {totals[i-1][0]} "
                f"({totals[i-1][1]}s) > rank {totals[i][0]} ({totals[i][1]}s)"
            )
    return notes


def _daimyo_board_canonical(year_entry: dict) -> bool:
    """True when ocr_notes records board-vs-Notion daimyo discrepancy (board is canonical)."""
    for note in year_entry.get("ocr_notes") or []:
        text = str(note).lower()
        if "notion rank" in text or "board canonical" in text:
            return True
    return False


def validate_daimyo_anchor(year_entry: dict, year: int, gender: str) -> list[str]:
    """V-9 daimyo rank/total vs Notion rows.json."""
    notes: list[str] = []
    anchor = notion_anchor(year, gender)
    if not anchor:
        return notes
    skip_notion = _daimyo_board_canonical(year_entry)
    daimyo = year_entry.get("daimyo") or {}
    daimyo_team = next((t for t in year_entry["teams"] if school_key(t["team"]) == "岱明"), None)
    if daimyo_team:
        expected_rank = anchor.get("岱明の順位")
        if (
            not skip_notion
            and expected_rank is not None
            and daimyo_team["rank"] != expected_rank
        ):
            notes.append(f"daimyo rank: team={daimyo_team['rank']} notion={expected_rank}")
        expected_total = anchor.get("岱明の記録")
        if expected_total and not skip_notion:
            exp_s = parse_time_to_seconds(expected_total)
            got_s = parse_time_to_seconds(daimyo_team.get("total"))
            if exp_s is not None and got_s is not None and exp_s != got_s:
                notes.append(f"daimyo total: team={daimyo_team['total']} notion={expected_total}")
    if daimyo and not skip_notion:
        if anchor.get("岱明の順位") is not None and daimyo.get("rank") != anchor["岱明の順位"]:
            notes.append(f"daimyo.rank meta mismatch notion={anchor['岱明の順位']}")
        if anchor.get("岱明の記録"):
            exp_s = parse_time_to_seconds(anchor["岱明の記録"])
            got_s = parse_time_to_seconds(daimyo.get("total"))
            if exp_s is not None and got_s is not None and exp_s != got_s:
                notes.append(f"daimyo.total meta mismatch notion={anchor['岱明の記録']}")
    return notes


def validate_leg_count(year_entry: dict, gender: str) -> list[str]:
    """V-6 correct number of legs per team."""
    notes: list[str] = []
    expected = leg_count_for_gender(gender)
    for team in year_entry["teams"]:
        if len(team["legs"]) != expected:
            notes.append(f"{team['team']}: expected {expected} legs, got {len(team['legs'])}")
    return notes


def validate_split_records(year_entry: dict, leg_count: int) -> list[str]:
    """V-8 split_record legs must be fastest on that leg."""
    notes: list[str] = []
    for leg in range(1, leg_count + 1):
        splits: list[tuple[str, int]] = []
        record_holders: list[str] = []
        for team in year_entry["teams"]:
            leg_row = next(L for L in team["legs"] if L["leg"] == leg)
            split_s = parse_time_to_seconds(leg_row.get("split"))
            if split_s is not None:
                splits.append((team["team"], split_s))
            if leg_row.get("split_record"):
                record_holders.append(team["team"])
        if not record_holders:
            continue
        if not splits:
            notes.append(f"leg{leg}: split_record flagged but no valid splits")
            continue
        fastest = min(splits, key=lambda x: x[1])
        for holder in record_holders:
            holder_split = next(s for t, s in splits if t == holder)
            if holder_split != fastest[1]:
                notes.append(
                    f"leg{leg}: split_record on {holder} but fastest is {fastest[0]}"
                )
    return notes


def validate_rank_crosscheck(year_entry: dict, leg_count: int) -> list[str]:
    """V-7 board ranks vs computed ranks."""
    return rank_mismatches(year_entry["teams"], leg_count)


def validate_year_transcript(
    year_entry: dict,
    *,
    year: int,
    gender: str,
    include_daimyo: bool = True,
) -> list[str]:
    """Run all validation rules; return list of error/warning strings."""
    leg_count = leg_count_for_gender(gender)
    notes: list[str] = []
    notes.extend(validate_leg_count(year_entry, gender))
    notes.extend(validate_times(year_entry, leg_count))
    notes.extend(validate_team_order(year_entry))
    notes.extend(validate_rank_crosscheck(year_entry, leg_count))
    notes.extend(validate_split_records(year_entry, leg_count))
    if include_daimyo:
        notes.extend(validate_daimyo_anchor(year_entry, year, gender))
    return notes


def assert_valid_year(
    year_entry: dict,
    *,
    year: int,
    gender: str,
    include_daimyo: bool = True,
) -> None:
    notes = validate_year_transcript(
        year_entry,
        year=year,
        gender=gender,
        include_daimyo=include_daimyo,
    )
    if notes:
        raise AssertionError(f"{year} {gender} validation failed:\n" + "\n".join(notes))
