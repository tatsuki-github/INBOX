"""Schema constants and helpers for Aragyoku full ekiden transcripts."""

from __future__ import annotations

WOMEN_LEG_COUNT = 5
MEN_LEG_COUNT = 6

WOMEN_LEG_DISTANCES = [
    {"leg": 1, "distance_km": 3.0},
    {"leg": 2, "distance_km": 1.855},
    {"leg": 3, "distance_km": 2.0},
    {"leg": 4, "distance_km": 2.0},
    {"leg": 5, "distance_km": 3.0},
]

# Standard men's course (6 legs); per-year overrides allowed in transcript meta.
MEN_LEG_DISTANCES = [
    {"leg": 1, "distance_km": 3.0},
    {"leg": 2, "distance_km": 2.0},
    {"leg": 3, "distance_km": 2.0},
    {"leg": 4, "distance_km": 2.0},
    {"leg": 5, "distance_km": 2.0},
    {"leg": 6, "distance_km": 3.0},
]

ATHLETE_CSV_COLUMNS = [
    "year",
    "gender",
    "rank",
    "team",
    "total",
    "leg",
    "name",
    "grade",
    "split",
    "cumulative",
    "passing_rank",
    "split_rank",
    "split_record",
    "status",
    "source_drive_id",
]

LEG_OPTIONAL_FIELDS = (
    "passing_rank",
    "split_rank",
    "split_record",
    "status",
    "raw_name_grade",
    "notes",
)

TEAM_OPTIONAL_FIELDS = ("gap_to_leader", "gap_to_prev")


def leg_count_for_gender(gender: str) -> int:
    if gender == "女子":
        return WOMEN_LEG_COUNT
    if gender == "男子":
        return MEN_LEG_COUNT
    raise ValueError(f"unknown gender: {gender}")


def default_legs_for_gender(gender: str) -> list[dict]:
    if gender == "女子":
        return list(WOMEN_LEG_DISTANCES)
    if gender == "男子":
        return list(MEN_LEG_DISTANCES)
    raise ValueError(f"unknown gender: {gender}")


def normalize_leg(leg_data: dict) -> dict:
    """Ensure all optional leg fields exist (null when absent)."""
    out = {
        "leg": leg_data["leg"],
        "name": leg_data.get("name"),
        "grade": leg_data.get("grade"),
        "split": leg_data.get("split"),
        "cumulative": leg_data.get("cumulative"),
        "passing_rank": leg_data.get("passing_rank"),
        "split_rank": leg_data.get("split_rank"),
        "split_record": leg_data.get("split_record"),
        "status": leg_data.get("status", "ok"),
        "raw_name_grade": leg_data.get("raw_name_grade"),
    }
    if leg_data.get("notes"):
        out["notes"] = leg_data["notes"]
    return out


def normalize_team(team_data: dict) -> dict:
    out = {
        "rank": team_data["rank"],
        "team": team_data["team"],
        "total": team_data["total"],
        "legs": [normalize_leg(L) for L in team_data["legs"]],
    }
    for field in TEAM_OPTIONAL_FIELDS:
        if field in team_data:
            out[field] = team_data[field]
    return out
