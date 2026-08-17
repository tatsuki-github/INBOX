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


def test_validate_weekly_balance_rejects_many_experiments():
    days = [
        DayPlan(date="2026-03-09", title="a", template_id="x", is_experiment=True),
        DayPlan(date="2026-03-10", title="b", template_id="y", is_experiment=True),
    ]
    errors = _validate_weekly_balance(days)
    assert any("experiment" in e for e in errors)
