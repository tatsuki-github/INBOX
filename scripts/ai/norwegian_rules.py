"""Norwegian Method principles for AI prompts and validation."""

from __future__ import annotations

from dataclasses import dataclass

from .intensity_distribution import distribution_guidance_for_prompt


@dataclass(frozen=True)
class NorwegianPrinciple:
    key: str
    title: str
    summary: str
    chapter: str


PRINCIPLES: tuple[NorwegianPrinciple, ...] = (
    NorwegianPrinciple(
        key="core_question",
        title="核心問い",
        summary=(
            "最高強度 × 最高ボリューム × 最低コストで、週を通じて繰り返せるか。"
            "最大努力ではなく controlled（精度・抑制・継続性）。"
        ),
        chapter="Introduction",
    ),
    NorwegianPrinciple(
        key="golden_zone",
        title="Golden Zone (GZ)",
        summary=(
            "真の変曲点（乳酸閾値）直下の狭い強度帯。"
            "刺激は強いがコストが低く、頻繁に繰り返せる。夕練の軽いポイントに適用。"
        ),
        chapter="Ch.2",
    ),
    NorwegianPrinciple(
        key="precision_over_toughness",
        title="精度 > タフさ",
        summary=(
            "イージーデーで速すぎる・ハードデーでも速すぎるグレーゾーンを避ける。"
            "脚フラット・生存インターバルはタフさ不足ではなく精度不足。"
        ),
        chapter="Ch.1",
    ),
    NorwegianPrinciple(
        key="frequency_over_intensity",
        title="頻度 > 強度",
        summary="double threshold、45/15。ワークアウトに勝つより、適応の蓄積を優先。",
        chapter="Ch.5-8",
    ),
    NorwegianPrinciple(
        key="three_elements",
        title="3要素",
        summary="precision（精度）, restraint（抑制）, continuity（継続性）。",
        chapter="Introduction",
    ),
)

SESSION_INTENSITY_MAP = {
    "evening_light": "GZ",
    "threshold": "T",
    "norwegian_4515": "T",
    "race_pace": "RP",
    "interval_hard": "3000mRP",
}


NORWEGIAN_TEMPLATE_IDS = frozenset(
    {
        "norwegian-45-15-base",
        "norwegian-45-15-combo",
        "norwegian-45-15-combination-run",
        "evening-light-600x2",
        "evening-light-300x4",
        "evening-light-900x1",
    }
)


def principles_for_prompt() -> str:
    lines = [
        "# Norwegian Method 原則（Marius Bakken）",
        "",
        distribution_guidance_for_prompt(),
        "",
        "## その他の原則",
    ]
    for p in PRINCIPLES:
        lines.append(f"- **{p.title}** ({p.chapter}): {p.summary}")
    return "\n".join(lines)


def recommend_intensity(session_kind: str) -> str | None:
    return SESSION_INTENSITY_MAP.get(session_kind)
