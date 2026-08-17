"""Tests for abort rule engine."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.abort_rules import build_abort_rules
from ai.session_context import SessionContext


def test_prev_meet_adds_jog_only_rule():
    ctx = SessionContext(
        date="2026-08-21",
        session="evening",
        weekday="金",
        prev_meet=True,
        weather={"humidity_pct": 93, "temperature_c": 27.2, "condition": "にわか雨（弱）", "precipitation_mm": 1.3},
    )
    practice = {"items": [{"type": "interval", "distance_m": 900, "reps": 1, "intensity": "GZ"}]}
    rules = build_abort_rules(ctx, practice)
    whens = [r["when"] for r in rules]
    assert any("練習会翌日" in w for w in whens)
    assert any("湿度" in w for w in whens)
    assert any("雨" in w for w in whens)
    assert any("1本目" in w for w in whens)
