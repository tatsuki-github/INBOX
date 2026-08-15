#!/usr/bin/env python3
"""朝練・夕練・練習休みスケジュールを events YAML に反映する。"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT / "input" / "events.2026.yaml"
SCHEDULES_PATH = ROOT / "input" / "practice_schedules.yaml"
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from yaml_io import dump_event

PRACTICE_TAGS = ["ランニング", "いだてん岱明練習"]

PRACTICE_TITLES = {
    "岱明朝練",
    "岱明夕練",
    "岱明朝練休み",
    "岱明夕練休み",
    "岱明練習休み",
    "岱明朝練と夕練",
}


def load_schedules() -> tuple[dict[str, dict[str, dict]], set[str]]:
    with SCHEDULES_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    schedules = data.get("schedules") or {}
    evening_skip = set(data.get("evening_skip_dates") or [])
    return schedules, evening_skip


def practice_event(title: str, date: str, kind: str) -> dict:
    ev: dict = {
        "title": title,
        "date": date,
        "category": "予定",
        "status": "scheduled",
        "tags": list(PRACTICE_TAGS),
    }
    if kind == "dot":
        ev["all_day"] = True
    else:
        ev["all_day"] = False
        if "朝" in title:
            ev["start_time"] = "08:00"
            ev["end_time"] = "09:30"
        else:
            ev["start_time"] = "18:00"
            ev["end_time"] = "19:30"
    return ev


def school_event(title: str, date: str) -> dict:
    return {"title": title, "date": date, "all_day": True, "category": "予定", "status": "scheduled"}


def build_practice(date: str, spec: dict, evening_skip: set[str]) -> list[dict]:
    out: list[dict] = []
    for key, dot_t, time_t in [("morning", "岱明朝練休み", "岱明朝練"), ("evening", "岱明夕練休み", "岱明夕練")]:
        kind = spec.get(key)
        if kind is None or (key == "evening" and date in evening_skip):
            continue
        out.append(practice_event(dot_t if kind == "dot" else time_t, date, kind))
    return out


def event_rank(ev: dict) -> tuple:
    title = ev.get("title", "")
    if "朝練休み" in title:
        p = 0
    elif "夕練休み" in title:
        p = 1
    elif title in {"岱明朝練", "岱明夕練"}:
        p = 2
    elif title in PRACTICE_TITLES:
        p = 3
    else:
        p = 4
    st = str(ev.get("start_time") or "99:99")
    return (p, st, title)


def main() -> None:
    schedules, evening_skip = load_schedules()
    text = YAML_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    events: list[dict] = data["events"]

    schedule_dates = {d for s in schedules.values() for d in s}

    memos = [e for e in events if not e.get("date")]
    dated = [e for e in events if e.get("date")]

    dated = [e for e in dated if not (e.get("date") in schedule_dates and e.get("title") in PRACTICE_TITLES)]

    for e in dated:
        if e.get("title") == "令和８年度 熊本県中学校総合体育大会陸上競技大会":
            e["title"] = "県中体連"
            e["end_date"] = "2026-07-20"
            e["description"] = "令和８年度 熊本県中学校総合体育大会陸上競技大会"

    new_entries: list[dict] = []
    existing_keys = {(e.get("date"), e.get("title")) for e in dated}
    for sched in schedules.values():
        for date, spec in sched.items():
            new_entries.extend(build_practice(date, spec, evening_skip))
            school = spec.get("school")
            if not school:
                continue
            for title in school if isinstance(school, list) else [school]:
                if (date, title) not in existing_keys:
                    new_entries.append(school_event(title, date))
                    existing_keys.add((date, title))

    by_date: dict[str, list[dict]] = defaultdict(list)
    for e in dated + new_entries:
        by_date[e["date"]].append(e)

    merged_dated: list[dict] = []
    for date in sorted(by_date.keys()):
        merged_dated.extend(sorted(by_date[date], key=event_rank))

    result = merged_dated + memos
    count = len(result)

    header_match = re.match(r"((?:#.*\n)*)", text)
    header = header_match.group(1) if header_match else ""
    header = re.sub(r"^# 件数: \d+", f"# 件数: {count}", header, count=1, flags=re.MULTILINE)
    body = ["events:"]
    body.extend(dump_event(ev) for ev in result)
    YAML_PATH.write_text(header + "year: " + str(data["year"]) + "\n" + "\n".join(body) + "\n", encoding="utf-8")
    print(f"Updated {YAML_PATH}: {count} events")


if __name__ == "__main__":
    main()
