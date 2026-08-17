"""Tests for session context loader."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.session_context import load_session_context, weekday_jp


def test_weekday_jp():
    assert weekday_jp("2026-08-21") == "金"


def test_aug21_evening_does_not_treat_practice_meet_as_fatigue():
    ctx = load_session_context("2026-08-21", session="evening", year=2026)
    assert ctx.prev_meet is False
    assert ctx.next_meet is False
    assert ctx.weather is not None
    assert ctx.start_time == "18:00"
    assert any("練習会" in t for t in ctx.prev_titles)


def test_aug22_next_race_not_practice_meet_fatigue():
    ctx = load_session_context("2026-08-22", session="evening", year=2026)
    assert ctx.next_meet is False
    assert ctx.next_race is True
