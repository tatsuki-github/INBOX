"""Practice data models and constants."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

LAP_M = 560

PRACTICE_TYPES = frozenset({"jog", "interval", "set", "strides", "warmup", "rest", "other"})
INTENSITIES = frozenset({"E", "T", "I", "R", "RP", "1500mRP", "3000mRP", "GZ"})
MACHINE_TAG_PREFIXES = ("practice:", "session:")


class PracticeType(str, Enum):
    JOG = "jog"
    INTERVAL = "interval"
    SET = "set"
    STRIDES = "strides"
    WARMUP = "warmup"
    REST = "rest"
    OTHER = "other"


@dataclass
class LegacyItem:
    """k/pace 表示用（convert_practice_pace 互換）。"""

    menu: str
    distance: str
    pace: str


@dataclass
class ParseResult:
    practice: dict[str, Any]
    legacy_items: list[LegacyItem] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    source: str = "none"
    confidence: str = "none"
    note_lines: list[str] = field(default_factory=list)

    @property
    def items(self) -> list[dict[str, Any]]:
        return self.practice.get("items") or []


def empty_practice() -> dict[str, Any]:
    return {"items": []}
