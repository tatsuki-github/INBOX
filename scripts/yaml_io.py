"""Shared YAML event read/write utilities."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

EVENT_DUMP_KEYS = [
    "date",
    "end_date",
    "all_day",
    "category",
    "status",
    "start_time",
    "end_time",
    "location",
    "template_ref",
    "description",
    "practice",
    "weather",
    "tags",
    "urls",
]


def yaml_scalar(value: str) -> str:
    s = str(value)
    if "\n" in s or ":" in s or s.startswith("'") or s.startswith('"'):
        return "'" + s.replace("'", "''") + "'"
    return s


def _dump_scalar(key: str, val: Any, indent: str) -> list[str]:
    if isinstance(val, bool):
        return [f"{indent}{key}: {'true' if val else 'false'}"]
    if key in {"date", "end_date", "start_time", "end_time"}:
        return [f"{indent}{key}: '{val}'"]
    if isinstance(val, (int, float)) and key not in {"description"}:
        return [f"{indent}{key}: {val}"]
    s = str(val)
    if "\n" in s:
        lines = [f"{indent}{key}: |"]
        for row in s.splitlines():
            lines.append(f"{indent}  {row}")
        return lines
    if ":" in s or "'" in s:
        return [f"{indent}{key}: '{s.replace(chr(39), chr(39) * 2)}'"]
    return [f"{indent}{key}: {yaml_scalar(s)}"]


def _dump_practice(practice: dict[str, Any], indent: str) -> list[str]:
    lines = [f"{indent}practice:"]
    sub = indent + "  "
    for key in ("warmup", "notes"):
        if practice.get(key):
            lines.extend(_dump_scalar(key, practice[key], sub))
    if practice.get("absentees") is not None:
        lines.append(f"{sub}absentees:")
        for name in practice["absentees"]:
            lines.append(f"{sub}  - {yaml_scalar(str(name))}")
    if practice.get("abort_if"):
        lines.append(f"{sub}abort_if:")
        for rule in practice["abort_if"]:
            lines.append(f"{sub}  - when: {yaml_scalar(str(rule.get('when', '')))}")
            lines.append(f"{sub}    then: {yaml_scalar(str(rule.get('then', '')))}")
    items = practice.get("items") or []
    if items:
        lines.append(f"{sub}items:")
        for item in items:
            lines.append(f"{sub}  - type: {yaml_scalar(str(item.get('type', 'other')))}")
            for ik, iv in item.items():
                if ik == "type":
                    continue
                if ik == "segments" and isinstance(iv, list):
                    lines.append(f"{sub}    segments:")
                    for seg in iv:
                        lines.append(f"{sub}      - distance_m: {seg['distance_m']}")
                        if seg.get("pace"):
                            lines.append(f"{sub}        pace: {seg['pace']}")
                        if seg.get("intensity"):
                            lines.append(f"{sub}        intensity: {seg['intensity']}")
                elif iv is not None:
                    lines.extend(_dump_scalar(ik, iv, sub + "    "))
    return lines


def _dump_weather(weather: dict[str, Any], indent: str) -> list[str]:
    lines = [f"{indent}weather:"]
    sub = indent + "  "
    key_order = (
        "location",
        "observed_at",
        "condition",
        "temperature_c",
        "humidity_pct",
        "wind_direction",
        "wind_speed_kmh",
        "precipitation_mm",
        "source",
        "fetched_at",
    )
    seen = set()
    for key in key_order:
        if key in weather and weather[key] is not None:
            lines.extend(_dump_scalar(key, weather[key], sub))
            seen.add(key)
    for key, val in weather.items():
        if key not in seen and val is not None:
            lines.extend(_dump_scalar(key, val, sub))
    return lines


def dump_event(ev: dict) -> str:
    lines = [f"- title: {yaml_scalar(ev['title'])}"]
    for key in EVENT_DUMP_KEYS:
        if key not in ev:
            continue
        val = ev[key]
        if key == "practice" and isinstance(val, dict):
            lines.extend(_dump_practice(val, "  "))
        elif key == "weather" and isinstance(val, dict):
            lines.extend(_dump_weather(val, "  "))
        elif key == "tags":
            lines.append("  tags:")
            for t in val:
                lines.append(f"  - {t}")
        elif key == "urls":
            lines.append("  urls:")
            for u in val:
                lines.append(f"  - {u}")
        else:
            lines.extend(_dump_scalar(key, val, "  "))
    return "\n".join(lines)


def write_events_yaml(path: Path, data: dict) -> None:
    text = path.read_text(encoding="utf-8")
    header_match = re.match(r"((?:#.*\n)*)", text)
    header = header_match.group(1) if header_match else ""
    count = len(data["events"])
    header = re.sub(r"^# 件数: \d+", f"# 件数: {count}", header, count=1, flags=re.MULTILINE)
    body = ["events:"]
    body.extend(dump_event(ev) for ev in data["events"])
    path.write_text(header + "year: " + str(data["year"]) + "\n" + "\n".join(body) + "\n", encoding="utf-8")


def load_events_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)
