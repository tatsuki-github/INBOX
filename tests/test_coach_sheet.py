"""Tests for coach-ready field sheet."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.coach_sheet import build_coach_sheet, decide_confidence
from ai.session_context import load_session_context
from ai.template_selector import select_best_template


def test_sheet_includes_split_and_abort_for_aug21():
    match = select_best_template("夕練 軽いポイント 300m×4")
    assert match is not None
    ctx = load_session_context("2026-08-21", session="evening", year=2026)
    sheet = build_coach_sheet(
        match.practice,
        ctx=ctx,
        session="evening",
        ok=True,
        template_id=match.template_id,
    )
    text = sheet.render()
    assert "岱明夕練" in text
    assert "18:00" in text
    assert "目安" in text
    assert "切上げ" in text
    assert "練習会" in text
    assert sheet.confidence == "review"
    assert "切上げ" in sheet.description_for_apply
    assert "信頼度" not in sheet.description_for_apply


def test_withhold_without_template():
    assert decide_confidence(ok=False, template_id=None, is_experiment=False, ctx=None) == "withhold"


def test_adopt_on_normal_evening():
    assert decide_confidence(ok=True, template_id="evening-light-300x4", is_experiment=False, ctx=None) == "adopt"
