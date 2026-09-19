#!/usr/bin/env python3
"""Normalize board-header 大会/区間記録 and inject into all year transcripts.

Source: meet_records/_extracted_raw.json (from overall-results board photos).
Writes:
  - meet_records/canonical.json
  - transcripts/{year}-{gender}.json  (+ meet_records field)
  - idaten-corpus copy of transcripts when present
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARAGYOKU = ROOT / "input/aragyoku"
RAW = ARAGYOKU / "meet_records/_extracted_raw.json"
CANONICAL = ARAGYOKU / "meet_records/canonical.json"
TRANSCRIPTS = ARAGYOKU / "transcripts"
CORPUS_TRANSCRIPTS = ROOT / "input/idaten-corpus/aragyoku/transcripts"


def era_to_western(label: str) -> int | None:
    m = re.fullmatch(r"H(\d+)", label)
    if m:
        return 1988 + int(m.group(1))
    m = re.fullmatch(r"R(\d+)", label)
    if m:
        return 2018 + int(m.group(1))
    return None


def as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_leg(leg: dict) -> dict:
    names = as_list(leg.get("name"))
    schools = as_list(leg.get("school"))
    year_labels = as_list(leg.get("year_labels"))
    # Pair holders; if multiple names share year_labels, attach all labels to each
    holders: list[dict] = []
    n = max(len(names), len(schools), 1 if year_labels else 0)
    for i in range(max(len(names), len(schools))):
        name = names[i] if i < len(names) else (names[-1] if names else None)
        school = schools[i] if i < len(schools) else (schools[-1] if schools else None)
        # Prefer pairing year_labels 1:1 with holders when lengths match
        if len(year_labels) == len(names) and names:
            yl = [year_labels[i]]
        else:
            yl = list(year_labels)
        holders.append(
            {
                "name": name,
                "school": school,
                "year_labels": yl,
                "western_years": [y for y in (era_to_western(x) for x in yl) if y is not None],
            }
        )
    out = {
        "leg": int(leg["leg"]),
        "distance_km": leg.get("distance_km"),
        "time": leg["time"],
        "holders": holders,
    }
    if leg.get("alt_holders"):
        out["alt_holders"] = leg["alt_holders"]
    return out


def normalize_total(total: dict | None) -> dict | None:
    if not total:
        return None
    yl = as_list(total.get("year_labels"))
    return {
        "time": total.get("time"),
        "year_labels": yl,
        "western_years": [y for y in (era_to_western(x) for x in yl) if y is not None],
        "school": total.get("school"),
        "name": total.get("name"),
    }


def course_era(year: int, gender: str) -> str:
    if gender == "女子":
        return "women_standard"
    if year <= 2023:
        return "men_pre2024"
    return "men_2024plus"


def normalize_entry(key: str, raw: dict) -> dict:
    year_s, gender = key.split("-", 1)
    year = int(year_s)
    return {
        "year": year,
        "gender": gender,
        "course_era": course_era(year, gender),
        "total": normalize_total(raw.get("total")),
        "legs": [normalize_leg(L) for L in raw.get("legs") or []],
        "source_image": raw.get("source_image"),
        "notes": list(raw.get("notes") or []),
    }


def inject(transcript: dict, meet: dict) -> dict:
    out = deepcopy(transcript)
    out["meet_records"] = {
        "total": meet["total"],
        "legs": meet["legs"],
        "course_era": meet["course_era"],
        "source_image": meet.get("source_image"),
        "notes": meet.get("notes") or [],
    }
    return out


def main() -> int:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    canonical: dict[str, dict] = {}
    for key, entry in sorted(raw.items()):
        canonical[key] = normalize_entry(key, entry)

    CANONICAL.parent.mkdir(parents=True, exist_ok=True)
    CANONICAL.write_text(
        json.dumps(canonical, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    updated = 0
    missing = []
    for key, meet in canonical.items():
        path = TRANSCRIPTS / f"{key}.json"
        if not path.exists():
            missing.append(key)
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        data = inject(data, meet)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        corpus = CORPUS_TRANSCRIPTS / f"{key}.json"
        if corpus.parent.exists():
            corpus.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        updated += 1

    print(f"wrote {CANONICAL} ({len(canonical)} years)")
    print(f"updated transcripts: {updated}")
    if missing:
        print("missing transcripts:", ", ".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
