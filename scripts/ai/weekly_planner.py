"""Weekly practice plan generation with experiment slot."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from .config import load_config
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

    gz_evening_streak = 0
    for day in days:
        tpl = day.template_id or ""
        is_gz_evening = tpl.startswith("evening-light")
        if is_gz_evening:
            gz_evening_streak += 1
            if gz_evening_streak >= 3:
                errors.append(f"too many consecutive GZ evening sessions from {day.date}")
        else:
            gz_evening_streak = 0
    return errors


def _fallback_week_plan(week_start: str, templates: list[dict[str, Any]]) -> WeeklyPlan:
    dates = _week_dates(week_start)
    catalog = {t["id"]: t for t in templates if t.get("id")}
    default_ids = [
        "jog-male-easy",
        None,
        "evening-light-600x2",
        None,
        "evening-light-300x4",
        None,
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
    return WeeklyPlan(
        week_start=week_start,
        weekly_theme="閾値下での精度と継続性（Norwegian Method）",
        days=days,
    )


def _template_match_by_id(template_id: str, templates: list[dict[str, Any]]) -> dict[str, Any] | None:
    for t in templates:
        if t.get("id") == template_id:
            return t
    return None


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

    plan.errors.extend(_validate_weekly_balance(plan.days))

    for day in plan.days:
        if not day.template_id:
            continue
        tpl = _template_match_by_id(day.template_id, templates)
        if not tpl:
            plan.errors.append(f"unknown template_id: {day.template_id}")
            continue
        from .template_selector import TemplateMatch

        match = TemplateMatch(
            template_id=day.template_id,
            label=tpl.get("label") or day.template_id,
            score=1.0,
            practice=tpl.get("practice") or {"items": []},
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
