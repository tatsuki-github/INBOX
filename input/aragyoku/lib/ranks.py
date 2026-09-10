"""Rank computation and cross-check for ekiden transcripts."""

from __future__ import annotations

def parse_time_to_seconds(value: str | None) -> int | None:
    if not value:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"dnf", "dns", "-"}:
        return None
    parts = text.split(":")
    try:
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = int(parts[1])
        elif len(parts) == 3:
            minutes = int(parts[0]) * 60 + int(parts[1])
            seconds = int(parts[2])
        else:
            return None
    except ValueError:
        return None
    if seconds >= 60 or minutes < 0:
        return None
    return minutes * 60 + seconds


def _rank_by_values(
    entries: list[tuple[str, int | None]],
    *,
    ascending: bool = True,
) -> dict[str, int]:
    """Assign competition ranks (1,2,2,4 style) by time."""
    valid = [(key, val) for key, val in entries if val is not None]
    if not valid:
        return {}
    ordered = sorted(valid, key=lambda item: item[1], reverse=not ascending)
    ranks: dict[str, int] = {}
    current_rank = 1
    i = 0
    while i < len(ordered):
        val = ordered[i][1]
        tied = [ordered[j] for j in range(i, len(ordered)) if ordered[j][1] == val]
        for key, _ in tied:
            ranks[key] = current_rank
        current_rank += len(tied)
        i += len(tied)
    return ranks


def compute_split_ranks(teams: list[dict], leg: int) -> dict[str, int]:
    entries: list[tuple[str, int | None]] = []
    for team in teams:
        key = f"{team['rank']}:{team['team']}"
        leg_row = next(L for L in team["legs"] if L["leg"] == leg)
        entries.append((key, parse_time_to_seconds(leg_row.get("split"))))
    return _rank_by_values(entries, ascending=True)


def compute_passing_ranks(teams: list[dict], leg: int) -> dict[str, int]:
    entries: list[tuple[str, int | None]] = []
    for team in teams:
        key = f"{team['rank']}:{team['team']}"
        leg_row = next(L for L in team["legs"] if L["leg"] == leg)
        entries.append((key, parse_time_to_seconds(leg_row.get("cumulative"))))
    return _rank_by_values(entries, ascending=True)


def attach_computed_ranks(teams: list[dict], leg_count: int) -> list[dict]:
    """Return teams with computed.split_rank and computed.passing_rank on each leg."""
    split_maps = {leg: compute_split_ranks(teams, leg) for leg in range(1, leg_count + 1)}
    pass_maps = {leg: compute_passing_ranks(teams, leg) for leg in range(1, leg_count + 1)}
    out: list[dict] = []
    for team in teams:
        key = f"{team['rank']}:{team['team']}"
        new_legs = []
        for leg_row in team["legs"]:
            leg = leg_row["leg"]
            enriched = dict(leg_row)
            enriched["computed"] = {
                "split_rank": split_maps[leg].get(key),
                "passing_rank": pass_maps[leg].get(key),
            }
            new_legs.append(enriched)
        out.append({**team, "legs": new_legs})
    return out


def rank_mismatches(teams: list[dict], leg_count: int) -> list[str]:
    """Compare board ranks to computed ranks; return human-readable mismatch notes."""
    enriched = attach_computed_ranks(teams, leg_count)
    notes: list[str] = []
    for team in enriched:
        for leg_row in team["legs"]:
            comp = leg_row.get("computed") or {}
            leg = leg_row["leg"]
            prefix = f"{team['team']} leg{leg}"
            board_split = leg_row.get("split_rank")
            calc_split = comp.get("split_rank")
            if board_split is not None and calc_split is not None and board_split != calc_split:
                notes.append(f"{prefix}: split_rank board={board_split} computed={calc_split}")
            board_pass = leg_row.get("passing_rank")
            calc_pass = comp.get("passing_rank")
            if board_pass is not None and calc_pass is not None and board_pass != calc_pass:
                notes.append(f"{prefix}: passing_rank board={board_pass} computed={calc_pass}")
    return notes
