"""Tests for AI practice generator."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.llm_client import MockLLMClient
from ai.practice_generator import generate_practice, generate_practice_auto
from ai.template_selector import select_best_template


def test_dry_run_generates_valid_practice():
    result = generate_practice_auto("夕練、600m×2、軽め", dry_run=True)
    assert result.ok
    assert result.metadata.template_id == "evening-light-600x2"
    assert result.practice.get("items")
    assert result.metadata.intensity_role == "Threshold: Main quality"
    assert result.metadata.intensity_header
    assert result.metadata.intensity_minutes


def test_llm_merge_with_mock():
    match = select_best_template("夕練、600m×2、軽め")
    assert match is not None
    llm = MockLLMClient(
        responses=[
            json.dumps(
                {
                    "warmup": "動きづくり＋ストライド",
                    "notes": "今日は特に1本目を抑える",
                    "items": match.practice.get("items"),
                },
                ensure_ascii=False,
            )
        ]
    )
    result = generate_practice("夕練、600m×2、軽め", template=match, llm=llm)
    assert result.ok
    assert result.metadata.llm_used
    assert "動きづくり" in (result.practice.get("warmup") or "")


def test_llm_retry_on_invalid_json_then_success():
    match = select_best_template("夕練、600m×2、軽め")
    assert match is not None
    llm = MockLLMClient(
        responses=[
            "not json",
            json.dumps({"notes": "OK", "items": match.practice.get("items")}),
        ]
    )
    result = generate_practice("夕練", template=match, llm=llm, config=__import__("ai.config", fromlist=["load_config"]).load_config())
    assert result.ok
    assert result.metadata.attempts >= 2
