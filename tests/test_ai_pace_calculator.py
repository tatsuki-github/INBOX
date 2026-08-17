"""Tests for Norwegian pace calculator."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.pace_calculator import build_block, gz_pace_range_sec_per_km, parse_pace, split_time


def test_parse_pace():
    assert parse_pace("4:01") == 241


def test_build_block_includes_distances():
    block = build_block("4:01")
    for dist in (300, 600, 900, 1200, 2100):
        assert f"{dist}m:" in block


def test_gz_slower_than_t_for_same_distance():
    t_lo, t_hi = (parse_pace("4:01"), parse_pace("4:01"))
    gz_lo, gz_hi = gz_pace_range_sec_per_km("4:01", 600)
    assert gz_lo > t_lo
