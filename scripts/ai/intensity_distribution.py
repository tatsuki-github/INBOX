"""Norwegian Method weekly intensity distribution (Easy / Threshold / High).

Planning and output prioritize time-in-zone ratios over GZ session counts.
Reference: Bakken Ch.5 — adjusted 60–65% / 20–30% / 5–10% for 4–6 h/week.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Target ranges for limited-volume runners (middle-school scale)
TARGET_EASY = (0.60, 0.65)
TARGET_THRESHOLD = (0.20, 0.30)
TARGET_HIGH = (0.05, 0.10)

# Validation tolerances (slightly wider than textbook targets)
TOLERANCE_EASY_MIN = 0.55
TOLERANCE_THRESHOLD = (0.15, 0.35)
TOLERANCE_HIGH_MAX = 0.12

WARMUP_EASY_MIN = 5

# template_id → estimated minutes and session role label
TEMPLATE_PROFILES: dict[str, dict[str, Any]] = {
    "jog-male-easy": {
        "easy": 50,
        "threshold": 0,
        "high": 0,
        "role": "Easy: volume",
    },
    "jog-female-easy": {
        "easy": 45,
        "threshold": 0,
        "high": 0,
        "role": "Easy: volume",
    },
    "jog-male-3360": {
        "easy": 28,
        "threshold": 0,
        "high": 0,
        "role": "Easy: track jog",
    },
    "jog-female-2800": {
        "easy": 24,
        "threshold": 0,
        "high": 0,
        "role": "Easy: track jog",
    },
    "evening-light-600x2": {
        "easy": 25,
        "threshold": 18,
        "high": 0,
        "role": "Threshold: Main quality",
    },
    "evening-light-300x4": {
        "easy": 25,
        "threshold": 14,
        "high": 0,
        "role": "Threshold: Support quality",
    },
    "evening-light-900x1": {
        "easy": 25,
        "threshold": 10,
        "high": 0,
        "role": "Threshold: Support quality",
    },
    "interval-300-rp": {
        "easy": 15,
        "threshold": 0,
        "high": 12,
        "role": "High: X-session",
    },
    "interval-600-3000rp": {
        "easy": 20,
        "threshold": 16,
        "high": 0,
        "role": "Threshold: Main quality",
    },
    "set-male-2100-900": {
        "easy": 20,
        "threshold": 22,
        "high": 0,
        "role": "Threshold: Main quality",
    },
    "set-female-1200-900": {
        "easy": 18,
        "threshold": 18,
        "high": 0,
        "role": "Threshold: Main quality",
    },
    "interval-900-progressive": {
        "easy": 18,
        "threshold": 20,
        "high": 0,
        "role": "Threshold: Main quality",
    },
    "longset-male-2000-1000": {
        "easy": 20,
        "threshold": 24,
        "high": 0,
        "role": "Threshold: Main quality",
    },
    "longset-female-1000x2": {
        "easy": 18,
        "threshold": 18,
        "high": 0,
        "role": "Threshold: Main quality",
    },
    "norwegian-45-15-base": {
        "easy": 10,
        "threshold": 22,
        "high": 0,
        "role": "Threshold: Support quality (45/15)",
    },
    "norwegian-45-15-combo": {
        "easy": 10,
        "threshold": 24,
        "high": 4,
        "role": "Threshold: Main quality (45/15)",
    },
    "norwegian-45-15-combination-run": {
        "easy": 45,
        "threshold": 18,
        "high": 0,
        "role": "Easy + Threshold (45/15 combo)",
    },
}

INTENSITY_TO_BUCKET = {
    "E": "easy",
    "T": "threshold",
    "GZ": "threshold",
    "RP": "high",
    "1500mRP": "high",
    "3000mRP": "threshold",
    "I": "high",
    "R": "high",
}


@dataclass
class BucketMinutes:
    easy: float = 0.0
    threshold: float = 0.0
    high: float = 0.0

    def total(self) -> float:
        return self.easy + self.threshold + self.high

    def as_dict(self) -> dict[str, float]:
        return {
            "easy": round(self.easy, 1),
            "threshold": round(self.threshold, 1),
            "high": round(self.high, 1),
        }

    def __iadd__(self, other: BucketMinutes) -> BucketMinutes:
        self.easy += other.easy
        self.threshold += other.threshold
        self.high += other.high
        return self


@dataclass
class SessionIntensity:
    date: str
    title: str
    template_id: str | None
    role: str
    minutes: BucketMinutes = field(default_factory=BucketMinutes)

    def as_dict(self) -> dict[str, Any]:
        total = self.minutes.total()
        return {
            "date": self.date,
            "title": self.title,
            "template_id": self.template_id,
            "role": self.role,
            "minutes": self.minutes.as_dict(),
            "share_pct": _share_pct(self.minutes) if total > 0 else None,
        }


@dataclass
class WeeklyIntensitySummary:
    sessions: list[SessionIntensity] = field(default_factory=list)
    totals: BucketMinutes = field(default_factory=BucketMinutes)
    share_pct: dict[str, float] = field(default_factory=dict)
    within_target: bool = True
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": distribution_targets_for_output(),
            "totals_minutes": self.totals.as_dict(),
            "share_pct": self.share_pct,
            "within_target": self.within_target,
            "notes": self.notes,
            "sessions": [s.as_dict() for s in self.sessions],
        }


def distribution_targets_for_output() -> dict[str, str]:
    return {
        "easy": "60–65%",
        "threshold": "20–30%",
        "high": "5–10%",
        "priority": "時間割合を優先（GZ回数ではなく Easy/Threshold/High の週合計）",
    }


def distribution_guidance_for_prompt() -> str:
    return "\n".join(
        [
            "## 週間強度配分（計画・出力の最優先）",
            "Bakken Ch.5 調整配分（週4–6h）:",
            "- **Easy 60–65%** — HRmax 70%未満。グレーゾーン禁止",
            "- **Threshold 20–30%** — GZ/T/45-15。Main quality（長め）+ Support quality（短め）",
            "- **High 5–10%** — X-session（短RP・スプリント）。週1まで",
            "",
            "「週N回GZ」ではなく、上記**時間割合**が週末に収まるよう日を割り当てる。",
            "Main quality は Threshold 枠の中心（例: 600m×3–4）。Support は短GZ（300m系）。",
            "Easy 日を削って Threshold を足さない。",
        ]
    )


def profile_for_template(template_id: str | None) -> dict[str, Any]:
    if not template_id:
        return {
            "easy": 0,
            "threshold": 0,
            "high": 0,
            "role": "Rest / off",
        }
    return TEMPLATE_PROFILES.get(
        template_id,
        {
            "easy": 20,
            "threshold": 10,
            "high": 0,
            "role": "Mixed (estimate)",
        },
    )


def session_intensity_from_template(
    date: str,
    title: str,
    template_id: str | None,
) -> SessionIntensity:
    profile = profile_for_template(template_id)
    return SessionIntensity(
        date=date,
        title=title,
        template_id=template_id,
        role=str(profile["role"]),
        minutes=BucketMinutes(
            easy=float(profile.get("easy") or 0),
            threshold=float(profile.get("threshold") or 0),
            high=float(profile.get("high") or 0),
        ),
    )


def _rep_count(reps: Any) -> float:
    if reps is None:
        return 1.0
    if isinstance(reps, (int, float)):
        return float(reps)
    text = str(reps)
    if "-" in text:
        parts = [float(p) for p in text.split("-") if p.strip().isdigit()]
        return sum(parts) / len(parts) if parts else 1.0
    return float(text) if text.isdigit() else 1.0


def _interval_work_minutes(item: dict[str, Any]) -> float:
    reps = _rep_count(item.get("reps"))
    if item.get("distance_km"):
        return reps * float(item["distance_km"]) * 5.0  # ~5 min/km heuristic
    distance_m = float(item.get("distance_m") or 400)
    # middle-school GZ/T: ~70–80 sec per 300m equivalent
    return reps * (distance_m / 300.0) * 1.2


def estimate_practice_minutes(practice: dict[str, Any] | None) -> BucketMinutes:
    if not practice:
        return BucketMinutes()
    minutes = BucketMinutes(easy=WARMUP_EASY_MIN if practice.get("warmup") else 0.0)
    for item in practice.get("items") or []:
        itype = item.get("type") or ""
        intensity = str(item.get("intensity") or "").upper()
        bucket = INTENSITY_TO_BUCKET.get(intensity)
        if itype == "jog":
            km = item.get("distance_km")
            if km is None:
                km_min = item.get("distance_km_min")
                km_max = item.get("distance_km_max")
                if km_min is not None and km_max is not None:
                    km = (float(km_min) + float(km_max)) / 2.0
                elif item.get("laps"):
                    km = float(item["laps"]) * 560.0 / 1000.0
                elif item.get("distance_m"):
                    km = float(item["distance_m"]) / 1000.0
            minutes.easy += float(km or 4.5) * 5.0
        elif itype in {"interval", "set"}:
            work = _interval_work_minutes(item)
            rest = float(item.get("rest_sec") or 60) / 60.0
            reps = _rep_count(item.get("reps"))
            block = work + rest * max(reps - 1, 0)
            if bucket == "high":
                minutes.high += block
            elif bucket == "threshold":
                minutes.threshold += block
            else:
                minutes.threshold += block * 0.7
                minutes.easy += block * 0.3
        elif itype == "strides":
            minutes.high += 5.0
        else:
            minutes.easy += 5.0
    return minutes


def session_intensity_from_practice(
    date: str,
    title: str,
    template_id: str | None,
    practice: dict[str, Any] | None,
) -> SessionIntensity:
    profile = profile_for_template(template_id)
    profile_minutes = BucketMinutes(
        easy=float(profile.get("easy") or 0),
        threshold=float(profile.get("threshold") or 0),
        high=float(profile.get("high") or 0),
    )
    if practice and practice.get("items"):
        estimated = estimate_practice_minutes(practice)
        minutes = BucketMinutes(
            easy=max(profile_minutes.easy, estimated.easy),
            threshold=max(profile_minutes.threshold, estimated.threshold),
            high=max(profile_minutes.high, estimated.high),
        )
    else:
        minutes = profile_minutes
    return SessionIntensity(
        date=date,
        title=title,
        template_id=template_id,
        role=str(profile["role"]),
        minutes=minutes,
    )


def _share_pct(minutes: BucketMinutes) -> dict[str, float]:
    total = minutes.total()
    if total <= 0:
        return {"easy": 0.0, "threshold": 0.0, "high": 0.0}
    return {
        "easy": round(100.0 * minutes.easy / total, 1),
        "threshold": round(100.0 * minutes.threshold / total, 1),
        "high": round(100.0 * minutes.high / total, 1),
    }


def summarize_week_intensity(
    days: list[Any],
    *,
    use_practice: bool = True,
) -> WeeklyIntensitySummary:
    """Aggregate intensity from DayPlan-like objects (date, title, template_id, generation)."""
    summary = WeeklyIntensitySummary()
    for day in days:
        template_id = getattr(day, "template_id", None)
        practice = None
        generation = getattr(day, "generation", None)
        if use_practice and generation is not None:
            practice = getattr(generation, "practice", None)
        if template_id or practice:
            session = session_intensity_from_practice(
                getattr(day, "date", ""),
                getattr(day, "title", ""),
                template_id,
                practice,
            )
        else:
            session = session_intensity_from_template(
                getattr(day, "date", ""),
                getattr(day, "title", ""),
                None,
            )
        summary.sessions.append(session)
        summary.totals += session.minutes

    summary.share_pct = _share_pct(summary.totals)
    summary.notes = _evaluate_distribution(summary.totals, summary.share_pct)
    summary.within_target = not any(n.startswith("ERROR:") for n in summary.notes)
    return summary


def _evaluate_distribution(totals: BucketMinutes, share: dict[str, float]) -> list[str]:
    notes: list[str] = []
    total = totals.total()
    if total <= 0:
        notes.append("INFO: no practice minutes scheduled this week")
        return notes

    easy_r = share["easy"] / 100.0
    th_r = share["threshold"] / 100.0
    hi_r = share["high"] / 100.0

    if easy_r < TOLERANCE_EASY_MIN:
        notes.append(
            f"ERROR: Easy {share['easy']:.1f}% below minimum {TOLERANCE_EASY_MIN * 100:.0f}% "
            f"(target {TARGET_EASY[0]*100:.0f}–{TARGET_EASY[1]*100:.0f}%) — add Easy days or shorten Threshold"
        )
    elif easy_r < TARGET_EASY[0]:
        notes.append(
            f"WARN: Easy {share['easy']:.1f}% slightly low (target 60–65%)"
        )

    if th_r < TOLERANCE_THRESHOLD[0]:
        notes.append(
            f"WARN: Threshold {share['threshold']:.1f}% below {TOLERANCE_THRESHOLD[0]*100:.0f}% "
            f"(target 20–30%)"
        )
    elif th_r > TOLERANCE_THRESHOLD[1]:
        notes.append(
            f"ERROR: Threshold {share['threshold']:.1f}% exceeds {TOLERANCE_THRESHOLD[1]*100:.0f}% "
            f"(target 20–30%) — reduce Main/Support sessions, do not add GZ for count alone"
        )

    if hi_r > TOLERANCE_HIGH_MAX:
        notes.append(
            f"ERROR: High {share['high']:.1f}% exceeds {TOLERANCE_HIGH_MAX*100:.0f}% (target 5–10%)"
        )

    if not notes:
        notes.append(
            f"OK: distribution Easy {share['easy']:.1f}% / "
            f"Threshold {share['threshold']:.1f}% / High {share['high']:.1f}%"
        )
    return notes


def validate_weekly_intensity(days: list[Any]) -> list[str]:
    """Return validation error strings (empty if distribution OK)."""
    summary = summarize_week_intensity(days)
    return [n for n in summary.notes if n.startswith("ERROR:")]


def format_session_header(
    template_id: str | None,
    practice: dict[str, Any] | None = None,
) -> str:
    """Human-readable session line prioritizing intensity role over GZ label."""
    profile = profile_for_template(template_id)
    role = str(profile["role"])
    if practice and practice.get("items"):
        minutes = estimate_practice_minutes(practice)
        share = _share_pct(minutes)
        return (
            f"{role} — "
            f"Easy {share['easy']:.0f}% / Threshold {share['threshold']:.0f}% / "
            f"High {share['high']:.0f}% (session est.)"
        )
    return role
