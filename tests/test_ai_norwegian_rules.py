"""Tests for Norwegian rules."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.norwegian_rules import NORWEGIAN_TEMPLATE_IDS, principles_for_prompt, recommend_intensity


def test_principles_for_prompt_includes_golden_zone():
    text = principles_for_prompt()
    assert "Golden Zone" in text or "GZ" in text
    assert "60–65%" in text
    assert "20–30%" in text


def test_recommend_intensity_evening():
    assert recommend_intensity("evening_light") == "GZ"


def test_norwegian_templates_include_4515():
    assert "norwegian-45-15-base" in NORWEGIAN_TEMPLATE_IDS
