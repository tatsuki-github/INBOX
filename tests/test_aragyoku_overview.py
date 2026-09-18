"""Tests for scripts/generate_aragyoku_overview.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_aragyoku_overview.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_aragyoku_overview", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pace_for_men_2ku_9min_current():
    mod = _load_module()
    # 540s / 2.855km ≈ 189.1s/km → 3:09.1/km
    assert mod.pace_for(2.855, "9:00") == "3:09.1/km"
    assert mod.pace_for(3.05, "9:00") == "2:57.0/km"


def test_overview_markdown_contains_faq_and_distances(tmp_path: Path):
    mod = _load_module()
    out = tmp_path / "aragyoku-overview.md"
    text = mod.build_markdown()
    out.write_text(text, encoding="utf-8")
    assert "荒玉駅伝" in text
    assert "男子2区" in text
    assert "9:00" in text
    assert "3:09.1/km" in text
    assert "2.855km" in text
    assert "2024年以降" in text
    assert "ペース換算" in text
