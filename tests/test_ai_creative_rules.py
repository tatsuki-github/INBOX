"""Tests for creative rules engine."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.creative_rules import load_rules, validate_experiment_notes, validate_fixed_constraints, validate_template_diff


def test_validate_fixed_pace_format():
    rules = load_rules()
    practice = {"items": [{"type": "jog", "pace": "k/4:16"}]}
    assert validate_fixed_constraints(practice, rules) == []


def test_validate_fixed_rejects_bad_pace():
    rules = load_rules()
    practice = {"items": [{"type": "jog", "pace": "4:16/km"}]}
    errors = validate_fixed_constraints(practice, rules)
    assert any("pace" in e for e in errors)


def test_template_diff_allows_small_reps_change():
    rules = load_rules()
    base = [{"type": "interval", "distance_m": 600, "reps": 2, "intensity": "GZ", "rest_sec": 180}]
    cand = copy.deepcopy(base)
    cand[0]["reps"] = 3
    assert validate_template_diff(base, cand, rules) == []


def test_experiment_notes_require_prefix():
    rules = load_rules()
    practice = {"notes": "試しに距離変更", "items": []}
    errors = validate_experiment_notes(practice, rules, is_experiment=True)
    assert errors
