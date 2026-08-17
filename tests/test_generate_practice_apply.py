"""Tests for generate_practice apply path."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import generate_practice as gp


def test_event_matches_evening_tag():
    ev = {
        "title": "岱明夕練",
        "date": "2026-08-21",
        "tags": ["practice:daiming", "session:evening"],
    }
    assert gp._event_matches(ev, "2026-08-21", "岱明夕練", "evening")
    assert not gp._event_matches(ev, "2026-08-22", "岱明夕練", "evening")


def test_apply_writes_description(tmp_path, monkeypatch):
    from yaml_io import load_events_yaml, write_events_yaml

    src = Path(__file__).resolve().parent.parent / "input" / "events.2026.yaml"
    dest = tmp_path / "events.2026.yaml"
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(gp, "INPUT_DIR", tmp_path)

    practice = {
        "warmup": "動きづくり",
        "items": [{"type": "interval", "distance_m": 300, "reps": 4, "intensity": "GZ", "rest_sec": 50}],
        "abort_if": [{"when": "雨", "then": "中止"}],
    }
    gp._apply_to_events(
        2026,
        "2026-08-21",
        "岱明夕練",
        practice,
        "evening-light-300x4",
        "動きづくり\n\n300m×4（GZ）\n",
        "evening",
    )
    data = load_events_yaml(dest)
    ev = next(e for e in data["events"] if e.get("date") == "2026-08-21" and e.get("title") == "岱明夕練")
    assert ev["practice"]["items"][0]["distance_m"] == 300
    assert "300m" in ev["description"]
    assert ev.get("template_ref") == "evening-light-300x4"
