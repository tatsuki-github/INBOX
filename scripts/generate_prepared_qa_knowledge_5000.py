#!/usr/bin/env python3
"""Add ~5000 high-quality prepared FAQ entries for remaining knowledge gaps (ADR 059).

Focus (natural user questions, concrete answers, meet links when available):
  - athlete × meet race results (荒玉地区, 2024–2026)
  - aragyoku team orders / leg awards / runner careers
  - remaining calendar, practice sessions, course points, media boards
  - leftover legs / SB gaps

Usage:
  python3 scripts/generate_prepared_qa_knowledge_5000.py
  python3 scripts/generate_prepared_qa_knowledge_5000.py --dry-run
  python3 scripts/generate_prepared_qa_knowledge_5000.py --target 5000
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import (  # noqa: E402
    EVENTS_2025,
    EVENTS_2026,
    MEN_FULL,
    WOMEN_FULL,
    drive_url_for_calendar,
    entry,
    friendly_calendar_answer,
    load_drive_meet_folder_map,
    load_years,
    slug,
)
from generate_prepared_qa_knowledge_1000 import load_keywords, take  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
BY_YEAR_CSV = (
    ROOT
    / "input"
    / "external"
    / "drive"
    / "personal"
    / "t-tsuchiyama"
    / "sb"
    / "by-year"
)
BY_YEAR_SB = ROOT / "input" / "external" / "sb" / "middle-school" / "by-year"
EVENTS_2024 = ROOT / "input" / "events.2024.yaml"
DEFAULT_YEAR = 2026
YEARS_RACE = (2024, 2025, 2026)


def _truthy_sb(val: object) -> bool:
    s = str(val or "").strip().upper()
    return s in {"TRUE", "__YES__", "YES", "1", "○", "採用"}


def meet_url(r: dict) -> str:
    for key in ("参考", "url", "URL"):
        u = str(r.get(key) or "").strip()
        if u.startswith("http") and "notion.com" not in u and "notion.so" not in u:
            return u
    return ""


def short_meet(meet: str) -> str:
    """Human-friendly meet alias for questions (keep answer with full name)."""
    m = re.sub(r"\s+", " ", (meet or "").strip())
    m = re.sub(r"^\d{4}[./]\d{1,2}[./]\d{1,2}\s*", "", m)
    m = re.sub(r"^令和\d+年度\s*", "", m)
    m = re.sub(r"^第\d+回\s*", "", m)
    # common shortenings
    if "通信" in m:
        return "通信陸上"
    if "総合体育" in m or "中体連" in m:
        return "中体連"
    if "中学校陸上競技選手権" in m or "県中学" in m:
        return "県中学選手権"
    if "長距離記録会" in m:
        n = re.search(r"第([１２3-9一二三四五六七八九十\d]+)回", meet)
        if n:
            return f"第{n.group(1)}回長距離記録会"
        return "長距離記録会"
    if "ナイター" in m:
        return "玉名郡ナイター"
    if "なごみ" in m or "金栗四三" in m:
        return "なごみ大会"
    if "ジュニア" in m:
        return "ジュニア駅伝"
    if len(m) > 22:
        m = m[:21] + "…"
    return m or "大会"


def load_race_rows(year: int) -> list[dict[str, str]]:
    path = BY_YEAR_CSV / f"{year}-single-table.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def gen_athlete_meet(existing_ids: set[str], limit: int) -> list[dict]:
    """One entry per athlete × meet × year (natural 'あの大会の記録は？')."""
    keywords = load_keywords()
    out: list[dict] = []
    for year in YEARS_RACE:
        # group (name, short_meet) -> rows (may merge similar full names)
        groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        meta: dict[tuple[str, str], dict] = {}
        for r in load_race_rows(year):
            aff = (r.get("所属") or "").strip()
            name = (r.get("名前") or "").strip()
            meet = (r.get("大会名") or "").strip()
            dist = (r.get("距離") or "").strip()
            mark = (r.get("記録") or "").strip()
            if not name or not meet or not dist or not mark:
                continue
            if not any(k in aff for k in keywords):
                continue
            sm = short_meet(meet)
            key = (name, sm)
            groups[key].append(r)
            if key not in meta:
                meta[key] = {
                    "aff": aff,
                    "gender": (r.get("性別") or "").strip(),
                    "meet_full": meet,
                }
        for (name, sm), rows in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
            eid = f"race-{year}-{slug(name)}-{slug(sm)}"
            if eid in existing_ids or any(e["id"] == eid for e in out):
                continue
            # quality: prefer groups with at least one public result URL
            urls = [meet_url(r) for r in rows]
            if not any(urls) and year >= 2025:
                # still allow if SB or clear mark; skip empty-link noise for recent years
                # when meet looks like internal scrap
                if not any(_truthy_sb(r.get("SB採用")) for r in rows):
                    pass  # keep — many older rows still valuable
            info = meta[(name, sm)]
            lines = []
            for r in sorted(rows, key=lambda x: (x.get("日付") or "", x.get("距離") or "")):
                date = (r.get("日付") or "").strip()
                dist = (r.get("距離") or "").strip()
                mark = (r.get("記録") or "").strip()
                bit = f"{date} {dist} {mark}"
                if _truthy_sb(r.get("SB採用")):
                    bit += "【SB】"
                u = meet_url(r)
                if u:
                    bit += f" 大会結果: {u}"
                lines.append(bit)
            if not lines:
                continue
            who = f"{name}（{info['aff']}" + (
                f"/{info['gender']}" if info["gender"] else ""
            ) + "）"
            qs = [
                f"{name}の{sm}の記録は？",
                f"{year}年{name}の{sm}の結果",
                f"{name}は{sm}で何分？",
                f"{name}の{sm}タイム",
            ]
            if year != DEFAULT_YEAR:
                qs = [q if str(year) in q else f"{year}年{q}" for q in qs]
            if year == DEFAULT_YEAR:
                qs.extend(
                    [
                        f"{name}の今年の{sm}の記録",
                        f"今年度{name}の{sm}",
                    ]
                )
            ans = (
                f"{who}の{year}年度・{sm}の記録は{len(lines)}件です"
                f"（大会名: {info['meet_full']}）。\n" + "\n".join(lines)
            )
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [f"input/external/drive/personal/t-tsuchiyama/sb/by-year/{year}-single-table.csv"],
                    ["race", "athlete", "meet", year, sm],
                )
            )
            if len(out) >= limit:
                return out
    return out


def gen_team_orders(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        years = load_years(path)
        for year in sorted(years.keys(), reverse=True):
            for team in years[year].get("teams") or []:
                name = team.get("team") or ""
                if not name:
                    continue
                legs = [lg for lg in (team.get("legs") or []) if lg.get("name") and lg.get("leg")]
                if not legs:
                    continue
                eid = f"aragyoku-{year}-{gender}-team-{slug(name)}-order"
                if eid in existing_ids:
                    continue
                rank = team.get("rank")
                total = team.get("total") or "?"
                bits = [
                    f"{lg.get('leg')}区{(lg.get('name') or '').replace(' ', '')}"
                    f"（{lg.get('split') or '?'}）"
                    for lg in sorted(legs, key=lambda x: int(x.get("leg") or 0))
                ]
                qs = [
                    f"{year}年荒玉駅伝{gender}の{name}のオーダーは？",
                    f"{year}年荒玉{gender}{name}の区間メンバーは？",
                    f"{year}年の{name}{gender}オーダーを教えて",
                    f"{year}荒玉{gender}{name}誰が何区？",
                ]
                ans = f"{year}年荒玉駅伝{gender}・{name}のオーダーです。"
                if rank:
                    ans += f" 総合{rank}位（{total}）。"
                ans += " " + "、".join(bits) + "。"
                out.append(
                    entry(
                        eid,
                        qs,
                        ans,
                        [src],
                        ["aragyoku", "order", gender, int(year), name],
                    )
                )
                if len(out) >= limit:
                    return out
    return out


def gen_runner_careers(existing_ids: set[str], limit: int) -> list[dict]:
    """Per-runner aragyoku appearance history."""
    appear: dict[str, list[tuple]] = defaultdict(list)
    srcs = {
        "女子": "input/idaten-corpus/aragyoku/women_full_2012_2025.json",
        "男子": "input/idaten-corpus/aragyoku/men_full_2012_2025.json",
    }
    for gender, path in (("女子", WOMEN_FULL), ("男子", MEN_FULL)):
        for year, yd in load_years(path).items():
            for team in yd.get("teams") or []:
                tname = team.get("team") or ""
                for lg in team.get("legs") or []:
                    name = (lg.get("name") or "").replace(" ", "")
                    if not name or not lg.get("leg"):
                        continue
                    appear[name].append(
                        (
                            int(year),
                            gender,
                            tname,
                            int(lg.get("leg")),
                            lg.get("split") or "?",
                            team.get("rank"),
                        )
                    )
    out: list[dict] = []
    # Prefer multi-appearance athletes first (richer answers)
    ordered = sorted(
        appear.items(),
        key=lambda kv: (-len(kv[1]), -max(y for y, *_ in kv[1]), kv[0]),
    )
    for name, rows in ordered:
        eid = f"aragyoku-career-{slug(name)}"
        if eid in existing_ids:
            continue
        rows = sorted(rows, key=lambda x: (x[0], x[1], x[3]))
        lines = []
        genders = set()
        teams = set()
        for year, gender, team, leg, split, rank in rows:
            genders.add(gender)
            teams.add(team)
            bit = f"{year}年{gender}・{team}{leg}区（{split}）"
            if rank:
                bit += f"／総合{rank}位"
            lines.append(bit)
        qs = [
            f"{name}の荒玉出走歴は？",
            f"{name}は荒玉で何区を走った？",
            f"{name}の荒玉駅伝の区間は？",
            f"{name}の荒玉出場記録",
        ]
        g = "・".join(sorted(genders))
        t = "、".join(sorted(teams)[:4])
        ans = (
            f"{name}の荒玉駅伝出走歴は{len(lines)}回です"
            f"（{g}／所属例: {t}）。\n" + "\n".join(lines)
        )
        src_list = [srcs[g] for g in sorted(genders)]
        out.append(
            entry(
                eid,
                qs,
                ans,
                src_list,
                ["aragyoku", "career", "athlete", name],
            )
        )
        if len(out) >= limit:
            return out
    return out


def _split_to_sec(split: str) -> float:
    s = (split or "").strip()
    m = re.match(r"^(\d+):(\d{2})(?:\.(\d+))?$", s)
    if not m:
        return 1e12
    return int(m.group(1)) * 60 + int(m.group(2)) + (
        float(f"0.{m.group(3)}") if m.group(3) else 0
    )


def gen_leg_awards(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        years = load_years(path)
        for year in sorted(years.keys(), reverse=True):
            by_leg: dict[int, list[tuple[str, str, str]]] = defaultdict(list)
            for team in years[year].get("teams") or []:
                tname = team.get("team") or ""
                for lg in team.get("legs") or []:
                    leg = lg.get("leg")
                    runner = (lg.get("name") or "").replace(" ", "")
                    split = lg.get("split") or ""
                    if not leg or not runner or not split:
                        continue
                    by_leg[int(leg)].append((tname, runner, split))
            for leg, rows in sorted(by_leg.items()):
                eid = f"aragyoku-{year}-{gender}-leg{leg}-best"
                if eid in existing_ids:
                    continue
                ranked = sorted(rows, key=lambda x: _split_to_sec(x[2]))
                best_team, best_name, best_split = ranked[0]
                top3 = ranked[:3]
                qs = [
                    f"{year}年荒玉{gender}{leg}区の区間賞は誰？",
                    f"{year}年荒玉駅伝{gender}の{leg}区最速は？",
                    f"{year}荒玉{gender}{leg}区賞",
                ]
                ans = (
                    f"{year}年荒玉駅伝{gender}{leg}区の最速（区間賞相当）は"
                    f"{best_name}（{best_team}・{best_split}）です。"
                )
                if len(top3) > 1:
                    ans += " 上位: " + "、".join(
                        f"{i+1}位{n}（{t}・{s}）" for i, (t, n, s) in enumerate(top3)
                    ) + "。"
                out.append(
                    entry(
                        eid,
                        qs,
                        ans,
                        [src],
                        ["aragyoku", "leg-award", gender, int(year)],
                    )
                )
                if len(out) >= limit:
                    return out
    return out


def gen_remaining_legs(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        for year in sorted(load_years(path).keys(), reverse=True):
            for team in load_years(path)[year].get("teams") or []:
                name = team.get("team") or ""
                for lg in team.get("legs") or []:
                    runner = (lg.get("name") or "").replace(" ", "")
                    leg_no = lg.get("leg")
                    split = lg.get("split") or "?"
                    if not runner or not leg_no:
                        continue
                    eid = f"aragyoku-{year}-{gender}-{slug(name)}-leg{leg_no}"
                    if eid in existing_ids:
                        continue
                    qs = [
                        f"{year}年荒玉駅伝{gender}の{name}{leg_no}区は誰？",
                        f"{year}年荒玉{gender}{name}の{leg_no}区走者は？",
                        f"{name}の{year}年荒玉{gender}{leg_no}区",
                    ]
                    ans = (
                        f"{year}年荒玉駅伝{gender}の{name}{leg_no}区は{runner}"
                        f"（区間タイム{split}）です。"
                    )
                    out.append(
                        entry(
                            eid,
                            qs,
                            ans,
                            [src],
                            ["aragyoku", "leg", gender, int(year), name],
                        )
                    )
                    if len(out) >= limit:
                        return out
    return out


def gen_sb_gaps(existing_ids: set[str], limit: int) -> list[dict]:
    keywords = load_keywords()
    out: list[dict] = []
    for year in range(DEFAULT_YEAR, 2011, -1):
        path = BY_YEAR_SB / f"{year}-sb-adopted.json"
        if not path.exists():
            continue
        for r in json.loads(path.read_text(encoding="utf-8")):
            if not _truthy_sb(r.get("SB採用")):
                continue
            aff = (r.get("所属") or "").strip()
            name = (r.get("名前") or "").strip()
            dist = (r.get("距離") or "").strip()
            mark = (r.get("SB") or r.get("記録") or "").strip()
            if not name or not dist or not mark:
                continue
            if not any(k in aff for k in keywords):
                continue
            eid = f"sb-{year}-{slug(name)}-{slug(dist)}"
            if eid in existing_ids or any(e["id"] == eid for e in out):
                continue
            # skip if aggregate-only already covers and year is current with same dist? keep per-dist
            meet = (r.get("大会名") or "").strip()
            date = (r.get("日付") or "").strip()
            url = meet_url(r)
            qs = [
                f"{year}年{name}の{dist}の自己ベストは？",
                f"{year}年の{name}の{dist}SBは？",
                f"{name}の{year}年度{dist}記録",
            ]
            if year == DEFAULT_YEAR:
                qs.extend(
                    [
                        f"{name}の{dist}の自己ベストは？",
                        f"{name}の{dist}SBは？",
                    ]
                )
            ans = f"{name}（{aff}）の{year}年度・{dist}シーズンベスト（SB採用）は {mark} です。"
            if meet or date:
                ans += f" 大会: {meet}（{date}）。"
            if url:
                ans += f" 大会結果: {url}"
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [str(path.relative_to(ROOT))],
                    ["sb", "athlete", dist, year],
                )
            )
            if len(out) >= limit:
                return out
    return out


def gen_calendar_gap(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    drive_map = load_drive_meet_folder_map()
    event_files = [
        (2026, EVENTS_2026),
        (2025, EVENTS_2025),
        (2024, EVENTS_2024),
    ]
    for year, path in event_files:
        if not path.exists():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for ev in data.get("events") or []:
            title = (ev.get("title") or "").strip()
            date = ev.get("date") or ev.get("start")
            if not title or not date:
                continue
            if re.match(r"^(TODO|仮|未定|テスト)$", title):
                continue
            eid = f"cal-{year}-{str(date).replace('-', '')}-{slug(title)[:28]}"
            if eid in existing_ids or any(e["id"] == eid for e in out):
                eid = f"calx-{year}-{str(date).replace('-', '')}-{slug(title)[:28]}"
                if eid in existing_ids or any(e["id"] == eid for e in out):
                    continue
            loc = ev.get("location") or ""
            desc = (ev.get("description") or "").strip()
            status = ev.get("status") or ""
            if int(year) == DEFAULT_YEAR:
                qs = [
                    f"{title}はいつ？",
                    f"{year}年の{title}の日程は？",
                    f"今年の{title}について",
                ]
            else:
                qs = [
                    f"{year}年の{title}はいつ？",
                    f"{year}年の{title}の日程は？",
                ]
            ans = friendly_calendar_answer(
                title,
                str(date)[:10],
                location=str(loc or ""),
                status=str(status) if status else None,
                description=desc,
                drive_url=drive_url_for_calendar(title, desc, drive_map),
            )
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [f"input/events.{year}.yaml"],
                    ["calendar", "schedule", year],
                )
            )
            if len(out) >= limit:
                return out
    return out


def gen_practice_sessions(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    for year in (2026, 2025, 2024, 2023, 2022):
        path = ROOT / "out" / str(year) / "practice.json"
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else list(data.values()) if isinstance(data, dict) else []
        for ev in items:
            if not isinstance(ev, dict):
                continue
            title = (ev.get("title") or "").strip()
            date = (ev.get("date") or "").strip()
            if not title or not date:
                continue
            eid = f"practice-{year}-{date.replace('-', '')}-{slug(title)[:28]}"
            if eid in existing_ids or any(e["id"] == eid for e in out):
                continue
            start = ev.get("start_time") or ""
            end = ev.get("end_time") or ""
            prac = ev.get("practice") or {}
            bits = []
            if isinstance(prac, dict):
                if prac.get("warmup"):
                    bits.append(f"ウォームアップ: {prac['warmup']}")
                for it in prac.get("items") or []:
                    if not isinstance(it, dict):
                        continue
                    g = it.get("group") or ""
                    typ = it.get("type") or ""
                    dist = it.get("distance_km")
                    reps = it.get("reps")
                    piece = f"{g}{typ}".strip()
                    if dist:
                        piece += f" {dist}km"
                    if reps:
                        piece += f"×{reps}"
                    if piece:
                        bits.append(piece)
            qs = [
                f"{title}のメニューは？",
                f"{date}の{title}",
                f"{year}年{title}の練習内容",
            ]
            if year == DEFAULT_YEAR:
                qs.append(f"今年の{title}の練習は？")
            ans = f"{title}は {date}"
            if start:
                ans += f" {start}"
                if end:
                    ans += f"–{end}"
            ans += " です。"
            if bits:
                ans += " 内容: " + "、".join(bits[:8]) + "。"
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [str(path.relative_to(ROOT))],
                    ["practice", year],
                )
            )
            if len(out) >= limit:
                return out
    return out


def gen_course_points(existing_ids: set[str], limit: int) -> list[dict]:
    path = ROOT / "input" / "aragyoku" / "course-points.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[dict] = []
    drive = data.get("drive_url") or ""
    for pt in data.get("points") or []:
        pid = pt.get("id") or ""
        label = pt.get("label") or pid
        if not pid:
            continue
        eid = f"course-point-{slug(pid)}"
        if eid in existing_ids:
            continue
        note = pt.get("location_note") or ""
        w = pt.get("women") or {}
        m = pt.get("men") or {}
        wbits = [f"女子{k}区={v}" for k, v in w.items()]
        mbits = [f"男子{k}区={v}" for k, v in m.items()]
        qs = [
            f"荒玉の{label}はどこ？",
            f"荒玉コースの{label}",
            f"{label}は何区の何km？",
        ]
        if pid in {"C", "B", "D", "E", "A"}:
            qs.append(f"荒玉の{pid}地点は？")
        ans = f"荒玉駅伝コースの{label}です。"
        if note:
            ans += f" {note}。"
        if wbits:
            ans += " " + "、".join(wbits) + "。"
        if mbits:
            ans += " " + "、".join(mbits) + "。"
        if drive:
            ans += f" コース図: {drive}"
        out.append(
            entry(
                eid,
                qs,
                ans,
                ["input/aragyoku/course-points.json"],
                ["aragyoku", "course", pid],
            )
        )
        if len(out) >= limit:
            return out
    # overview
    eid = "course-points-overview"
    if eid not in existing_ids:
        qs = [
            "荒玉のコースポイントは？",
            "荒玉駅伝のA地点B地点は？",
            "荒玉コースの共通ポイントは？",
        ]
        ans = (
            f"{data.get('title') or '荒玉コース共通ポイント'}。"
            f" 1周{data.get('lap_metres')}m。"
            f" {data.get('distance_note') or ''}"
        )
        if drive:
            ans += f" 図: {drive}"
        out.append(
            entry(
                eid,
                qs,
                ans.strip(),
                ["input/aragyoku/course-points.json"],
                ["aragyoku", "course"],
            )
        )
    return out[:limit]


def gen_media_boards(existing_ids: set[str], limit: int) -> list[dict]:
    path = ROOT / "input" / "external" / "media-manifest.json"
    if not path.exists():
        return []
    items = json.loads(path.read_text(encoding="utf-8")).get("items") or []
    out: list[dict] = []
    for it in items:
        if it.get("topic") != "ekiden":
            continue
        year = it.get("year")
        gender = it.get("gender") or ""
        stem = it.get("stem") or f"{year}-{gender}"
        eid = f"media-ekiden-{slug(str(stem))}"
        if eid in existing_ids:
            continue
        ocr = it.get("ocr_path")
        summary = ""
        if ocr and (ROOT / ocr).exists():
            text = (ROOT / ocr).read_text(encoding="utf-8", errors="replace")
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            keep = [ln for ln in lines[:30] if re.search(r"\d|位|区|優勝|タイム", ln)]
            summary = " ".join(keep[:8])
            if len(summary) > 220:
                summary = summary[:219] + "…"
        qs = [
            f"{year}年荒玉{gender}の結果ボードは？",
            f"{year}年荒玉駅伝{gender}の成績表画像",
            f"{year}荒玉{gender}OCR",
        ]
        ans = f"{year}年荒玉駅伝{gender}の結果ボード（OCR）です。"
        if summary:
            ans += " " + summary
            if not ans.endswith("。"):
                ans += "。"
        if it.get("notion_page_url"):
            ans += f" 参照: {it['notion_page_url']}"
        out.append(
            entry(
                eid,
                qs,
                ans,
                [ocr] if ocr else [str(path.relative_to(ROOT))],
                ["aragyoku", "media", "ocr", year, gender],
            )
        )
        if len(out) >= limit:
            return out
    return out


def gen_daiming_focus(existing_ids: set[str], limit: int) -> list[dict]:
    """Extra natural paraphrases for 岱明 athletes' current-year races & SB."""
    keywords = ["岱明"]
    out: list[dict] = []
    # current year races already in race-*; add grade/school scoped asks
    path = BY_YEAR_SB / f"{DEFAULT_YEAR}-sb-adopted.json"
    if not path.exists():
        return out
    by_name: dict[str, list[dict]] = defaultdict(list)
    for r in json.loads(path.read_text(encoding="utf-8")):
        if not _truthy_sb(r.get("SB採用")):
            continue
        aff = (r.get("所属") or "").strip()
        name = (r.get("名前") or "").strip()
        if not name or not any(k in aff for k in keywords):
            continue
        by_name[name].append(r)
    for name, rows in sorted(by_name.items()):
        eid = f"sb-focus-{DEFAULT_YEAR}-{slug(name)}-alldist"
        if eid in existing_ids:
            continue
        # skip if identical to records-athlete aggregate SB-only; still useful as SB-focused ask
        parts = []
        for r in sorted(rows, key=lambda x: x.get("距離") or ""):
            dist = r.get("距離")
            mark = r.get("SB") or r.get("記録")
            url = meet_url(r)
            bit = f"{dist} {mark}"
            if url:
                bit += f"（大会結果: {url}）"
            parts.append(bit)
        if not parts:
            continue
        qs = [
            f"{name}の今年度の自己ベスト一覧は？",
            f"{name}のSBを全部教えて",
            f"{name}の距離別ベストは？",
            f"岱明の{name}のSB一覧",
        ]
        ans = (
            f"{name}（岱明）の{DEFAULT_YEAR}年度自己ベスト（SB採用）です。\n"
            + "\n".join(parts)
        )
        out.append(
            entry(
                eid,
                qs,
                ans,
                [str(path.relative_to(ROOT))],
                ["sb", "athlete", "daiming", DEFAULT_YEAR],
            )
        )
        if len(out) >= limit:
            return out
    return out


def gen_school_year_rankings(existing_ids: set[str], limit: int) -> list[dict]:
    """School × year × distance top3 (aragyoku keywords)."""
    keywords = load_keywords()
    out: list[dict] = []
    for year in range(DEFAULT_YEAR, 2019, -1):
        path = BY_YEAR_SB / f"{year}-sb-adopted.json"
        if not path.exists():
            continue
        by: dict[tuple[str, str], list[tuple[float, str, str, str]]] = defaultdict(list)
        for r in json.loads(path.read_text(encoding="utf-8")):
            if not _truthy_sb(r.get("SB採用")):
                continue
            aff = (r.get("所属") or "").strip()
            name = (r.get("名前") or "").strip()
            dist = (r.get("距離") or "").strip()
            mark = (r.get("SB") or r.get("記録") or "").strip()
            if not name or not dist or not mark:
                continue
            if not any(k in aff for k in keywords):
                continue
            school = re.sub(r"(中学校|中学|中)$", "", aff) or aff
            try:
                sec = float(r.get("SB秒") or r.get("記録秒") or 1e12)
            except (TypeError, ValueError):
                continue
            url = meet_url(r)
            by[(school, dist)].append((sec, name, mark, url))
        for (school, dist), rows in sorted(by.items()):
            eid = f"rank-school-{year}-{slug(school)}-{slug(dist)}"
            if eid in existing_ids or any(e["id"] == eid for e in out):
                continue
            # unique best per athlete
            best_by_athlete: dict[str, tuple] = {}
            for sec, name, mark, url in rows:
                prev = best_by_athlete.get(name)
                if prev is None or sec < prev[0]:
                    best_by_athlete[name] = (sec, name, mark, url)
            top = sorted(best_by_athlete.values(), key=lambda x: x[0])[:3]
            if not top:
                continue
            qs = [
                f"{year}年{school}の{dist}ランキングは？",
                f"{year}年{school}{dist}の上位は？",
                f"{school}の{year}年度{dist}トップ3",
            ]
            if year == DEFAULT_YEAR:
                qs.append(f"{school}の{dist}ランキングは？")
            lines = []
            for i, (_sec, name, mark, url) in enumerate(top, 1):
                bit = f"{i}位 {name} {mark}"
                if url:
                    bit += f" 大会結果: {url}"
                lines.append(bit)
            ans = f"{year}年度・{school}の{dist}上位です。\n" + "\n".join(lines)
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [str(path.relative_to(ROOT))],
                    ["sb", "ranking", "school", dist, year],
                )
            )
            if len(out) >= limit:
                return out
    return out


def build_new_entries(existing_ids: set[str], target: int) -> list[dict]:
    used = set(existing_ids)
    buckets = {
        "athlete_meet": gen_athlete_meet(existing_ids, 3600),
        "team_orders": gen_team_orders(existing_ids, 500),
        "careers": gen_runner_careers(existing_ids, 1600),
        "leg_awards": gen_leg_awards(existing_ids, 200),
        "legs_rem": gen_remaining_legs(existing_ids, 200),
        "sb_gaps": gen_sb_gaps(existing_ids, 400),
        "calendar": gen_calendar_gap(existing_ids, 300),
        "practice": gen_practice_sessions(existing_ids, 400),
        "course": gen_course_points(existing_ids, 40),
        "media": gen_media_boards(existing_ids, 80),
        "daiming": gen_daiming_focus(existing_ids, 80),
        "school_rank": gen_school_year_rankings(existing_ids, 900),
    }
    for k, v in buckets.items():
        print(f"  bucket {k}: {len(v)}")

    # quality-first quotas
    quotas = [
        ("athlete_meet", 2800),
        ("team_orders", 420),
        ("careers", 900),
        ("school_rank", 500),
        ("leg_awards", 140),
        ("legs_rem", 100),
        ("sb_gaps", 200),
        ("calendar", 200),
        ("practice", 200),
        ("daiming", 40),
        ("media", 40),
        ("course", 20),
    ]
    selected: list[dict] = []
    for name, n in quotas:
        got = take(buckets[name], n, used)
        selected.extend(got)
        print(f"  took {name}: {len(got)}/{n}")

    if len(selected) < target:
        for name, _ in quotas:
            if len(selected) >= target:
                break
            selected.extend(take(buckets[name], target - len(selected), used))
    # last resort order
    if len(selected) < target:
        for name in (
            "athlete_meet",
            "careers",
            "school_rank",
            "team_orders",
            "practice",
            "sb_gaps",
            "calendar",
        ):
            if len(selected) >= target:
                break
            selected.extend(take(buckets[name], target - len(selected), used))

    print(f"  FINAL new: {len(selected[:target])}")
    return selected[:target]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--target", type=int, default=5000)
    args = parser.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = data.get("entries") or []
    existing_ids = {e["id"] for e in entries}
    print(f"existing entries: {len(entries)}")

    new_entries = build_new_entries(existing_ids, args.target)
    if len(new_entries) < args.target:
        raise SystemExit(f"expected {args.target} new entries, got {len(new_entries)}")

    existing_q = {q for e in entries for q in (e.get("questions") or [])}
    cleaned: list[dict] = []
    for e in new_entries:
        qs = [q for q in e["questions"] if q not in existing_q]
        if not qs:
            continue
        e = dict(e)
        e["questions"] = qs
        cleaned.append(e)
        for q in qs:
            existing_q.add(q)

    if len(cleaned) < args.target:
        more = build_new_entries(
            existing_ids | {e["id"] for e in cleaned},
            args.target - len(cleaned) + 400,
        )
        have = {e["id"] for e in cleaned} | existing_ids
        for e in more:
            if e["id"] in have:
                continue
            qs = [q for q in e["questions"] if q not in existing_q]
            if not qs:
                continue
            e = dict(e)
            e["questions"] = qs
            cleaned.append(e)
            have.add(e["id"])
            for q in qs:
                existing_q.add(q)
            if len(cleaned) >= args.target:
                break

    cleaned = cleaned[: args.target]
    if len(cleaned) < args.target:
        raise SystemExit(f"after cleanup expected {args.target}, got {len(cleaned)}")

    merged = list(entries) + cleaned
    seen: set[str] = set()
    uniq = []
    for e in merged:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        uniq.append(e)

    data["entries"] = uniq
    data["total"] = len(uniq)
    note = data.get("note") or ""
    if "+5000" not in note:
        data["note"] = (
            note.rstrip()
            + "\nナレッジギャップ埋め+5000（大会別記録・オーダー・出走歴・学校順位等）。\n"
        )
    print(f"merged total {len(uniq)} (+{len(cleaned)})")
    for sid in (
        "race-2026-南本幸治郎-通信陸上",
        "aragyoku-career-松野凛空",
        "aragyoku-2025-男子-team-岱明-order",
    ):
        e = next((x for x in cleaned if x["id"] == sid), None)
        if e:
            print("SAMPLE", e["id"], e["answer"][:200].replace("\n", " | "))

    if args.dry_run:
        return 0

    FAQ.write_text(
        yaml.dump(
            data,
            allow_unicode=True,
            sort_keys=False,
            width=120,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {FAQ.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
