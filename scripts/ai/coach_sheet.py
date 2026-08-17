"""Assemble a coach-ready field sheet from practice + session context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from practice_renderer import render_item_line
from practice_utils import format_absentees

from .abort_rules import build_abort_rules
from .session_context import SessionContext
from .split_times import annotate_interval_line

Confidence = Literal["adopt", "review", "withhold"]

SESSION_LABEL = {"morning": "岱明朝練", "evening": "岱明夕練"}


@dataclass
class CoachSheet:
    header: str
    readout: str
    abort_lines: list[str]
    checklist: list[str]
    confidence: Confidence
    description_for_apply: str
    abort_if: list[dict[str, str]] = field(default_factory=list)
    text: str = ""

    def render(self) -> str:
        return self.text or _join_sheet(self)


def _join_sheet(sheet: CoachSheet) -> str:
    parts = [sheet.header, "", sheet.readout]
    if sheet.abort_lines:
        parts.extend(["", "切上げ", *[f"- {line}" for line in sheet.abort_lines]])
    if sheet.checklist:
        parts.extend(["", "確認（名前は書かない）", *[f"- {line}" for line in sheet.checklist]])
    return "\n".join(parts).strip() + "\n"


def _format_weather(weather: dict[str, Any] | None) -> str | None:
    if not weather:
        return None
    bits: list[str] = []
    temp = weather.get("temperature_c")
    if isinstance(temp, (int, float)):
        bits.append(f"{temp}°C")
    humidity = weather.get("humidity_pct")
    if isinstance(humidity, (int, float)):
        bits.append(f"湿度{int(humidity)}%")
    condition = weather.get("condition")
    if condition:
        bits.append(str(condition))
    return " ".join(bits) if bits else None


def _neighbor_label(titles: list[str], meet: bool, race: bool) -> str:
    if meet:
        meets = [t for t in titles if "練習会" in t]
        return meets[0] if meets else "練習会"
    if race:
        races = [t for t in titles if "記録会" in t or "選手権" in t]
        return races[0] if races else "記録会"
    return "—"


def _build_header(ctx: SessionContext | None, session: str, confidence: Confidence) -> str:
    if ctx is None:
        return f"【{SESSION_LABEL.get(session, session)}】\n信頼度: {confidence}"
    label = SESSION_LABEL.get(session, session)
    clock = ""
    if ctx.start_time and ctx.end_time:
        clock = f" {ctx.start_time}–{ctx.end_time}"
    elif ctx.start_time:
        clock = f" {ctx.start_time}"
    lines = [f"【{ctx.date}（{ctx.weekday}）{label}{clock}】"]
    prev = _neighbor_label(ctx.prev_titles, ctx.prev_meet, False)
    next_label = _neighbor_label(ctx.next_titles, ctx.next_meet, ctx.next_race)
    lines.append(f"前後: 前日={prev} / 翌日={next_label}")
    if ctx.race_in_two_days and ctx.next_race_in_two_days:
        lines.append(f"2日後: {ctx.next_race_in_two_days.title}")
    weather_line = _format_weather(ctx.weather)
    if weather_line:
        lines.append(f"天候: {weather_line}")
    lines.append(f"信頼度: {confidence}")
    return "\n".join(lines)


def _readout_body(practice: dict[str, Any], t_pace: str) -> str:
    lines: list[str] = []
    warmup = practice.get("warmup")
    if warmup:
        lines.append(str(warmup))
    absentee_line = format_absentees(practice.get("absentees"))
    if absentee_line:
        if lines:
            lines.append("")
        lines.append(absentee_line)
    items = practice.get("items") or []
    if items:
        if lines:
            lines.append("")
        for item in items:
            line = render_item_line(item)
            lines.append(annotate_interval_line(item, line, t_pace))
    return "\n".join(lines).strip()


def decide_confidence(
    *,
    ok: bool,
    template_id: str | None,
    is_experiment: bool,
    ctx: SessionContext | None,
) -> Confidence:
    if not ok or not template_id:
        return "withhold"
    if is_experiment:
        return "review"
    if ctx and (ctx.prev_meet or ctx.next_meet or ctx.next_race or ctx.race_in_two_days):
        return "review"
    weather = (ctx.weather if ctx else None) or {}
    humidity = weather.get("humidity_pct")
    precip = weather.get("precipitation_mm")
    temp = weather.get("temperature_c")
    condition = str(weather.get("condition") or "")
    if isinstance(humidity, (int, float)) and humidity >= 85:
        return "review"
    if isinstance(precip, (int, float)) and precip >= 1.0:
        return "review"
    if "雨" in condition:
        return "review"
    if isinstance(temp, (int, float)) and temp >= 32:
        return "review"
    return "adopt"


def build_coach_sheet(
    practice: dict[str, Any],
    *,
    ctx: SessionContext | None = None,
    session: str = "evening",
    t_pace: str = "4:01",
    ok: bool = True,
    template_id: str | None = None,
    is_experiment: bool = False,
) -> CoachSheet:
    confidence = decide_confidence(
        ok=ok,
        template_id=template_id,
        is_experiment=is_experiment,
        ctx=ctx,
    )
    abort_if = build_abort_rules(ctx, practice)
    abort_lines = [f"{r['when']} → {r['then']}" for r in abort_if]
    readout = _readout_body(practice, t_pace)
    notes = practice.get("notes")
    apply_parts = [readout]
    if abort_lines:
        apply_parts.extend(["", "切上げ", *[f"- {line}" for line in abort_lines]])
    if notes:
        apply_parts.extend(["", str(notes)])
    description_for_apply = "\n".join(p for p in apply_parts if p).strip() + "\n"
    checklist = ["例外グループ（特定選手だけ距離変更など）があれば手で追記"]
    if ctx and ctx.race_in_two_days:
        checklist.append(
            "出場種目を確認（800m→600m×1 / 1500m→900m×1または1000m×1）。連続は1000mまで"
        )
    sheet = CoachSheet(
        header=_build_header(ctx, session, confidence),
        readout=readout,
        abort_lines=abort_lines,
        checklist=checklist,
        confidence=confidence,
        description_for_apply=description_for_apply,
        abort_if=abort_if,
    )
    sheet.text = _join_sheet(sheet)
    return sheet


def attach_abort_if(practice: dict[str, Any], abort_if: list[dict[str, str]]) -> dict[str, Any]:
    if abort_if:
        practice["abort_if"] = abort_if
    return practice
