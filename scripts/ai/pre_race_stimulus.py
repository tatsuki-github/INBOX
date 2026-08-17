"""大会2日前の RP 刺激（1本、連続疾走は 1000m まで）。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

MAX_CONTINUOUS_M = 1000
DEFAULT_DISTANCE_M = 900
ALTERNATE_1500_M = 1000

EVENT_STIMULUS_M: dict[str, int] = {
    "100m": 300,
    "200m": 300,
    "400m": 300,
    "4x400mR": 300,
    "800m": 600,
    "1000m": 900,
    "1500m": 900,
    "3000m": 1000,
    "3000mSC": 1000,
    "5000m": 1000,
}

RACE_NEGATIVE = ("練習会", "研究大会", "人権教育", "振込", "返金", "参加費")
RACE_POSITIVE = (
    "選手権",
    "記録会",
    "ジュニアオリンピック",
    "通信陸上",
    "陸上競技大会",
    "総合体育大会",
    "中体連",
    "全中",
)

SKIP_QUERY_TOKENS = ("ジョグのみ", "休み", "中止")

_EVENT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"3000\s*m\s*SC", re.I), "3000mSC"),
    (re.compile(r"4\s*[x×]\s*400"), "4x400mR"),
    (re.compile(r"(?<!\d)5000\s*m", re.I), "5000m"),
    (re.compile(r"(?<!\d)3000\s*m", re.I), "3000m"),
    (re.compile(r"(?<!\d)1500\s*m", re.I), "1500m"),
    (re.compile(r"(?<!\d)1000\s*m", re.I), "1000m"),
    (re.compile(r"(?<!\d)800\s*m", re.I), "800m"),
    (re.compile(r"(?<!\d)400\s*m", re.I), "400m"),
    (re.compile(r"(?<!\d)200\s*m", re.I), "200m"),
    (re.compile(r"(?<!\d)100\s*m", re.I), "100m"),
)

_JOG_MALE = {
    "type": "jog",
    "group": "男子",
    "laps": 6,
    "distance_km": 3.36,
    "pace": "k/4:50",
}
_JOG_FEMALE = {
    "type": "jog",
    "group": "女子",
    "laps": 5,
    "distance_km": 2.8,
    "pace": "k/5:00",
}


@dataclass(frozen=True)
class PreRaceStimulus:
    distance_m: int
    reps: int
    intensity: str
    event_hint: str
    mixed_events: tuple[str, ...] = ()

    @property
    def template_id(self) -> str:
        return f"pre-race-rp-{self.distance_m}"

    @property
    def label(self) -> str:
        return f"大会2日前 RP刺激 {self.distance_m}m×{self.reps}"

    @property
    def needs_event_confirm(self) -> bool:
        return self.event_hint == "unknown" or bool(self.mixed_events)

    @property
    def notes(self) -> str:
        parts = ["大会2日前のRP刺激。勝ちにいかない。1本のみ。連続疾走は1000mまで。"]
        if self.event_hint == "1500m":
            parts.append("1500mは900m×1（既定）または1000m×1。")
        if self.mixed_events:
            parts.append(
                "複数種目あり。短い刺激を既定（800m組を守る）。1500m組は900/1000に手で変更可。"
            )
        if self.event_hint == "unknown":
            parts.append("種目不明のため900m×1。出場種目を確認すること。")
        return "".join(parts)


def parse_race_events(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for pattern, label in _EVENT_PATTERNS:
        if pattern.search(text) and label not in seen:
            seen.add(label)
            found.append(label)
    return found


def is_championship_race(title: str, description: str = "") -> bool:
    if any(token in title for token in RACE_NEGATIVE):
        return False
    blob = f"{title}\n{description}"
    if any(token in blob for token in RACE_POSITIVE):
        return True
    return "大会" in title and bool(parse_race_events(blob))


def prefer_longer_1500_from_query(query: str) -> bool:
    return "1000" in query and "900" not in query


def should_apply_pre_race_stimulus(
    *,
    race_in_two_days: bool,
    next_race: bool,
    next_meet: bool,
    session: str,
    query: str = "",
) -> bool:
    if not race_in_two_days:
        return False
    if session != "evening":
        return False
    if next_race:
        return False
    return not any(token in query for token in SKIP_QUERY_TOKENS)


def stimulus_for_events(
    events: Sequence[str],
    *,
    prefer_longer_1500: bool = False,
) -> PreRaceStimulus:
    mapped: list[tuple[str, int]] = []
    for event in events:
        distance = EVENT_STIMULUS_M.get(event)
        if distance is None:
            continue
        if event == "1500m" and prefer_longer_1500:
            distance = ALTERNATE_1500_M
        mapped.append((event, min(int(distance), MAX_CONTINUOUS_M)))
    if not mapped:
        return PreRaceStimulus(
            distance_m=DEFAULT_DISTANCE_M,
            reps=1,
            intensity="RP",
            event_hint="unknown",
        )
    mixed = tuple(event for event, _ in mapped) if len(mapped) > 1 else ()
    event_hint, distance_m = min(mapped, key=lambda item: item[1])
    return PreRaceStimulus(
        distance_m=distance_m,
        reps=1,
        intensity="RP",
        event_hint=event_hint,
        mixed_events=mixed,
    )


def build_pre_race_practice(stimulus: PreRaceStimulus) -> dict:
    return {
        "warmup": "動きづくり",
        "notes": stimulus.notes,
        "items": [
            dict(_JOG_MALE),
            dict(_JOG_FEMALE),
            {
                "type": "interval",
                "distance_m": stimulus.distance_m,
                "reps": 1,
                "intensity": "RP",
            },
        ],
    }


def validate_pre_race_practice(practice: dict, template_id: str | None) -> list[str]:
    if not template_id or not str(template_id).startswith("pre-race-rp-"):
        return []
    errors: list[str] = []
    for item in practice.get("items") or []:
        if item.get("type") != "interval":
            continue
        distance = item.get("distance_m") or 0
        try:
            distance_m = int(distance)
        except (TypeError, ValueError):
            errors.append(f"pre-race RP distance is not an int: {distance}")
            continue
        if distance_m > MAX_CONTINUOUS_M:
            errors.append(
                f"pre-race continuous distance {distance_m}m exceeds {MAX_CONTINUOUS_M}m"
            )
        reps = item.get("reps")
        if reps not in (1, "1"):
            errors.append("pre-race RP must be exactly 1 rep")
    return errors
