"""Helpers for compact men's transcript data authoring."""

from __future__ import annotations


def split_s(m: int, s: int) -> str:
    return f"{m}:{s:02d}"


def add_split(cum_s: int, split: str) -> tuple[str, int]:
    m, sec = split.split(":")
    split_s = int(m) * 60 + int(sec)
    return split, cum_s + split_s


def legs_from_splits(rows: list[tuple]) -> list[dict]:
    """Each row: (name, grade, split). Cumulative and ranks are derived later."""
    out: list[dict] = []
    cum_s = 0
    for i, row in enumerate(rows, 1):
        name, grade, split = row
        split, cum_s = add_split(cum_s, split)
        cum = f"{cum_s // 60}:{cum_s % 60:02d}"
        out.append(
            {
                "leg": i,
                "name": name,
                "grade": grade,
                "split": split,
                "cumulative": cum,
                "raw_name_grade": f"{name}({grade})",
            }
        )
    return out


def team(rank: int, school: str, total: str, rows: list[tuple]) -> dict:
    legs = legs_from_splits(rows)
    computed_total = legs[-1]["cumulative"]
    return {"rank": rank, "team": school, "total": computed_total, "legs": legs}
