"""Shared helpers for women's transcript generation."""

from __future__ import annotations

import json
from pathlib import Path

from lib.enrich import apply_board_ranks_from_computed
from lib.schema import normalize_leg
from lib.school_aliases import school_key

ROOT = Path(__file__).resolve().parent
TOP6 = json.loads((ROOT / "women_top6_2012_2025.json").read_text(encoding="utf-8"))


def leg(
    n: int,
    name,
    grade,
    split: str,
    cum: str,
    pr: int | None = None,
    sr: int | None = None,
    record: bool = False,
) -> dict:
    return normalize_leg(
        {
            "leg": n,
            "name": name,
            "grade": grade,
            "split": split,
            "cumulative": cum,
            "passing_rank": pr,
            "split_rank": sr,
            "split_record": True if record else None,
            "status": "ok",
            "raw_name_grade": f"{name} {grade}",
        }
    )


def team(rank: int, name: str, total: str, legs: list[dict]) -> dict:
    return {"rank": rank, "team": school_key(name), "total": total, "legs": legs}


def finalize_teams(teams: list[dict]) -> list[dict]:
    """Assign ranks from computed times and mark split_record legs."""
    ranked = apply_board_ranks_from_computed(teams, 5)
    fastest_split: dict[int, str] = {}
    for leg_no in range(1, 6):
        best = min(
            (
                (t["team"], L["split"])
                for t in ranked
                for L in t["legs"]
                if L["leg"] == leg_no and L.get("split")
            ),
            key=lambda x: _tsec(x[1]),
        )
        fastest_split[leg_no] = best[0]
    for t in ranked:
        for L in t["legs"]:
            if fastest_split.get(L["leg"]) == t["team"]:
                L["split_record"] = True
    return ranked


def _tsec(value: str) -> int:
    m, s = value.split(":")
    return int(m) * 60 + int(s)


def merge_top6(year: int, board_teams: list[dict]) -> list[dict]:
    anchor_by_team = {
        school_key(t["team"]): t for t in TOP6["years"][str(year)]["teams"]
    }
    out: list[dict] = []
    for bt in board_teams:
        key = school_key(bt["team"])
        if key in anchor_by_team:
            at = anchor_by_team[key]
            assert bt["total"] == at["total"], (year, bt["team"], bt["total"], at["total"])
            board_by_leg = {L["leg"]: L for L in bt["legs"]}
            merged = []
            for al in at["legs"]:
                bl = board_by_leg[al["leg"]]
                merged.append(
                    leg(
                        al["leg"],
                        al["name"],
                        al["grade"],
                        al["split"],
                        al["cumulative"],
                        bl.get("passing_rank"),
                        bl.get("split_rank"),
                        record=bool(bl.get("split_record")),
                    )
                )
            out.append(team(bt["rank"], at["team"], at["total"], merged))
        else:
            out.append(bt)
    return out
