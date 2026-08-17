"""Tests for practice validator."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.template_selector import select_best_template
from ai.validator import RetryState, validate_practice


def test_validate_evening_template_ok():
    match = select_best_template("夕練 600m×2 軽め")
    assert match is not None
    practice = dict(match.practice)
    result = validate_practice(
        "夕練",
        practice,
        base_items=match.practice.get("items") or [],
    )
    assert result.ok


def test_retry_state_tracks_attempts():
    state = RetryState(max_attempts=3)
    assert state.can_retry()
    state.record_failure(["err"])
    assert state.attempt == 1
    state.record_failure(["err2"])
    state.record_failure(["err3"])
    assert not state.can_retry()
