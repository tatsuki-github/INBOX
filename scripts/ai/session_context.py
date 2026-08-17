"""Load ±3 day practice/meet/weather context for a session date."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from practice_utils import tags_list
from yaml_io import load_events_yaml

from .config import INPUT_DIR

WEEKDAYS = "月火水木金土日"


@dataclass(frozen=True)
class NeighborSummary:
    date: str
    title: str
    weather: dict[str, Any] | None = None


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
    return "練習会" in title


def _is_race(title: str) -> bool:
    return "記録会" in title or "選手権" in title


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
    prev_meet = any(_is_meet(t) for n in neighbors if n.date == prev_day for t in [n.title])
    next_meet = any(_is_meet(t) for n in neighbors if n.date == next_day for t in [n.title])
    next_race = any(_is_race(t) for n in neighbors if n.date == next_day for t in [n.title])

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
        prev_titles=prev_titles,
        next_titles=next_titles,
    )
