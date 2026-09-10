"""Enrich team leg records with computed ranks and optional board ranks."""

from __future__ import annotations

from .ranks import attach_computed_ranks
from .schema import normalize_leg, normalize_team


def enrich_teams(teams: list[dict], leg_count: int) -> list[dict]:
    """Attach computed ranks; normalize leg optional fields."""
    normalized = [normalize_team(t) for t in teams]
    return attach_computed_ranks(normalized, leg_count)


def apply_board_ranks_from_computed(teams: list[dict], leg_count: int) -> list[dict]:
    """Fill null passing_rank/split_rank from computed values (OCR fallback)."""
    enriched = enrich_teams(teams, leg_count)
    out: list[dict] = []
    for team in enriched:
        legs = []
        for leg_row in team["legs"]:
            comp = leg_row.pop("computed", {})
            row = dict(leg_row)
            if row.get("passing_rank") is None and comp.get("passing_rank") is not None:
                row["passing_rank"] = comp["passing_rank"]
            if row.get("split_rank") is None and comp.get("split_rank") is not None:
                row["split_rank"] = comp["split_rank"]
            legs.append(row)
        out.append({**team, "legs": legs})
    return out
