"""Tests for abort rule engine."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.abort_rules import build_abort_rules
from ai.session_context import SessionContext


def test_practice_meet_does_not_add_fatigue_abort():
    ctx = SessionContext(
        date="2026-08-21",
        session="evening",
        weekday="金",
        prev_meet=True,
        next_meet=True,
        weather={"humidity_pct": 93, "temperature_c": 27.2, "condition": "にわか雨（弱）", "precipitation_mm": 1.3},
    )
    practice = {"items": [{"type": "interval", "distance_m": 900, "reps": 1, "intensity": "GZ"}]}
    rules = build_abort_rules(ctx, practice)
    whens = [r["when"] for r in rules]
    assert not any("練習会" in w for w in whens)
    assert any("湿度" in w for w in whens)
    assert any("雨" in w for w in whens)
    assert any("1本目" in w for w in whens)


def test_next_race_still_adds_taper_abort():
    ctx = SessionContext(
        date="2026-08-22",
        session="evening",
        weekday="土",
        next_race=True,
    )
    practice = {"items": [{"type": "interval", "distance_m": 300, "reps": 4, "intensity": "GZ"}]}
    rules = build_abort_rules(ctx, practice)
    assert any(r["when"] == "翌日が記録会" for r in rules)


def test_race_in_two_days_adds_single_rep_rule():
    ctx = SessionContext(
        date="2026-07-16",
        session="evening",
        weekday="木",
        race_in_two_days=True,
    )
    practice = {"items": [{"type": "interval", "distance_m": 600, "reps": 1, "intensity": "RP"}]}
    rules = build_abort_rules(ctx, practice)
    assert any(r["when"] == "大会2日前のRP刺激" for r in rules)
    assert any("1本のみ" in r["then"] for r in rules)
