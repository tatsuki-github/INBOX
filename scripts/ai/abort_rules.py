"""Deterministic abort / cut-down rules for coach-ready sheets."""

from __future__ import annotations

from typing import Any

import yaml

from .config import RULES_PATH
from .session_context import SessionContext


def _abort_thresholds(rules_path=None) -> dict[str, Any]:
    path = rules_path or RULES_PATH
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    abort = data.get("abort") or {}
    return {
        "humidity_pct": int(abort.get("humidity_pct", 85)),
        "precipitation_mm": float(abort.get("precipitation_mm", 1.0)),
        "temperature_c": float(abort.get("temperature_c", 32)),
        "late_split_sec": int(abort.get("late_split_sec", 8)),
    }


def _weather_condition(ctx: SessionContext) -> str:
    weather = ctx.weather or {}
    return str(weather.get("condition") or "")


def build_abort_rules(
    ctx: SessionContext | None,
    practice: dict[str, Any],
    *,
    rules_path=None,
) -> list[dict[str, str]]:
    thresholds = _abort_thresholds(rules_path)
    rules: list[dict[str, str]] = []
    items = practice.get("items") or []
    has_gz = any(item.get("intensity") == "GZ" for item in items)

    if ctx and ctx.prev_meet:
        rules.append({"when": "練習会翌日で脚が重い", "then": "ジョグのみ"})
    if ctx and (ctx.next_meet or ctx.next_race):
        rules.append({"when": "翌日が練習会または記録会", "then": "追い込み禁止。本数を増やさない"})
    if ctx and ctx.race_in_two_days:
        rules.append(
            {
                "when": "大会2日前のRP刺激",
                "then": "1本のみ。本数を増やさない。勝ちにいかない",
            }
        )

    weather = (ctx.weather if ctx else None) or {}
    humidity = weather.get("humidity_pct")
    if isinstance(humidity, (int, float)) and humidity >= thresholds["humidity_pct"]:
        rules.append({"when": f"湿度{int(humidity)}%", "then": "レスト延長、水を必須。厳しければ短縮"})
    precip = weather.get("precipitation_mm")
    condition = _weather_condition(ctx) if ctx else ""
    rainy = "雨" in condition
    if (isinstance(precip, (int, float)) and precip >= thresholds["precipitation_mm"]) or rainy:
        rules.append({"when": "雨が強い / 雷", "then": "短縮または中止"})
    temp = weather.get("temperature_c")
    if isinstance(temp, (int, float)) and temp >= thresholds["temperature_c"]:
        rules.append({"when": f"気温{temp}°C", "then": "本数を増やさない。ジョグペース維持"})

    if has_gz:
        late = thresholds["late_split_sec"]
        rules.append({"when": f"1本目が目安+{late}秒以上遅い", "then": "本数を半分"})
    return rules
