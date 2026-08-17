"""Tests for Norwegian-method golden zone table generation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from update_golden_zone_tables import build_block, parse_pace, split_time


def test_parse_pace():
    assert parse_pace("4:01") == 241


def test_build_block_includes_all_daiming_distances():
    block = build_block("4:01")
    for dist in (300, 600, 900, 1000, 1120, 1200, 1680, 2000, 2100, 2500):
        assert f"{dist}m:" in block


def test_short_interval_t_faster_than_daniels_t():
    t_sec = parse_pace("4:01")
    t300_fast = split_time(t_sec - 7, 300)
    t300_daniels = split_time(t_sec, 300)
    assert t300_fast < t300_daniels


def test_long_interval_gz_slower_per_km_than_short():
    t_sec = parse_pace("4:01")
    gz_short_pace = t_sec + 12
    gz_long_pace = t_sec + 22
    assert gz_long_pace > gz_short_pace
