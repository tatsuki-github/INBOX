"""Prompt assembly for AI practice generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .config import PROMPTS_DIR
from .intensity_distribution import (
    distribution_guidance_for_prompt,
    distribution_targets_for_output,
)
from .norwegian_rules import principles_for_prompt
from .pace_calculator import build_block
from .template_selector import TemplateMatch


def _read_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    return path.read_text(encoding="utf-8")


def build_practice_system_prompt(*, t_pace: str | None = "4:01") -> str:
    base = _read_prompt("system-practice-gen.md")
    norwegian = principles_for_prompt()
    pace_table = build_block(t_pace or "4:01")
    return f"{base}\n\n{norwegian}\n\n## Reference pace table (T={t_pace or '4:01'}/km)\n{pace_table}"


def build_practice_user_prompt(
    query: str,
    template: TemplateMatch,
    *,
    lint_errors: list[str] | None = None,
) -> str:
    payload = {
        "coach_request": query,
        "selected_template_id": template.template_id,
        "selected_template_label": template.label,
        "template_practice": template.practice,
    }
    if lint_errors:
        payload["previous_validation_errors"] = lint_errors
        payload["instruction"] = "Fix validation errors. Keep template structure."
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_weekly_system_prompt() -> str:
    return _read_prompt("system-weekly-plan.md")


def build_weekly_user_prompt(
    week_start: str,
    templates: list[dict[str, Any]],
    *,
    guidance: str | None = None,
    rag_context: str | None = None,
) -> str:
    catalog = [
        {"id": t.get("id"), "label": t.get("label")}
        for t in templates
        if t.get("id")
    ]
    payload: dict[str, Any] = {
        "week_start": week_start,
        "template_catalog": catalog,
        "intensity_distribution_targets": distribution_targets_for_output(),
        "planning_priority": distribution_guidance_for_prompt(),
    }
    if guidance:
        payload["coach_guidance"] = guidance
    if rag_context:
        payload["reference_context"] = rag_context
    payload["norwegian_principles"] = principles_for_prompt()
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_explain_system_prompt() -> str:
    return _read_prompt("system-explain.md")


def build_explain_user_prompt(question: str, context_chunks: list[str]) -> str:
    return json.dumps(
        {"question": question, "context": context_chunks},
        ensure_ascii=False,
        indent=2,
    )


def load_few_shot_examples() -> list[dict[str, str]]:
    path = PROMPTS_DIR / "few-shot-examples.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("examples") or []
