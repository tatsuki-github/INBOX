"""Norwegian Method pace calculations (Bakken *The Norwegian Method Applied*)."""

from __future__ import annotations

import re

# Daiming practice distances (560m track + morning continuous)
DISTANCES_M = [300, 600, 900, 1000, 1120, 1200, 1680, 2000, 2100, 2500]

CATEGORY = {
    300: "short",
    600: "short",
    900: "short",
    1000: "medium",
    1120: "medium",
    1200: "medium",
    1680: "long",
    2000: "long",
    2100: "vlong",
    2500: "vlong",
}

T_OFFSET = {
    "short": (-7, -5),
    "medium": (0, 0),
    "long": (5, 7),
    "vlong": (7, 10),
}

GZ_OFFSET = {
    "short": (8, 12),
    "medium": (12, 18),
    "long": (15, 22),
    "vlong": (18, 25),
}

CATEGORY_TIME = {
    "short": "〜3分",
    "medium": "4〜5分",
    "long": "6〜8分",
    "vlong": "9〜15分",
}

T_NOTE = {
    "short": "T-7〜5秒/km",
    "medium": "Tペース",
    "long": "T+5〜7秒/km",
    "vlong": "T+7〜10秒/km",
}

BLOCK_START = "【ノルウェー式ゴールデンゾーン】"
BLOCK_END_MARKERS = ("  tags:", "\n- title:")


def parse_pace(pace_str: str) -> int:
    m = re.match(r"(\d+):(\d+)", pace_str.strip())
    if not m:
        raise ValueError(f"Cannot parse pace: {pace_str}")
    return int(m.group(1)) * 60 + int(m.group(2))


def fmt_pace(sec_per_km: int) -> str:
    return f"{sec_per_km // 60}:{sec_per_km % 60:02d}"


def fmt_time(seconds: float, distance_m: int) -> str:
    if distance_m == 300:
        return f"{seconds:.1f}秒"
    mins = int(seconds // 60)
    secs = int(round(seconds % 60))
    if secs == 60:
        mins += 1
        secs = 0
    return f"{mins}:{secs:02d}"


def split_time(pace_sec_per_km: float, distance_m: int) -> float:
    return pace_sec_per_km * distance_m / 1000


def fmt_range(low_sec: float, high_sec: float, distance_m: int) -> str:
    lo = fmt_time(low_sec, distance_m)
    hi = fmt_time(high_sec, distance_m)
    return lo if lo == hi else f"{lo}〜{hi}"


def category_for_distance(distance_m: int) -> str:
    if distance_m not in CATEGORY:
        raise ValueError(f"Unsupported distance: {distance_m}m")
    return CATEGORY[distance_m]


def gz_pace_range_sec_per_km(t_pace_str: str, distance_m: int) -> tuple[int, int]:
    t_sec = parse_pace(t_pace_str)
    cat = category_for_distance(distance_m)
    gz_lo, gz_hi = GZ_OFFSET[cat]
    return t_sec + gz_lo, t_sec + gz_hi


def t_pace_range_sec_per_km(t_pace_str: str, distance_m: int) -> tuple[int, int]:
    t_sec = parse_pace(t_pace_str)
    cat = category_for_distance(distance_m)
    t_lo, t_hi = T_OFFSET[cat]
    return t_sec + t_lo, t_sec + t_hi


def gz_pace_k_format(t_pace_str: str, distance_m: int) -> tuple[str, str]:
    lo, hi = gz_pace_range_sec_per_km(t_pace_str, distance_m)
    return f"k/{fmt_pace(lo)}", f"k/{fmt_pace(hi)}"


def build_block(t_pace_str: str) -> str:
    t_sec = parse_pace(t_pace_str)
    lines = [
        "【ノルウェー式ゴールデンゾーン】（インターバル長別ペース調整）",
        "※ T/GZ とも本書 Ch.2・Ch.5 のインターバル長別ガイドに準拠",
        "",
        "【閾値ペース（T）】",
    ]

    current_cat: str | None = None
    for dist in DISTANCES_M:
        cat = CATEGORY[dist]
        if cat != current_cat:
            lines.append(f"{CATEGORY_TIME[cat]} {T_NOTE[cat]}")
            current_cat = cat

        t_lo, t_hi = T_OFFSET[cat]
        pace_lo = t_sec + t_lo
        pace_hi = t_sec + t_hi
        time_str = fmt_range(split_time(pace_lo, dist), split_time(pace_hi, dist), dist)
        lines.append(f"{dist}m: {time_str}")

    lines.extend(["", "【ゴールデンゾーン（GZ）】"])
    current_cat = None
    for dist in DISTANCES_M:
        cat = CATEGORY[dist]
        if cat != current_cat:
            gz_lo, gz_hi = GZ_OFFSET[cat]
            lines.append(f"{CATEGORY_TIME[cat]} T+{gz_lo}〜{gz_hi}秒/km")
            current_cat = cat

        gz_lo, gz_hi = GZ_OFFSET[cat]
        pace_lo = t_sec + gz_lo
        pace_hi = t_sec + gz_hi
        time_str = fmt_range(split_time(pace_lo, dist), split_time(pace_hi, dist), dist)
        lines.append(f"{dist}m: {time_str}")

    return "\n".join(lines)


def normalize_block(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines())


def replace_block(desc: str, new_block: str) -> str:
    start = desc.find(BLOCK_START)
    if start < 0:
        return desc
    end = len(desc)
    for marker in BLOCK_END_MARKERS:
        pos = desc.find(marker, start)
        if pos >= 0:
            end = min(end, pos)
    prefix = desc[:start]
    suffix = desc[end:].lstrip("\n")
    return prefix + normalize_block(new_block) + "\n" + suffix
