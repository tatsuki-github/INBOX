"""Tests: 練習会は岱明生徒の負荷に数えない。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.attendance_rules import counts_as_load_meet, is_practice_meet
from ai.coach_sheet import decide_confidence
from ai.session_context import SessionContext, load_session_context


def test_practice_meet_titles_are_recognized_but_not_load() -> None:
    assert is_practice_meet("練習会（桃田）") is True
    assert is_practice_meet("練習会（岱明）") is True
    assert counts_as_load_meet("練習会（桃田）") is False
    assert counts_as_load_meet("玉名郡ナイター中・長距離記録会") is False


def test_day_after_daiming_practice_meet_is_not_fatigue() -> None:
    ctx = load_session_context("2026-08-21", session="evening", year=2026)
    assert ctx.prev_meet is False
    assert decide_confidence(
        ok=True,
        template_id="evening-light-300x4",
        is_experiment=False,
        ctx=SessionContext(
            date="2026-08-21",
            session="evening",
            weekday="金",
            prev_meet=True,
            next_meet=True,
        ),
    ) == "adopt"
