"""Shared metadata for practice_schedules.yaml (actuals mode cutoff)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEDULES_PATH = ROOT / "input" / "practice_schedules.yaml"

# Fallback if key missing (summer schedule closed → actuals from this date).
DEFAULT_ACTUALS_MODE_FROM = "2026-09-19"


def load_schedules_document() -> dict:
    with SCHEDULES_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def actuals_mode_from(doc: dict | None = None) -> str:
    data = doc if doc is not None else load_schedules_document()
    raw = data.get("actuals_mode_from") or DEFAULT_ACTUALS_MODE_FROM
    return str(raw)


def is_actuals_mode_date(date: str, *, cutoff: str | None = None) -> bool:
    """True when date is on/after actuals_mode_from (no planned practice menus)."""
    return date >= (cutoff or actuals_mode_from())
