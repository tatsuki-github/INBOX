"""Tests for Norwegian intensity distribution module."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.intensity_distribution import (  # noqa: E402
    distribution_guidance_for_prompt,
    profile_for_template,
    summarize_week_intensity,
    validate_weekly_intensity,
)
from ai.weekly_planner import DayPlan  # noqa: E402


def test_distribution_guidance_prioritizes_ratios_over_gz_count():
    text = distribution_guidance_for_prompt()
    assert "60–65%" in text
    assert "20–30%" in text
    assert "GZ回数" in text or "時間割合" in text


def test_evening_light_roles_are_threshold_not_gz_frequency():
    main = profile_for_template("evening-light-600x2")
    support = profile_for_template("evening-light-300x4")
    assert "Main quality" in main["role"]
    assert "Support quality" in support["role"]


def test_fallback_week_meets_easy_majority():
    days = [
        DayPlan(date="2026-08-17", title="jog", template_id="jog-male-easy"),
        DayPlan(date="2026-08-18", title="rest", template_id=None),
        DayPlan(date="2026-08-19", title="support", template_id="evening-light-300x4"),
        DayPlan(date="2026-08-20", title="rest", template_id=None),
        DayPlan(date="2026-08-21", title="main", template_id="evening-light-600x2"),
        DayPlan(date="2026-08-22", title="jog", template_id="jog-female-easy"),
        DayPlan(date="2026-08-23", title="rest", template_id=None),
    ]
    summary = summarize_week_intensity(days)
    assert summary.share_pct["easy"] >= 55.0
    assert summary.within_target
    assert not validate_weekly_intensity(days)


def test_too_many_threshold_sessions_fails_validation():
    days = [
        DayPlan(date="2026-08-17", title="a", template_id="evening-light-600x2"),
        DayPlan(date="2026-08-18", title="b", template_id="evening-light-600x2"),
        DayPlan(date="2026-08-19", title="c", template_id="evening-light-600x2"),
        DayPlan(date="2026-08-20", title="d", template_id="evening-light-300x4"),
    ]
    errors = validate_weekly_intensity(days)
    assert errors
    assert any("Threshold" in e for e in errors)
