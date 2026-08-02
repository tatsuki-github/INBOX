#!/usr/bin/env python3
"""朝練・夕練・練習休みスケジュールを events YAML に反映する。"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT / "input" / "events.2026.yaml"

PRACTICE_TAGS = ["ランニング", "いだてん岱明練習"]

SCHEDULES: dict[str, dict[str, dict]] = {
    "2026-07": {
        "2026-07-18": {"morning": None, "evening": None},
        "2026-07-19": {"morning": None, "evening": None},
        "2026-07-20": {"morning": "dot", "evening": "dot"},
        "2026-07-21": {"morning": "dot", "evening": "dot", "school": "三者面談（3年）"},
        "2026-07-22": {"morning": "dot", "evening": "timed", "school": "三者面談（3年）"},
        "2026-07-23": {"morning": "timed", "evening": "dot", "school": "三者面談（3年）"},
        "2026-07-24": {"morning": "timed", "evening": "timed", "school": ["三者面談（3年）", "学校保健講演会"]},
        "2026-07-25": {"morning": "dot", "evening": "dot"},
        "2026-07-26": {"morning": "dot", "evening": "dot"},
        "2026-07-27": {"morning": "timed", "evening": "timed", "school": "三者面談（3年）"},
        "2026-07-28": {"morning": "timed", "evening": "dot", "school": "三者面談（3年）"},
        "2026-07-29": {"morning": "dot", "evening": "timed"},
        "2026-07-30": {"morning": "dot", "evening": "dot"},
        "2026-07-31": {"morning": "timed", "evening": "dot"},
    },
    "2026-08": {
        "2026-08-01": {"morning": None, "evening": "timed"},
        "2026-08-02": {"morning": "dot", "evening": "dot"},
        "2026-08-03": {"morning": "timed", "evening": "timed"},
        "2026-08-04": {"morning": "timed", "evening": "dot"},
        "2026-08-05": {"morning": "dot", "evening": "timed"},
        "2026-08-06": {"morning": "timed", "evening": "dot"},
        "2026-08-07": {"morning": "timed", "evening": "timed"},
        "2026-08-08": {"morning": "dot", "evening": "timed"},
        "2026-08-09": {"morning": "dot", "evening": "dot"},
        "2026-08-10": {"morning": "timed", "evening": "timed", "school": "学校閉庁日"},
        "2026-08-11": {"morning": "dot", "evening": "dot"},
        "2026-08-12": {"morning": "dot", "evening": "timed", "school": "学校閉庁日"},
        "2026-08-13": {"morning": "dot", "evening": "dot", "school": "学校閉庁日"},
        "2026-08-14": {"morning": "dot", "evening": "timed", "school": "学校閉庁日"},
        "2026-08-15": {"morning": "dot", "evening": "timed"},
        "2026-08-16": {"morning": "dot", "evening": "dot"},
        "2026-08-17": {"morning": "timed", "evening": "timed"},
        "2026-08-18": {"morning": "dot", "evening": "dot", "school": "職員会議・校内研"},
        "2026-08-19": {"morning": "timed", "evening": "timed", "school": "2，3年課題提出日"},
        "2026-08-20": {"morning": "timed", "evening": None, "school": "1年課題提出日"},
        "2026-08-21": {"morning": "timed", "evening": "timed", "school": "1年課題提出日"},
        "2026-08-22": {"morning": "dot", "evening": "timed", "school": "玉名市人権教育研究大会"},
        "2026-08-23": {"morning": "dot", "evening": "dot"},
        "2026-08-24": {"morning": "timed", "evening": "timed"},
        "2026-08-25": {"morning": "timed", "evening": "dot"},
        "2026-08-26": {"morning": "dot", "evening": "timed", "school": "夏期休業最終日"},
    },
}

PRACTICE_TITLES = {
    "岱明朝練",
    "岱明夕練",
    "岱明朝練休み",
    "岱明夕練休み",
    "岱明練習休み",
    "岱明朝練と夕練",
}

EVENING_SKIP = {"2026-08-20", "2026-08-23"}


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


def build_practice(date: str, spec: dict) -> list[dict]:
    out: list[dict] = []
    for key, dot_t, time_t in [("morning", "岱明朝練休み", "岱明朝練"), ("evening", "岱明夕練休み", "岱明夕練")]:
        kind = spec.get(key)
        if kind is None or (key == "evening" and date in EVENING_SKIP):
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


def dump_event(ev: dict) -> str:
    lines = [f"- title: {ev['title']}"]
    for key in ["date", "end_date", "all_day", "category", "status", "start_time", "end_time", "location", "description", "tags", "urls"]:
        if key not in ev:
            continue
        val = ev[key]
        if key == "tags":
            lines.append("  tags:")
            for t in val:
                lines.append(f"  - {t}")
        elif key == "urls":
            lines.append("  urls:")
            for u in val:
                lines.append(f"  - {u}")
        elif key == "description":
            s = str(val)
            if "\n" in s:
                lines.append("  description: |")
                for row in s.splitlines():
                    lines.append(f"    {row}")
            elif ":" in s or s.startswith("'") or s.startswith('"'):
                lines.append(f"  description: '{s.replace(chr(39), chr(39)*2)}'")
            else:
                lines.append(f"  {key}: {s}")
        elif isinstance(val, bool):
            lines.append(f"  {key}: {'true' if val else 'false'}")
        elif key in {"date", "end_date", "start_time", "end_time"}:
            lines.append(f"  {key}: '{val}'")
        else:
            lines.append(f"  {key}: {val}")
    return "\n".join(lines)


def main() -> None:
    text = YAML_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    events: list[dict] = data["events"]

    schedule_dates = {d for s in SCHEDULES.values() for d in s}

    memos = [e for e in events if not e.get("date")]
    dated = [e for e in events if e.get("date")]

    # スケジュール対象日の練習系を除去
    dated = [e for e in dated if not (e.get("date") in schedule_dates and e.get("title") in PRACTICE_TITLES)]

    # 県中体連
    for e in dated:
        if e.get("title") == "令和８年度 熊本県中学校総合体育大会陸上競技大会":
            e["title"] = "県中体連"
            e["end_date"] = "2026-07-20"
            e["description"] = "令和８年度 熊本県中学校総合体育大会陸上競技大会"

    # 新規エントリ
    new_entries: list[dict] = []
    existing_keys = {(e.get("date"), e.get("title")) for e in dated}
    for sched in SCHEDULES.values():
        for date, spec in sched.items():
            new_entries.extend(build_practice(date, spec))
            school = spec.get("school")
            if not school:
                continue
            for title in school if isinstance(school, list) else [school]:
                if (date, title) not in existing_keys:
                    new_entries.append(school_event(title, date))
                    existing_keys.add((date, title))

    # 日付順にマージ（同日: 休み→練習→その他）
    from collections import defaultdict

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
    with YAML_PATH.open("w", encoding="utf-8") as f:
        f.write(header)
        yaml.dump(
            {"year": data["year"], "events": result},
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )
    print(f"Updated {YAML_PATH}: {count} events")


if __name__ == "__main__":
    main()
