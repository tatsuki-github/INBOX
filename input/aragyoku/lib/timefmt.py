"""Time format helpers for Aragyoku transcripts."""

from __future__ import annotations

import re


def normalize_board_time(value: str | None) -> str | None:
    """Convert board notation (12' 12\", 1° 03' 47\") to M:SS or H:MM:SS."""
    if not value:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"dnf", "dns", "-"}:
        return None
    text = (
        text.replace("°", ":")
        .replace("'", ":")
        .replace('"', "")
        .replace("″", "")
        .replace(" ", "")
        .replace("．", ".")
    )
    text = re.sub(r"[^\d:.]", "", text)
    parts = [p for p in text.split(":") if p != ""]
    if not parts:
        return None
    try:
        nums = [int(float(p)) for p in parts]
    except ValueError:
        return None
    if len(nums) == 2:
        minutes, seconds = nums
        if seconds >= 60:
            return None
        return f"{minutes}:{seconds:02d}"
    if len(nums) == 3:
        hours, minutes, seconds = nums
        if minutes >= 60 or seconds >= 60:
            return None
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return None


def circled_to_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    mapping = {
        "①": 1,
        "②": 2,
        "③": 3,
        "④": 4,
        "⑤": 5,
        "⑥": 6,
        "⑦": 7,
        "⑧": 8,
        "⑨": 9,
        "⑩": 10,
        "⑪": 11,
        "⑫": 12,
        "⑬": 13,
        "⑭": 14,
        "⑮": 15,
        "⑯": 16,
        "⑰": 17,
        "⑱": 18,
        "⑲": 19,
        "⑳": 20,
    }
    text = str(value).strip()
    if text in mapping:
        return mapping[text]
    text = text.replace("O", "0").replace("o", "0")
    if text.isdigit():
        return int(text)
    return None
