"""Tests for weekly planner."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.weekly_planner import _validate_weekly_balance, plan_week_auto
from ai.weekly_planner import DayPlan


def test_weekly_dry_run_has_seven_days():
    plan = plan_week_auto("2026-03-09", dry_run=True)
    assert len(plan.days) == 7
    assert plan.weekly_theme
    assert plan.intensity is not None
    assert plan.intensity.share_pct["easy"] >= 55.0


def test_weekly_dry_run_includes_intensity_distribution():
    plan = plan_week_auto("2026-03-09", dry_run=True)
    dist = plan.intensity.as_dict()
    assert dist["target"]["easy"] == "60–65%"
    assert dist["share_pct"]["easy"] >= 55.0


def test_validate_weekly_balance_rejects_many_experiments():
    days = [
        DayPlan(date="2026-03-09", title="a", template_id="x", is_experiment=True),
        DayPlan(date="2026-03-10", title="b", template_id="y", is_experiment=True),
    ]
    errors = _validate_weekly_balance(days)
    assert any("experiment" in e for e in errors)


def test_weekly_overrides_two_days_before_chutaoren():
    plan = plan_week_auto("2026-07-13", dry_run=True)
    thursday = next(d for d in plan.days if d.date == "2026-07-16")
    assert thursday.template_id == "pre-race-rp-600"
    assert thursday.generation is not None
    intervals = [i for i in thursday.generation.practice["items"] if i.get("type") == "interval"]
    assert intervals[0]["distance_m"] == 600
    assert intervals[0]["reps"] == 1
    assert intervals[0]["intensity"] == "RP"
