"""Annotate interval items with Norwegian-method split times in seconds."""

from __future__ import annotations

from typing import Any

from .pace_calculator import (
    CATEGORY,
    fmt_range,
    gz_pace_range_sec_per_km,
    split_time,
    t_pace_range_sec_per_km,
)


def split_hint_for_item(item: dict[str, Any], t_pace: str = "4:01") -> str | None:
    """Return a human split range for GZ/T intervals, or None if not applicable."""
    if item.get("type") != "interval":
        return None
    intensity = item.get("intensity")
    distance_m = item.get("distance_m")
    if intensity not in {"GZ", "T"} or not isinstance(distance_m, (int, float)):
        return None
    dist = int(distance_m)
    if dist not in CATEGORY:
        return None
    if intensity == "GZ":
        lo, hi = gz_pace_range_sec_per_km(t_pace, dist)
    else:
        lo, hi = t_pace_range_sec_per_km(t_pace, dist)
    return fmt_range(split_time(lo, dist), split_time(hi, dist), dist)


def annotate_interval_line(item: dict[str, Any], line: str, t_pace: str = "4:01") -> str:
    """Insert 目安 split times into a rendered interval line."""
    hint = split_hint_for_item(item, t_pace)
    if not hint:
        return line
    marker = f"（{item.get('intensity')}、"
    if marker in line:
        return line.replace(marker, f"（{item.get('intensity')}、目安 {hint}、", 1)
    close = f"（{item.get('intensity')}）"
    if close in line:
        return line.replace(close, f"（{item.get('intensity')}、目安 {hint}）", 1)
    return f"{line}（目安 {hint}）"
