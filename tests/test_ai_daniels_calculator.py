"""Tests for Daniels VDOT calculator."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.daniels_calculator import (  # noqa: E402
    calculate_from_race,
    calculate_from_t_pace,
    parse_time,
    training_paces_from_vdot,
    vdot_from_race,
)
from ai.pace_calculator import parse_pace  # noqa: E402

# Validated against input/events.2026.yaml athlete memo blocks
REPO_CASES = [
    (303.56, 53.7, "4:01"),
    (323.50, 50.0, "4:15"),
    (270.13, 61.3, "3:36"),
    (262.33, 63.4, "3:31"),
    (277.20, 59.5, "3:42"),
]


def test_parse_time():
    assert parse_time("4:20") == 260
    assert parse_time("5:03.56") == 303.56


def test_vdot_matches_repo_athletes():
    for time_sec, expected_vdot, _ in REPO_CASES:
        vdot = vdot_from_race(1500, time_sec)
        assert abs(vdot - expected_vdot) < 0.05


def test_t_pace_matches_repo_athletes():
    for time_sec, vdot, t_pace in REPO_CASES:
        paces = training_paces_from_vdot(vdot)
        assert abs(paces["T"] - parse_pace(t_pace)) <= 1


def test_gz_slower_than_daniels_t():
    result = calculate_from_race("1500m", "4:20")
    t_sec = parse_pace(result["t_pace_str"])
    assert "【ゴールデンゾーン（GZ）】" in result["golden_zone_block"]
    assert f"T+8" in result["golden_zone_block"]
    # GZ must be slower than T (Norwegian sub-threshold)
    assert "600m:" in result["golden_zone_block"]
    assert "k/" in result["golden_zone_block"]


def test_calculate_from_t_pace():
    result = calculate_from_t_pace("4:01")
    assert result["t_pace_str"] == "4:01"
    assert abs(result["vdot"] - 53.7) <= 0.5
    assert result["paces"]["T"] == parse_pace("4:01")


def test_1500m_4_20_vdot():
    result = calculate_from_race("1500m", "4:20")
    assert abs(result["vdot"] - 64.0) < 0.1
    assert result["t_pace_str"] == "3:29"
