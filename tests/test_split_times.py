"""Tests for split-time annotation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.split_times import annotate_interval_line, split_hint_for_item


def test_gz_300_has_second_hint():
    item = {"type": "interval", "distance_m": 300, "reps": 4, "intensity": "GZ", "rest_sec": 50}
    hint = split_hint_for_item(item, "4:01")
    assert hint is not None
    assert "秒" in hint


def test_annotate_inserts_measu():
    item = {"type": "interval", "distance_m": 300, "reps": 4, "intensity": "GZ", "rest_sec": 50}
    line = "300m×4（GZ、レスト50秒）"
    out = annotate_interval_line(item, line, "4:01")
    assert "目安" in out
    assert "GZ" in out


def test_jog_has_no_split_hint():
    item = {"type": "jog", "group": "男子", "laps": 6, "pace": "k/4:50"}
    assert split_hint_for_item(item) is None
