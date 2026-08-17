"""Weekly practice plan generation with experiment slot."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from .config import load_config
from .intensity_distribution import (
    WeeklyIntensitySummary,
    summarize_week_intensity,
    validate_weekly_intensity,
)
from .llm_client import LLMClient, create_llm_client, extract_json_object
from .practice_generator import GenerationResult, generate_practice
from .prompt_builder import build_weekly_system_prompt, build_weekly_user_prompt
from .rag.retriever import retrieve_context
from .template_selector import load_templates


@dataclass
class DayPlan:
    date: str
    title: str
    template_id: str | None
    is_experiment: bool = False
    coach_note: str | None = None
    generation: GenerationResult | None = None


@dataclass
class WeeklyPlan:
    week_start: str
    weekly_theme: str
    days: list[DayPlan] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    intensity: WeeklyIntensitySummary | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


def _week_dates(week_start: str) -> list[str]:
    start = date.fromisoformat(week_start)
    return [(start + timedelta(days=i)).isoformat() for i in range(7)]


def _validate_weekly_balance(days: list[DayPlan]) -> list[str]:
    errors: list[str] = []
    experiments = sum(1 for d in days if d.is_experiment)
    if experiments > 1:
        errors.append(f"at most 1 experiment per week, got {experiments}")

    errors.extend(validate_weekly_intensity(days))
    return errors


def _fallback_week_plan(week_start: str, templates: list[dict[str, Any]]) -> WeeklyPlan:
    dates = _week_dates(week_start)
    catalog = {t["id"]: t for t in templates if t.get("id")}
    # Easy-heavy week: Threshold ~20–25% via Main + Support (not GZ count)
    default_ids = [
        "jog-male-easy",
        None,
        "evening-light-300x4",
        None,
        "evening-light-600x2",
        "jog-female-easy",
        None,
    ]
    days: list[DayPlan] = []
    for idx, d in enumerate(dates):
        tid = default_ids[idx] if idx < len(default_ids) else None
        title = "岱明練習" if tid else "休息"
        if tid and tid in catalog:
            title = catalog[tid].get("label") or title
        days.append(
            DayPlan(
                date=d,
                title=title,
                template_id=tid,
                is_experiment=False,
            )
        )
    plan = WeeklyPlan(
        week_start=week_start,
        weekly_theme="Easy 60–65% / Threshold 20–30% — 精度と継続性（Norwegian Method）",
        days=days,
    )
    plan.intensity = summarize_week_intensity(plan.days)
    return plan


def _template_match_by_id(template_id: str, templates: list[dict[str, Any]]) -> dict[str, Any] | None:
    for t in templates:
        if t.get("id") == template_id:
            return t
    return None


def _apply_pre_race_calendar_overrides(days: list[DayPlan]) -> None:
    from .pre_race_stimulus import should_apply_pre_race_stimulus, stimulus_for_events
    from .session_context import load_session_context
    from .template_selector import select_template_by_id

    for day in days:
        ctx = load_session_context(day.date, session="evening", year=int(day.date[:4]))
        if not should_apply_pre_race_stimulus(
            race_in_two_days=ctx.race_in_two_days,
            next_race=ctx.next_race,
            next_meet=False,
            session="evening",
            query=day.coach_note or "",
        ):
            continue
        preview = ctx.next_race_in_two_days
        stimulus = stimulus_for_events(preview.events if preview else [])
        if select_template_by_id(stimulus.template_id) is None:
            continue
        day.template_id = stimulus.template_id
        day.title = stimulus.label
        day.coach_note = stimulus.notes
        day.is_experiment = False


def plan_week(
    week_start: str,
    *,
    guidance: str | None = None,
    llm: LLMClient | None = None,
    dry_run: bool = False,
) -> WeeklyPlan:
    templates = load_templates()
    rag_context = "\n---\n".join(retrieve_context(f"weekly plan {week_start} {guidance or ''}", top_k=5))

    if dry_run or llm is None:
        plan = _fallback_week_plan(week_start, templates)
    else:
        system = build_weekly_system_prompt()
        user = build_weekly_user_prompt(week_start, templates, guidance=guidance, rag_context=rag_context)
        try:
            raw = llm.complete(system, user)
            data = extract_json_object(raw)
            days = []
            for item in data.get("days") or []:
                days.append(
                    DayPlan(
                        date=item.get("date", ""),
                        title=item.get("title") or "練習",
                        template_id=item.get("template_id"),
                        is_experiment=bool(item.get("is_experiment")),
                        coach_note=item.get("coach_note"),
                    )
                )
            plan = WeeklyPlan(
                week_start=week_start,
                weekly_theme=str(data.get("weekly_theme") or ""),
                days=days,
            )
        except (ValueError, KeyError) as exc:
            plan = _fallback_week_plan(week_start, templates)
            plan.errors.append(f"LLM weekly plan parse failed: {exc}")

    _apply_pre_race_calendar_overrides(plan.days)
    plan.errors.extend(_validate_weekly_balance(plan.days))

    for day in plan.days:
        if not day.template_id:
            continue
        tpl = _template_match_by_id(day.template_id, templates)
        if not tpl:
            plan.errors.append(f"unknown template_id: {day.template_id}")
            continue
        from .template_selector import TemplateMatch

        practice = copy.deepcopy(tpl.get("practice") or {"items": []})
        if day.coach_note and str(day.template_id).startswith("pre-race-rp-"):
            practice["notes"] = day.coach_note
        match = TemplateMatch(
            template_id=day.template_id,
            label=tpl.get("label") or day.template_id,
            score=1.0,
            practice=practice,
        )
        query = day.coach_note or day.title or day.template_id
        if day.is_experiment:
            query = f"【実験】{query}"
        result = generate_practice(
            query,
            title=day.title,
            template=match,
            llm=llm,
            dry_run=dry_run or llm is None,
            is_experiment=day.is_experiment,
        )
        day.generation = result
        if not result.ok:
            plan.errors.extend([f"{day.date}: {e}" for e in result.errors])

    plan.intensity = summarize_week_intensity(plan.days, use_practice=True)
    return plan


def plan_week_auto(
    week_start: str,
    *,
    guidance: str | None = None,
    dry_run: bool = False,
) -> WeeklyPlan:
    config = load_config()
    llm = None if dry_run else create_llm_client(config)
    return plan_week(week_start, guidance=guidance, llm=llm, dry_run=dry_run or llm is None)
