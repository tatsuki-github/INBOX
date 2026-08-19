"""Daniels VDOT and training-pace calculations (Jack Daniels Running Formula, 3rd ed.).

Race time -> VDOT -> E/M/T/I/R paces -> Norwegian Golden Zone (via pace_calculator).
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import TypedDict

import yaml

from ai.pace_calculator import build_block, fmt_pace, parse_pace

ROOT = Path(__file__).resolve().parents[2]
PACES_PATH = ROOT / "input" / "daniels_vdot_paces.yaml"

MILE_TO_KM = 1.60934

RACE_DISTANCES_M = {
    "1500m": 1500,
    "1500": 1500,
    "mile": 1609.34,
    "3000m": 3000,
    "3000": 3000,
    "5k": 5000,
    "5K": 5000,
    "10k": 10000,
    "10K": 10000,
}


class TrainingPaces(TypedDict):
    E: tuple[int, int]
    M: int
    T: int
    I: int
    R: int


class DanielsResult(TypedDict):
    distance_label: str
    time_sec: float
    time_display: str
    vdot: float
    paces: TrainingPaces
    t_pace_str: str
    golden_zone_block: str


def _load_pace_table() -> dict[int, dict[str, int]]:
    data = yaml.safe_load(PACES_PATH.read_text(encoding="utf-8"))
    rows = data["vdot_paces_sec_per_mile"]
    return {int(k): v for k, v in rows.items()}


def parse_time(time_str: str) -> float:
    """Parse M:SS, MM:SS.ss, or H:MM:SS."""
    text = time_str.strip()
    if re.match(r"^\d+\.\d+$", text):
        return float(text)
    parts = text.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError(f"Cannot parse time: {time_str}")


def format_race_time(seconds: float) -> str:
    if seconds >= 3600:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:04.1f}"
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}:{s:04.2f}".rstrip("0").rstrip(".")


def mile_sec_to_km_sec(sec_per_mile: int) -> int:
    return round(sec_per_mile / MILE_TO_KM)


def vdot_from_race(distance_m: float, time_sec: float) -> float:
    """Daniels-Gilbert VO2 equation + %VO2max for race duration."""
    velocity_m_min = distance_m / (time_sec / 60)
    vo2 = 0.182258 * velocity_m_min + 0.000104 * velocity_m_min**2 - 4.6
    t_min = time_sec / 60
    pct_vo2max = (
        0.8
        + 0.1894393 * math.exp(-0.012778 * t_min)
        + 0.2989558 * math.exp(-0.1932605 * t_min)
    )
    return vo2 / pct_vo2max


def _interp_row(vdot: float, table: dict[int, dict[str, int]]) -> dict[str, int]:
    keys = sorted(table.keys())
    if vdot <= keys[0]:
        return table[keys[0]]
    if vdot >= keys[-1]:
        return table[keys[-1]]
    for lo, hi in zip(keys, keys[1:]):
        if lo <= vdot <= hi:
            frac = (vdot - lo) / (hi - lo)
            return {
                key: int(table[lo][key] + frac * (table[hi][key] - table[lo][key]))
                for key in table[lo]
            }
    raise ValueError(f"VDOT out of table range: {vdot}")


def training_paces_from_vdot(vdot: float) -> TrainingPaces:
    row = _interp_row(vdot, _load_pace_table())
    return TrainingPaces(
        E=(mile_sec_to_km_sec(row["e_lo"]), mile_sec_to_km_sec(row["e_hi"])),
        M=mile_sec_to_km_sec(row["m"]),
        T=mile_sec_to_km_sec(row["t"]),
        I=mile_sec_to_km_sec(row["i"]),
        R=mile_sec_to_km_sec(row["r"]),
    )


def resolve_distance(label: str) -> tuple[float, str]:
    key = label.strip()
    if key in RACE_DISTANCES_M:
        meters = RACE_DISTANCES_M[key]
        return meters, key
    m = re.match(r"^(\d+(?:\.\d+)?)\s*m?$", key, re.I)
    if m:
        meters = float(m.group(1))
        return meters, f"{int(meters)}m"
    raise ValueError(f"Unsupported distance: {label}")


def build_daniels_block(result: DanielsResult) -> str:
    p = result["paces"]
    e_lo, e_hi = p["E"]
    lines = [
        "【ダニエルズ・ペース】",
        f"根拠: {result['distance_label']} {result['time_display']} → VDOT {result['vdot']:.1f}",
        f"E: {fmt_pace(e_lo)}〜{fmt_pace(e_hi)}/km",
        f"M: {fmt_pace(p['M'])}/km",
        f"T: {fmt_pace(p['T'])}/km",
        f"I: {fmt_pace(p['I'])}/km",
        f"R: {fmt_pace(p['R'])}/km",
        "",
        result["golden_zone_block"],
    ]
    return "\n".join(lines)


def calculate_from_race(distance_label: str, time_str: str) -> DanielsResult:
    distance_m, display_distance = resolve_distance(distance_label)
    time_sec = parse_time(time_str)
    vdot = vdot_from_race(distance_m, time_sec)
    paces = training_paces_from_vdot(vdot)
    t_pace_str = fmt_pace(paces["T"])
    return DanielsResult(
        distance_label=display_distance,
        time_sec=time_sec,
        time_display=format_race_time(time_sec),
        vdot=round(vdot, 1),
        paces=paces,
        t_pace_str=t_pace_str,
        golden_zone_block=build_block(t_pace_str),
    )


def vdot_from_t_pace(t_sec: int) -> float:
    """Find VDOT whose Daniels T pace is closest to t_sec."""
    best_vdot = 50.0
    best_diff = 999
    for i in range(300, 801):
        vdot = i / 10
        diff = abs(training_paces_from_vdot(vdot)["T"] - t_sec)
        if diff < best_diff:
            best_diff = diff
            best_vdot = vdot
    return round(best_vdot, 1)


def calculate_from_t_pace(t_pace_str: str) -> DanielsResult:
    t_sec = parse_pace(t_pace_str)
    best_vdot = vdot_from_t_pace(t_sec)
    paces = training_paces_from_vdot(best_vdot)
    return DanielsResult(
        distance_label="T-pace指定",
        time_sec=0,
        time_display=t_pace_str,
        vdot=round(best_vdot, 1),
        paces=paces,
        t_pace_str=t_pace_str,
        golden_zone_block=build_block(t_pace_str),
    )
