"""Fixed / variable / creative layer validation for AI-generated practice."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from practice_models import INTENSITIES, LAP_M

from .config import RULES_PATH


@dataclass(frozen=True)
class GenerationRules:
    fixed: dict[str, Any]
    variable: dict[str, Any]
    creative: dict[str, Any]
    template_required_intensities: frozenset[str]


def load_rules(path: Path | None = None) -> GenerationRules:
    rules_path = path or RULES_PATH
    data = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
    return GenerationRules(
        fixed=data.get("fixed") or {},
        variable=data.get("variable") or {},
        creative=data.get("creative") or {},
        template_required_intensities=frozenset(data.get("template_required_intensities") or []),
    )


def _parse_reps(reps: Any) -> tuple[int, int]:
    if isinstance(reps, int):
        return reps, reps
    if isinstance(reps, str):
        m = re.match(r"^(\d+)(?:-(\d+))?$", reps.strip())
        if m:
            lo = int(m.group(1))
            hi = int(m.group(2) or lo)
            return lo, hi
    raise ValueError(f"Cannot parse reps: {reps!r}")


def _parse_pace_sec(pace: str) -> int:
    m = re.fullmatch(r"k/(\d+):(\d{2})", pace.strip())
    if not m:
        raise ValueError(f"Invalid pace: {pace!r}")
    return int(m.group(1)) * 60 + int(m.group(2))


def _item_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        item.get("type"),
        item.get("group"),
        item.get("distance_m"),
        item.get("intensity"),
        item.get("label"),
    )


def _within_reps_delta(base: Any, candidate: Any, delta: int) -> bool:
    try:
        b_lo, b_hi = _parse_reps(base)
        c_lo, c_hi = _parse_reps(candidate)
    except ValueError:
        return base == candidate
    return abs(c_lo - b_lo) <= delta and abs(c_hi - b_hi) <= delta


def _within_pace_delta(base: str | None, candidate: str | None, delta: int) -> bool:
    if base is None and candidate is None:
        return True
    if base is None or candidate is None:
        return False
    return abs(_parse_pace_sec(base) - _parse_pace_sec(candidate)) <= delta


def validate_template_diff(
    base_items: list[dict[str, Any]],
    candidate_items: list[dict[str, Any]],
    rules: GenerationRules,
    *,
    is_experiment: bool = False,
) -> list[str]:
    """Ensure candidate items are template base + allowed variable deltas."""
    errors: list[str] = []
    delta_reps = int(rules.variable.get("reps_delta", 2))
    delta_pace = int(rules.variable.get("pace_delta_sec_per_km", 10))
    delta_rest = int(rules.variable.get("rest_sec_delta", 30))
    max_new = int((rules.creative.get("weekly_experiment") or {}).get("max_new_items", 2))

    base_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in base_items:
        base_by_key[_item_key(item)] = item

    matched = 0
    new_items = 0
    for idx, cand in enumerate(candidate_items):
        key = _item_key(cand)
        base = base_by_key.get(key)
        intensity = cand.get("intensity")
        if intensity and intensity in rules.template_required_intensities and base is None:
            if not is_experiment:
                errors.append(
                    f"items[{idx}]: intensity {intensity} requires template base (not experiment)"
                )
            else:
                new_items += 1
            continue

        if base is None:
            new_items += 1
            continue

        matched += 1
        if not _within_reps_delta(base.get("reps"), cand.get("reps"), delta_reps):
            errors.append(f"items[{idx}]: reps out of variable range")
        for pace_field in ("pace", "pace_min", "pace_max"):
            if not _within_pace_delta(base.get(pace_field), cand.get(pace_field), delta_pace):
                errors.append(f"items[{idx}]: {pace_field} out of variable range")
        base_rest = base.get("rest_sec")
        cand_rest = cand.get("rest_sec")
        if base_rest is not None and cand_rest is not None:
            if abs(int(cand_rest) - int(base_rest)) > delta_rest:
                errors.append(f"items[{idx}]: rest_sec out of variable range")

    if is_experiment and new_items > max_new:
        errors.append(f"experiment exceeds max_new_items ({max_new})")

    if not is_experiment and new_items > 0 and matched == 0 and base_items:
        errors.append("candidate has new items but no template match")

    return errors


def validate_fixed_constraints(practice: dict[str, Any], rules: GenerationRules) -> list[str]:
    errors: list[str] = []
    lap_m = int(rules.fixed.get("track_lap_m", LAP_M))
    for idx, item in enumerate(practice.get("items") or []):
        laps = item.get("laps")
        distance_m = item.get("distance_m")
        if laps is not None and distance_m is not None:
            expected = laps * lap_m
            if int(distance_m) != expected:
                errors.append(f"items[{idx}]: distance_m {distance_m} != laps*{lap_m}")
        for pace_field in ("pace", "pace_min", "pace_max"):
            pace = item.get(pace_field)
            if pace and not re.fullmatch(r"k/\d+:\d{2}", pace):
                errors.append(f"items[{idx}]: invalid {pace_field} {pace}")
        intensity = item.get("intensity")
        if intensity and intensity not in INTENSITIES:
            errors.append(f"items[{idx}]: unknown intensity {intensity}")
    return errors


def validate_experiment_notes(practice: dict[str, Any], rules: GenerationRules, *, is_experiment: bool) -> list[str]:
    if not is_experiment:
        return []
    prefix = (rules.creative.get("weekly_experiment") or {}).get("require_notes_prefix", "【実験】")
    notes = practice.get("notes") or ""
    if prefix and not str(notes).startswith(prefix):
        return [f"notes must start with {prefix!r} for experiment sessions"]
    forbidden = frozenset((rules.creative.get("weekly_experiment") or {}).get("forbidden_intensities") or [])
    errors: list[str] = []
    for idx, item in enumerate(practice.get("items") or []):
        intensity = item.get("intensity")
        if intensity in forbidden:
            errors.append(f"items[{idx}]: intensity {intensity} forbidden in experiment")
    return errors


def apply_template_base(template_practice: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(template_practice)
