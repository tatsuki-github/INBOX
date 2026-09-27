#!/usr/bin/env python3
"""Build searchable athlete and team profile JSON from repository snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROSTER_PATH = ROOT / "input/external/notion/databases/いだてん岱明生徒/rows.json"
RECORDS_PATH = ROOT / "out/analysis/notion_records_2026.json"
TEAM_RECORDS_PATH = ROOT / "out/analysis/arato-tamana-teams/岱明中.md"
OUTPUT_PATH = ROOT / "input/athlete-team-profiles.json"

TEAM_ID = "daiming-jhs-athletics"
def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_profiles() -> dict[str, Any]:
    roster = _read_json(ROSTER_PATH)
    records = _read_json(RECORDS_PATH)
    if not isinstance(roster, list) or not isinstance(records, list):
        raise ValueError("Roster and records snapshots must be JSON arrays")

    athletes: list[dict[str, Any]] = []
    by_name: dict[str, dict[str, Any]] = {}
    for row in roster:
        if not isinstance(row, dict):
            continue
        name = str(row.get("名前") or "").strip()
        notion_id = str(row.get("id") or "").strip()
        if not name or not notion_id:
            continue
        athlete = {
            "id": f"notion:{notion_id}",
            "name": name,
            "team_id": TEAM_ID,
            "grade": row.get("学年"),
            "season": 2026,
            "profile_source": "input/external/notion/databases/いだてん岱明生徒/rows.json",
            "records": [],
        }
        athletes.append(athlete)
        by_name[name] = athlete

    for row in records:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        affiliation = str(row.get("affiliation") or "").strip()
        athlete = by_name.get(name)
        if (
            athlete is None
            or affiliation not in {"岱明", "岱明中"}
            or row.get("grade") != athlete.get("grade")
        ):
            continue
        athlete["records"].append(
            {
                "season": 2026,
                "event_date": row.get("date"),
                "discipline": row.get("distance"),
                "result": row.get("time_text"),
                "result_url": row.get("url"),
                "record_source": "out/analysis/notion_records_2026.json",
            }
        )

    # Add earlier records only when school, exact name, and grade progression agree.
    year: int | None = None
    discipline: str | None = None
    for line in TEAM_RECORDS_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("## ") and line.endswith("年度"):
            try:
                year = int(line[3:-2])
            except ValueError:
                year = None
            continue
        if line.startswith("### ") and line.endswith("m"):
            discipline = line[4:]
            continue
        if year is None or discipline is None or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6 or cells[0] not in {"男子", "女子"}:
            continue
        try:
            record_grade = int(cells[1])
        except ValueError:
            continue
        athlete = by_name.get(cells[2])
        if not athlete or athlete.get("grade") != record_grade + (2026 - year):
            continue
        athlete["records"].append(
            {
                "season": year,
                "event_date": cells[4],
                "discipline": discipline,
                "result": cells[3],
                "result_url": cells[5],
                "record_source": "out/analysis/arato-tamana-teams/岱明中.md",
            }
        )

    for athlete in athletes:
        unique_records = {}
        for record in athlete["records"]:
            key = tuple(record.get(field) for field in ("season", "discipline", "event_date", "result", "result_url"))
            unique_records[key] = record
        athlete["records"] = list(unique_records.values())
        athlete["records"].sort(
            key=lambda r: (str(r.get("event_date") or ""), str(r.get("discipline") or ""), str(r.get("result") or ""))
        )

    team = {
        "id": TEAM_ID,
        "name": "岱明中学校陸上競技部",
        "aliases": ["岱明", "岱明中", "いだてん岱明"],
        "season": 2026,
        "overview": "岱明中学校の陸上競技部。選手プロフィールは2026年度のNotion生徒DB、競技記録は同年度の中学生記録スナップショットに基づく。",
        "members": [athlete["id"] for athlete in athletes],
        "record_count": sum(len(athlete["records"]) for athlete in athletes),
        "profile_source": "input/external/notion/databases/いだてん岱明生徒/rows.json",
        "record_source": "out/analysis/notion_records_2026.json",
        "team_record_sources": [
            "out/analysis/arato-tamana-teams/岱明中.md",
            "out/analysis/aragyoku-teams/岱明.md",
        ],
    }
    return {
        "schema_version": 1,
        "generated_from": [
            "input/external/notion/databases/いだてん岱明生徒/rows.json",
            "out/analysis/notion_records_2026.json",
            "out/analysis/arato-tamana-teams/岱明中.md",
        ],
        "teams": [team],
        "athletes": athletes,
    }


def main() -> int:
    missing = [path for path in (ROSTER_PATH, RECORDS_PATH, TEAM_RECORDS_PATH) if not path.is_file()]
    if missing:
        raise SystemExit("Missing input: " + ", ".join(str(p.relative_to(ROOT)) for p in missing))
    data = build_profiles()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {OUTPUT_PATH.relative_to(ROOT)}: "
        f"{len(data['athletes'])} athletes, {data['teams'][0]['record_count']} linked records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
