"""Tests for AI template selector."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.template_selector import select_best_template, select_templates


def test_select_evening_light_600():
    match = select_best_template("夕練、600m×2、軽め")
    assert match is not None
    assert match.template_id == "evening-light-600x2"


def test_select_norwegian_4515():
    match = select_best_template("45/15 基本")
    assert match is not None
    assert match.template_id == "norwegian-45-15-base"


def test_select_templates_returns_ranked():
    matches = select_templates("ジョグ 男子", top_k=2)
    assert len(matches) >= 1
    assert matches[0].score >= matches[-1].score
