#!/usr/bin/env python3
"""Tests for Aragyoku transcript validation and rank computation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARAGYOKU = ROOT / "input/aragyoku"
sys.path.insert(0, str(ARAGYOKU))

from lib.ranks import (  # noqa: E402
    compute_passing_ranks,
    compute_split_ranks,
    parse_time_to_seconds,
    rank_mismatches,
)
from validate_transcript import validate_year_transcript  # noqa: E402


def _five_leg_sample() -> dict:
    """Minimal valid 5-leg women's year (2 teams)."""
    return {
        "year": 2025,
        "gender": "女子",
        "teams": [
            {
                "rank": 1,
                "team": "玉名",
                "total": "50:00",
                "legs": [
                    {
                        "leg": 1,
                        "name": "A",
                        "grade": 2,
                        "split": "10:00",
                        "cumulative": "10:00",
                        "passing_rank": 1,
                        "split_rank": 1,
                    },
                    {
                        "leg": 2,
                        "name": "B",
                        "grade": 2,
                        "split": "10:00",
                        "cumulative": "20:00",
                        "passing_rank": 1,
                        "split_rank": 1,
                    },
                    {
                        "leg": 3,
                        "name": "C",
                        "grade": 2,
                        "split": "10:00",
                        "cumulative": "30:00",
                        "passing_rank": 1,
                        "split_rank": 1,
                    },
                    {
                        "leg": 4,
                        "name": "D",
                        "grade": 2,
                        "split": "10:00",
                        "cumulative": "40:00",
                        "passing_rank": 1,
                        "split_rank": 1,
                    },
                    {
                        "leg": 5,
                        "name": "E",
                        "grade": 2,
                        "split": "10:00",
                        "cumulative": "50:00",
                        "passing_rank": 1,
                        "split_rank": 1,
                    },
                ],
            },
            {
                "rank": 2,
                "team": "南関",
                "total": "55:00",
                "legs": [
                    {
                        "leg": 1,
                        "name": "F",
                        "grade": 3,
                        "split": "11:00",
                        "cumulative": "11:00",
                        "passing_rank": 2,
                        "split_rank": 2,
                    },
                    {
                        "leg": 2,
                        "name": "G",
                        "grade": 3,
                        "split": "11:00",
                        "cumulative": "22:00",
                        "passing_rank": 2,
                        "split_rank": 2,
                    },
                    {
                        "leg": 3,
                        "name": "H",
                        "grade": 3,
                        "split": "11:00",
                        "cumulative": "33:00",
                        "passing_rank": 2,
                        "split_rank": 2,
                    },
                    {
                        "leg": 4,
                        "name": "I",
                        "grade": 3,
                        "split": "11:00",
                        "cumulative": "44:00",
                        "passing_rank": 2,
                        "split_rank": 2,
                    },
                    {
                        "leg": 5,
                        "name": "J",
                        "grade": 3,
                        "split": "11:00",
                        "cumulative": "55:00",
                        "passing_rank": 2,
                        "split_rank": 2,
                    },
                ],
            },
        ],
    }


def test_parse_time_to_seconds() -> None:
    assert parse_time_to_seconds("10:16") == 616
    assert parse_time_to_seconds("0:59") == 59
    assert parse_time_to_seconds(None) is None
    assert parse_time_to_seconds("dnf") is None


def test_compute_split_ranks() -> None:
    teams = _five_leg_sample()["teams"]
    ranks = compute_split_ranks(teams, 1)
    assert ranks["1:玉名"] == 1
    assert ranks["2:南関"] == 2


def test_rank_mismatch_detection() -> None:
    year = _five_leg_sample()
    year["teams"][0]["legs"][0]["split_rank"] = 99
    notes = rank_mismatches(year["teams"], 5)
    assert any("split_rank" in n for n in notes)


def test_validate_year_passes_clean_sample() -> None:
    year = _five_leg_sample()
    notes = validate_year_transcript(year, year=2025, gender="女子")
    assert notes == []


def test_validate_times_catches_bad_cumulative() -> None:
    year = _five_leg_sample()
    year["teams"][0]["legs"][1]["cumulative"] = "19:00"
    notes = validate_year_transcript(year, year=2025, gender="女子")
    assert any("cum" in n for n in notes)


def test_fixture_transcript_file() -> None:
    fixture = json.loads(
        (ROOT / "tests/fixtures/aragyoku_sample_transcript.json").read_text(encoding="utf-8")
    )
    assert fixture["teams"][0]["legs"][0]["split_rank"] == 1
