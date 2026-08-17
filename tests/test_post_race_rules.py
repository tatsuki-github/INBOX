"""Tests for post-race rest rules."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.post_race_rules import is_daiming_race_event, should_apply_post_race_rest
from ai.practice_generator import generate_practice_auto
from ai.session_context import load_session_context


def test_is_daiming_race_event_detects_ekiden_and_nighter():
    assert is_daiming_race_event("荒玉中体連駅伝")
    assert is_daiming_race_event("玉名郡ナイター中・長距離記録会")
    assert is_daiming_race_event("第12回　中学駅伝金栗四三生誕の地なごみ大会")
    assert not is_daiming_race_event("練習会（岱明）")
    assert not is_daiming_race_event("玉名市人権教育研究大会")


def test_aug30_prev_race_after_tamana_nighter():
    ctx = load_session_context("2026-08-30", session="evening", year=2026)
    assert ctx.prev_race is True
    assert ctx.prev_race_title and "ナイター" in ctx.prev_race_title


def test_sep21_prev_race_after_nagomi():
    ctx = load_session_context("2026-09-21", session="evening", year=2026)
    assert ctx.prev_race is True


def test_post_race_generates_rest_template():
    ctx = load_session_context("2026-08-30", session="evening", year=2026)
    result = generate_practice_auto(
        "夕練",
        dry_run=True,
        session_ctx=ctx,
    )
    assert result.ok
    assert result.metadata.template_id == "post-race-rest"
    assert result.practice.get("items") == []
    assert "自主練" in (result.practice.get("notes") or "")


def test_should_apply_post_race_rest_respects_enabled():
    assert should_apply_post_race_rest(prev_race=True)
    assert not should_apply_post_race_rest(prev_race=False)
