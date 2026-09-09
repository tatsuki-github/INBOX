"""所属別 3000m 予想タイムランキングの算出。"""

from __future__ import annotations

from dataclasses import dataclass, field

from arato_tamana_records import AffiliationSection, RecordRow

BOYS_TOP_NS = (4, 5, 6)
GIRLS_TOP_NS = (3, 4, 5)
RANKING_GENDERS = ("男子", "女子")


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
    if not seconds or n <= 0:
        return None
    top = sorted(seconds)[:n]
    return sum(top) / len(top)


def _projections_for_gender(records: list[RecordRow], gender: str) -> list[float]:
    by_name: dict[str, list[RecordRow]] = {}
    for row in records:
        if row.gender != gender:
            continue
        by_name.setdefault(row.name, []).append(row)

    projections: list[float] = []
    for athlete_rows in by_name.values():
        projected = project_3000m_seconds(athlete_rows)
        if projected is not None:
            projections.append(projected)
    return sorted(projections)


def _build_gender_table(
    sections: list[AffiliationSection],
    gender: str,
    top_ns: tuple[int, ...],
) -> GenderRankingTable:
    primary_n = top_ns[-1]
    entries: list[AffiliationRankingEntry] = []

    for section in sections:
        projections = _projections_for_gender(section.records, gender)
        averages = {n: top_n_average(projections, n) for n in top_ns}
        entries.append(
            AffiliationRankingEntry(
                affiliation=section.affiliation,
                athlete_count=len(projections),
                averages=averages,
                sort_key=averages.get(primary_n),
            )
        )

    ranked = sorted(
        entries,
        key=lambda entry: (entry.sort_key is None, entry.sort_key or 999999.0, entry.affiliation),
    )
    for idx, entry in enumerate(ranked, start=1):
        entry.rank = idx

    return GenderRankingTable(gender=gender, top_ns=top_ns, entries=ranked)


def compute_affiliation_rankings(
    sections: list[AffiliationSection],
) -> tuple[GenderRankingTable, GenderRankingTable]:
    boys = _build_gender_table(sections, "男子", BOYS_TOP_NS)
    girls = _build_gender_table(sections, "女子", GIRLS_TOP_NS)
    return boys, girls
