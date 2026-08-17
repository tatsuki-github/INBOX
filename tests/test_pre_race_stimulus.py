"""大会2日前の RP 刺激ルール。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ai.pre_race_stimulus import (
    MAX_CONTINUOUS_M,
    PreRaceStimulus,
    is_championship_race,
    parse_race_events,
    should_apply_pre_race_stimulus,
    stimulus_for_events,
)
from ai.practice_generator import generate_practice
from ai.session_context import load_session_context


def test_1500m_defaults_to_900() -> None:
    s = stimulus_for_events(["1500m"])
    assert s == PreRaceStimulus(
        distance_m=900,
        reps=1,
        intensity="RP",
        event_hint="1500m",
        mixed_events=(),
    )
    assert s.distance_m <= MAX_CONTINUOUS_M
    assert s.template_id == "pre-race-rp-900"


def test_1500m_can_prefer_1000() -> None:
    s = stimulus_for_events(["1500m"], prefer_longer_1500=True)
    assert s.distance_m == 1000
    assert s.reps == 1
    assert s.distance_m <= MAX_CONTINUOUS_M


def test_800m_maps_to_600() -> None:
    s = stimulus_for_events(["800m"])
    assert s.distance_m == 600
    assert s.reps == 1
    assert s.intensity == "RP"
    assert s.event_hint == "800m"


def test_1000m_maps_to_900() -> None:
    s = stimulus_for_events(["1000m"])
    assert s.distance_m == 900
    assert s.distance_m <= MAX_CONTINUOUS_M


def test_3000m_is_capped_at_1000() -> None:
    s = stimulus_for_events(["3000m"])
    assert s.distance_m == 1000
    assert s.reps == 1


def test_unknown_event_defaults_to_900() -> None:
    s = stimulus_for_events([])
    assert s.distance_m == 900
    assert s.event_hint == "unknown"
    assert s.needs_event_confirm is True


def test_never_exceeds_1000m_continuous() -> None:
    for events in (["5000m"], ["3000mSC"], ["1500m", "800m"], ["4x400mR"]):
        s = stimulus_for_events(events)
        assert s.distance_m <= MAX_CONTINUOUS_M
        assert s.reps == 1


def test_parse_race_events_from_title() -> None:
    assert parse_race_events("中学県選手権 1500m") == ["1500m"]
    assert parse_race_events("ジュニアオリンピック 800m") == ["800m"]
    assert parse_race_events("熊本県中学校総合体育大会") == []
    assert "100m" not in parse_race_events("1000m")
    assert parse_race_events("800m 女子\n1500m 男子") == ["1500m", "800m"]


def test_mixed_800_and_1500_prefers_shorter_stimulus() -> None:
    s = stimulus_for_events(["1500m", "800m"])
    assert s.distance_m == 600
    assert s.mixed_events == ("1500m", "800m")


def test_championship_keywords_exclude_false_positives() -> None:
    assert is_championship_race("熊本県中学校総合体育大会 1500m") is True
    assert is_championship_race("県中体連", "令和８年度 熊本県中学校総合体育大会陸上競技大会") is True
    assert is_championship_race("練習会（桃田）") is False
    assert is_championship_race("人権教育研究大会") is False
    assert is_championship_race("玉名選手権参加費振込") is False


def test_session_context_detects_race_in_two_days() -> None:
    events = [
        {"title": "岱明夕練", "date": "2026-08-21", "tags": ["practice:daiming", "session:evening"]},
        {
            "title": "熊本県中学校総合体育大会 1500m",
            "date": "2026-08-23",
            "start": "09:00",
        },
    ]
    ctx = load_session_context("2026-08-21", session="evening", events=events)
    assert ctx.race_in_two_days is True
    assert ctx.next_race_in_two_days is not None
    assert ctx.next_race_in_two_days.title == "熊本県中学校総合体育大会 1500m"
    assert ctx.next_race_in_two_days.events == ["1500m"]


def test_session_context_ignores_practice_meet_as_championship() -> None:
    events = [
        {"title": "岱明夕練", "date": "2026-08-21", "tags": ["practice:daiming", "session:evening"]},
        {
            "title": "練習会（桃田）",
            "date": "2026-08-23",
            "start": "19:00",
            "location": "桃田運動公園陸上競技場",
        },
    ]
    ctx = load_session_context("2026-08-21", session="evening", events=events)
    assert ctx.race_in_two_days is False
    assert ctx.next_race_in_two_days is None


def test_session_context_ignores_education_conference() -> None:
    events = [
        {"title": "人権教育研究大会", "date": "2026-08-23", "start": "09:00"},
    ]
    ctx = load_session_context("2026-08-21", session="evening", events=events)
    assert ctx.race_in_two_days is False


def test_july16_is_two_days_before_chutaoren() -> None:
    ctx = load_session_context("2026-07-16", session="evening", year=2026)
    assert ctx.race_in_two_days is True
    assert ctx.next_race_in_two_days is not None
    assert "800m" in ctx.next_race_in_two_days.events
    assert "1500m" in ctx.next_race_in_two_days.events


def test_practice_meet_tomorrow_does_not_block_pre_race() -> None:
    assert (
        should_apply_pre_race_stimulus(
            race_in_two_days=True,
            next_race=False,
            next_meet=True,
            session="evening",
        )
        is True
    )
    assert (
        should_apply_pre_race_stimulus(
            race_in_two_days=True,
            next_race=True,
            next_meet=False,
            session="evening",
        )
        is False
    )
    assert (
        should_apply_pre_race_stimulus(
            race_in_two_days=True,
            next_race=False,
            next_meet=False,
            session="morning",
        )
        is False
    )
    assert (
        should_apply_pre_race_stimulus(
            race_in_two_days=True,
            next_race=False,
            next_meet=False,
            session="evening",
            query="ジョグのみ",
        )
        is False
    )
    assert (
        should_apply_pre_race_stimulus(
            race_in_two_days=True,
            next_race=False,
            next_meet=False,
            session="evening",
        )
        is True
    )


def test_generate_practice_uses_pre_race_template_when_race_in_two_days() -> None:
    events = [
        {"title": "岱明夕練", "date": "2026-08-21", "tags": ["practice:daiming", "session:evening"]},
        {"title": "熊本県中学校選手権 800m", "date": "2026-08-23"},
    ]
    ctx = load_session_context("2026-08-21", session="evening", events=events)
    result = generate_practice("夕練", dry_run=True, session_ctx=ctx)
    assert result.ok
    assert result.metadata.template_id == "pre-race-rp-600"
    intervals = [i for i in result.practice["items"] if i.get("type") == "interval"]
    assert intervals == [{"type": "interval", "distance_m": 600, "reps": 1, "intensity": "RP"}]
    assert "大会2日前" in (result.practice.get("notes") or "")
    assert all(i.get("distance_m", 0) <= MAX_CONTINUOUS_M for i in intervals)
