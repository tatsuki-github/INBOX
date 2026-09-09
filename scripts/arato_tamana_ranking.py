"""所属別ランキング（実記録・3000m 予想）の算出。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from arato_tamana_records import AffiliationSection, RecordRow

BOYS_TOP_NS = (4, 5, 6)
GIRLS_TOP_NS = (3, 4, 5)
BOYS_MIN_ATHLETES = BOYS_TOP_NS[-1]
GIRLS_MIN_ATHLETES = GIRLS_TOP_NS[-1]
RANKING_GENDERS = ("男子", "女子")
TOP_N_NOTE = (
    "男子は上位4/5/6人平均（6人未満の所属は対象外）、"
    "女子は上位3/4/5人平均（5人未満の所属は対象外）です。"
)


@dataclass
class AffiliationRankingEntry:
    affiliation: str
    athlete_count: int
    averages: dict[int, float | None] = field(default_factory=dict)
    sort_key: float | None = None
    rank: int = 0


@dataclass
class GenderRankingTable:
    gender: str
    top_ns: tuple[int, ...]
    entries: list[AffiliationRankingEntry]


@dataclass
class RankingCategorySpec:
    key: str
    title: str
    note: str
    value_fn: Callable[[list[RecordRow]], float | None]


@dataclass
class CategoryRankings:
    spec: RankingCategorySpec
    boys: GenderRankingTable
    girls: GenderRankingTable


def format_seconds(seconds: float) -> str:
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return f"{minutes}:{remainder:05.2f}"


def _best_seconds_at_distance(
    rows: list[RecordRow],
    distance: str,
    *,
    sb_only: bool,
) -> float | None:
    candidates = [
        row.record_seconds
        for row in rows
        if row.distance == distance and row.record_seconds is not None and (not sb_only or row.sb_adopted)
    ]
    if not candidates:
        return None
    return min(candidates)


def best_seconds_at_distance(rows: list[RecordRow], distance: str) -> float | None:
    """指定距離の SB を優先し、なければベストタイムを返す。"""
    for sb_only in (True, False):
        seconds = _best_seconds_at_distance(rows, distance, sb_only=sb_only)
        if seconds is not None:
            return seconds
    return None


def project_3000m_seconds(rows: list[RecordRow]) -> float | None:
    """3000m SB → 1500m SB換算 → 800m SB換算の順で 3000m 予想秒を返す。"""
    for sb_only in (True, False):
        t3000 = _best_seconds_at_distance(rows, "3000m", sb_only=sb_only)
        if t3000 is not None:
            return t3000

    for sb_only in (True, False):
        t1500 = _best_seconds_at_distance(rows, "1500m", sb_only=sb_only)
        if t1500 is not None:
            return t1500 * 2 + 30

    for sb_only in (True, False):
        t800 = _best_seconds_at_distance(rows, "800m", sb_only=sb_only)
        if t800 is not None:
            pace_800 = t800 / 0.8
            t1500 = (pace_800 + 10) * 1.5
            return t1500 * 2 + 30

    return None


def top_n_average(seconds: list[float], n: int) -> float | None:
    if n <= 0 or len(seconds) < n:
        return None
    top = sorted(seconds)[:n]
    return sum(top) / n


def _values_for_gender(
    records: list[RecordRow],
    gender: str,
    value_fn: Callable[[list[RecordRow]], float | None],
) -> list[float]:
    by_name: dict[str, list[RecordRow]] = {}
    for row in records:
        if row.gender != gender:
            continue
        by_name.setdefault(row.name, []).append(row)

    values: list[float] = []
    for athlete_rows in by_name.values():
        value = value_fn(athlete_rows)
        if value is not None:
            values.append(value)
    return sorted(values)


def _build_gender_table(
    sections: list[AffiliationSection],
    gender: str,
    top_ns: tuple[int, ...],
    value_fn: Callable[[list[RecordRow]], float | None],
) -> GenderRankingTable:
    primary_n = top_ns[-1]
    entries: list[AffiliationRankingEntry] = []

    for section in sections:
        values = _values_for_gender(section.records, gender, value_fn)
        if len(values) < primary_n:
            continue
        averages = {n: top_n_average(values, n) for n in top_ns}
        sort_key = averages.get(primary_n)
        if sort_key is None:
            continue
        entries.append(
            AffiliationRankingEntry(
                affiliation=section.affiliation,
                athlete_count=len(values),
                averages=averages,
                sort_key=sort_key,
            )
        )

    ranked = sorted(
        entries,
        key=lambda entry: (entry.sort_key, entry.affiliation),
    )
    for idx, entry in enumerate(ranked, start=1):
        entry.rank = idx

    return GenderRankingTable(gender=gender, top_ns=top_ns, entries=ranked)


def _build_category_rankings(
    sections: list[AffiliationSection],
    spec: RankingCategorySpec,
) -> CategoryRankings:
    return CategoryRankings(
        spec=spec,
        boys=_build_gender_table(sections, "男子", BOYS_TOP_NS, spec.value_fn),
        girls=_build_gender_table(sections, "女子", GIRLS_TOP_NS, spec.value_fn),
    )


def _actual_distance_note(distance: str) -> str:
    return (
        f"各選手の {distance} SB（なければベストタイム）を所属内で集計し、"
        f"上位平均で順位付けしています。{TOP_N_NOTE}"
    )


RANKING_CATEGORY_SPECS: tuple[RankingCategorySpec, ...] = (
    RankingCategorySpec(
        key="800m",
        title="800m 実記録",
        note=_actual_distance_note("800m"),
        value_fn=lambda rows: best_seconds_at_distance(rows, "800m"),
    ),
    RankingCategorySpec(
        key="1500m",
        title="1500m 実記録",
        note=_actual_distance_note("1500m"),
        value_fn=lambda rows: best_seconds_at_distance(rows, "1500m"),
    ),
    RankingCategorySpec(
        key="3000m",
        title="3000m 実記録",
        note=_actual_distance_note("3000m"),
        value_fn=lambda rows: best_seconds_at_distance(rows, "3000m"),
    ),
    RankingCategorySpec(
        key="3000m-projected",
        title="3000m 予想タイム",
        note=(
            "各選手の 3000m SB → 1500m SB（+15秒/km換算）→ 800m SB（+10秒/km→1500m→3000m）"
            " の順で予想タイムを算出し、所属内の上位平均で順位付けしています。"
            f" {TOP_N_NOTE}"
        ),
        value_fn=project_3000m_seconds,
    ),
)


def compute_all_affiliation_rankings(
    sections: list[AffiliationSection],
) -> list[CategoryRankings]:
    return [_build_category_rankings(sections, spec) for spec in RANKING_CATEGORY_SPECS]


def compute_affiliation_rankings(
    sections: list[AffiliationSection],
) -> tuple[GenderRankingTable, GenderRankingTable]:
    """後方互換: 3000m 予想タイムランキングのみ返す。"""
    projected = next(
        category
        for category in compute_all_affiliation_rankings(sections)
        if category.spec.key == "3000m-projected"
    )
    return projected.boys, projected.girls
