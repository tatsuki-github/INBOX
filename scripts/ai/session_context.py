"""Load ±3 day practice/meet/weather context for a session date."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from practice_utils import tags_list
from yaml_io import load_events_yaml

from .attendance_rules import counts_as_load_meet
from .config import INPUT_DIR
from .post_race_rules import is_daiming_race_event
from .pre_race_stimulus import is_championship_race, parse_race_events

WEEKDAYS = "月火水木金土日"


@dataclass(frozen=True)
class NeighborSummary:
    date: str
    title: str
    weather: dict[str, Any] | None = None


@dataclass(frozen=True)
class RacePreview:
    date: str
    title: str
    events: list[str] = field(default_factory=list)


@dataclass
class SessionContext:
    date: str
    session: str
    weekday: str
    target: dict[str, Any] | None = None
    start_time: str | None = None
    end_time: str | None = None
    weather: dict[str, Any] | None = None
    neighbors: list[NeighborSummary] = field(default_factory=list)
    prev_meet: bool = False
    next_meet: bool = False
    next_race: bool = False
    prev_race: bool = False
    prev_race_title: str | None = None
    race_in_two_days: bool = False
    next_race_in_two_days: RacePreview | None = None
    prev_titles: list[str] = field(default_factory=list)
    next_titles: list[str] = field(default_factory=list)


def weekday_jp(iso_date: str) -> str:
    return WEEKDAYS[date.fromisoformat(iso_date).weekday()]


def _is_relevant(ev: dict[str, Any]) -> bool:
    title = ev.get("title") or ""
    tags = tags_list(ev)
    if "practice:daiming" in tags:
        return True
    return any(key in title for key in ("岱明", "練習会", "記録会"))


def _is_meet(title: str) -> bool:
    """Load-affecting meet. 練習会は岱明生徒が基本不参加のため常に False。"""
    return counts_as_load_meet(title)


def _is_race(title: str) -> bool:
    return "記録会" in title or "選手権" in title


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _race_preview_on(
    events: list[dict[str, Any]],
    iso_date: str,
    *,
    race_filter=is_championship_race,
) -> RacePreview | None:
    previews: list[RacePreview] = []
    for ev in events:
        if ev.get("date") != iso_date:
            continue
        title = ev.get("title") or ""
        description = ev.get("description") or ""
        if not race_filter(title, description):
            continue
        parsed = parse_race_events(f"{title}\n{description}")
        previews.append(RacePreview(date=iso_date, title=title, events=parsed))
    if not previews:
        return None
    merged: list[str] = []
    for preview in previews:
        merged.extend(preview.events)
    return RacePreview(date=iso_date, title=previews[0].title, events=_unique(merged))


def _session_of(ev: dict[str, Any]) -> str | None:
    tags = tags_list(ev)
    if "session:morning" in tags or (ev.get("title") or "").startswith("岱明朝練"):
        return "morning"
    if "session:evening" in tags or (ev.get("title") or "").startswith("岱明夕練"):
        return "evening"
    return None


def load_events_for_year(year: int, *, path: Path | None = None) -> list[dict[str, Any]]:
    events_path = path or (INPUT_DIR / f"events.{year}.yaml")
    if not events_path.exists():
        return []
    data = load_events_yaml(events_path)
    return data.get("events") or []


def load_session_context(
    iso_date: str,
    *,
    session: str = "evening",
    events: list[dict[str, Any]] | None = None,
    year: int | None = None,
) -> SessionContext:
    if events is None:
        year = year or int(iso_date[:4])
        events = load_events_for_year(year)
    target_day = date.fromisoformat(iso_date)
    window_dates = {(target_day + timedelta(days=delta)).isoformat() for delta in range(-3, 4)}

    neighbors: list[NeighborSummary] = []
    prev_titles: list[str] = []
    next_titles: list[str] = []
    target: dict[str, Any] | None = None

    for ev in events:
        ev_date = ev.get("date")
        if ev_date not in window_dates:
            continue
        title = ev.get("title") or ""
        if ev_date == iso_date and _session_of(ev) == session:
            target = ev
        if not _is_relevant(ev):
            continue
        neighbors.append(NeighborSummary(date=ev_date, title=title, weather=ev.get("weather")))
        if ev_date < iso_date:
            prev_titles.append(title)
        elif ev_date > iso_date:
            next_titles.append(title)

    prev_day = (target_day - timedelta(days=1)).isoformat()
    next_day = (target_day + timedelta(days=1)).isoformat()
    two_days = (target_day + timedelta(days=2)).isoformat()
    prev_meet = any(_is_meet(t) for n in neighbors if n.date == prev_day for t in [n.title])
    next_meet = any(_is_meet(t) for n in neighbors if n.date == next_day for t in [n.title])
    next_race = any(_is_race(t) for n in neighbors if n.date == next_day for t in [n.title])
    race_preview = _race_preview_on(events, two_days)
    prev_race_preview = _race_preview_on(
        events,
        prev_day,
        race_filter=is_daiming_race_event,
    )

    weather = (target or {}).get("weather") if target else None
    if weather is None:
        for n in neighbors:
            if n.date == iso_date and n.weather:
                weather = n.weather
                break

    return SessionContext(
        date=iso_date,
        session=session,
        weekday=weekday_jp(iso_date),
        target=target,
        start_time=(target or {}).get("start_time"),
        end_time=(target or {}).get("end_time"),
        weather=weather,
        neighbors=neighbors,
        prev_meet=prev_meet,
        next_meet=next_meet,
        next_race=next_race,
        prev_race=prev_race_preview is not None,
        prev_race_title=prev_race_preview.title if prev_race_preview else None,
        race_in_two_days=race_preview is not None,
        next_race_in_two_days=race_preview,
        prev_titles=prev_titles,
        next_titles=next_titles,
    )
