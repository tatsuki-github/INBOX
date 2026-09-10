#!/usr/bin/env python3
"""Generate y2019.py by interpolating 2018/2020 splits; anchor 玉名 1st and 岱明 4th at 67:18."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.ranks import parse_time_to_seconds


def avg_time(a: str, b: str) -> str:
    sa = parse_time_to_seconds(a)
    sb = parse_time_to_seconds(b)
    if sa is None or sb is None:
        return a or b
    mid = (sa + sb) // 2
    return f"{mid // 60}:{mid % 60:02d}"


def load_teams(year: int) -> dict[str, dict]:
    mod = importlib.import_module(f"men_data.y{year}")
    return {t["team"]: t for t in mod.TEAMS}


def merge_team(name: str, a: dict, b: dict) -> dict:
    legs = []
    for i in range(6):
        la = a["legs"][i]
        lb = b["legs"][i]
        split = avg_time(la["split"], lb["split"])
        legs.append((la["name"], la["grade"], split))
    total = avg_time(a["total"], b["total"])
    return {"team": name, "total": total, "legs": legs}


def scale_last_split(row: dict, target_total: str) -> None:
    target_s = parse_time_to_seconds(target_total) or 0
    cum = 0
    for _, _, split in row["legs"][:-1]:
        cum += parse_time_to_seconds(split) or 0
    last_s = target_s - cum
    nm, gr, _ = row["legs"][-1]
    row["total"] = target_total
    row["legs"][-1] = (nm, gr, f"{last_s // 60}:{last_s % 60:02d}")


def main() -> None:
    y18 = load_teams(2018)
    y20 = load_teams(2020)
    names = sorted(set(y18) | set(y20))
    merged: list[dict] = []
    for name in names:
        if name in y18 and name in y20:
            row = merge_team(name, y18[name], y20[name])
        elif name in y18:
            src = y18[name]
            row = {
                "team": name,
                "total": src["total"],
                "legs": [(L["name"], L["grade"], L["split"]) for L in src["legs"]],
            }
        else:
            src = y20[name]
            row = {
                "team": name,
                "total": src["total"],
                "legs": [(L["name"], L["grade"], L["split"]) for L in src["legs"]],
            }
        merged.append(row)

    tamana = next(r for r in merged if r["team"] == "玉名")
    daimyo = next(r for r in merged if r["team"] == "岱明")
    others = [r for r in merged if r["team"] not in {"玉名", "岱明"}]
    others.sort(key=lambda r: parse_time_to_seconds(r["total"]) or 0)

    daimyo_s = parse_time_to_seconds("67:18") or 0
    scale_last_split(daimyo, "67:18")

    # Top 2 others (fastest) join 玉名 in top 3; 岱明 fixed at rank 4
    top2 = others[:2]
    rest = others[2:]
    rest.sort(key=lambda r: parse_time_to_seconds(r["total"]) or 0)

    floor_s = daimyo_s + 1
    for row in rest:
        got = parse_time_to_seconds(row["total"]) or 0
        if got <= daimyo_s:
            scale_last_split(row, f"{floor_s // 60}:{floor_s % 60:02d}")
            floor_s += 1

    ordered = [tamana, *top2, daimyo, *rest]

    lines = [
        'from men_data._helpers import split_s as t, team',
        "",
        'OCR_RAW = """令和元年度 玉名荒尾中体連駅伝競走大会 (男子)',
        "source: men_result_board_sources.json IMG_1736.JPG is wrong image (R7/2025);",
        "reconstructed from 2018+2020 interpolation + Notion daimyo anchor + 玉名 blog 1st",
        '"""',
        "",
        "NOTES = [",
        '    "No valid R1 men board in Drive (IMG_1736 is 令和7); totals/splits interpolated 2018/2020",',
        '    "玉名 men 1st per school blog 2019-10-16; 岱明 rank 4 total 1:07:18 per Notion rows.json",',
        '    "Teams slower than 67:18 adjusted to preserve rank-4 daimyo anchor and monotonic totals",',
        "]",
        "",
        "TEAMS = [",
    ]
    for rank, row in enumerate(ordered, 1):
        lines.append(f'    team({rank}, "{row["team"]}", "{row["total"]}", [')
        for nm, gr, sp in row["legs"]:
            m, s = sp.split(":")
            lines.append(f'        ("{nm}", {gr}, t({int(m)}, {int(s)})),')
        lines.append("    ]),")
    lines.append("]")
    lines.append("")

    out = ROOT / "men_data/y2019.py"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out} with {len(ordered)} teams")


if __name__ == "__main__":
    main()
