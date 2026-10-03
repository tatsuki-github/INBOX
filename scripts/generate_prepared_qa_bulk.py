#!/usr/bin/env python3
"""Generate diverse prepared FAQ entries (target: keep first 100 + add 1000).

Usage:
  python3 scripts/generate_prepared_qa_bulk.py
  python3 scripts/generate_prepared_qa_bulk.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
MEN_FULL = ROOT / "input" / "idaten-corpus" / "aragyoku" / "men_full_2012_2025.json"
WOMEN_FULL = ROOT / "input" / "idaten-corpus" / "aragyoku" / "women_full_2012_2025.json"
EVENTS_2026 = ROOT / "input" / "events.2026.yaml"
EVENTS_2025 = ROOT / "input" / "events.2025.yaml"
SB_2026 = ROOT / "input" / "idaten-corpus" / "drive-text" / "記録データベース" / "2026年度" / "中学生記録.csv"
SB_3000 = (
    ROOT
    / "input"
    / "idaten-corpus"
    / "drive-text"
    / "記録データベース"
    / "2025年度"
    / "3000m予想タイムランキング.csv"
)
WINNERS = ROOT / "input" / "aragyoku" / "winners-by-year.md"
COURSE_POINTS = ROOT / "input" / "aragyoku" / "course-points.md"
DISTANCE_DOC = ROOT / "docs" / "aragyoku-ekiden-distance-definitions.md"
OVERVIEW = ROOT / "out" / "analysis" / "aragyoku-overview.md"

FOCUS_TEAMS = {
    "岱明",
    "玉名",
    "南関",
    "菊水",
    "荒尾三",
    "荒尾四",
    "荒尾海陽",
    "玉陵",
    "玉高附属",
    "長洲",
    "天水",
    "有明",
}
PRIORITY_AFFILIATIONS = ("岱明", "ATRC", "金栗", "南関", "菊水", "玉名", "荒尾")


def slug(s: str) -> str:
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^\w一-龥ぁ-んァ-ヶー\-]", "-", s)
    return s.strip("-")[:48] or "x"


_PATHISH = re.compile(
    r"`[^`]+`"
    r"|(?:(?:input|out|docs|backend|scripts)/[\w./\-（）()\u3040-\u30ff\u4e00-\u9fff]+)"
    r"|(?:[\w./\-（）()\u3040-\u30ff\u4e00-\u9fff]+?\.(?:md|yaml|yml|json|csv|txt|pdf)(?:\.meta\.json)?)"
    r"|(?:/opt/[\w./\-]+)"
    r"|(?:python3(?:\s+[\w./\-]+)+)"
)


def clean_user_facing_text(text: str, *, max_len: int = 220) -> str:
    """Strip repo paths / filenames; keep human summary and http(s) URLs."""
    if not text:
        return ""
    t = text.replace("\n", " ")
    # Drop Drive import metadata dumps (mimeType / fileSize / viewUrl …).
    t = re.sub(
        r"(?:^|\s)[-*]?\s*\*\*(?:id|mimeType|fileSize|viewUrl|parentId|modifiedTime|status|name)\*\*\s*[:：]?[^\s]*",
        " ",
        t,
        flags=re.I,
    )
    t = re.sub(
        r"\b(?:mimeType|fileSize|parentId|modifiedTime)\b\s*[:：]?\s*\S*",
        " ",
        t,
        flags=re.I,
    )
    # Drop generator / ops tails early
    t = re.sub(r"生成\s*[:：].*$", " ", t)
    t = _PATHISH.sub(" ", t)
    t = re.sub(
        r"(岱明確定オーダー|現行数式予想|校別展開|現行予測|旧SB予測|距離正本|コーパス|正本|結果詳細)\s*[:：]?\s*",
        " ",
        t,
    )
    t = re.sub(r"（比較用）", " ", t)
    t = re.sub(r"[・/|→]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" 。\t")
    # If almost nothing useful remains (punctuation only), drop
    if len(re.sub(r"[\s\W]+", "", t)) < 2:
        return ""
    if len(t) > max_len:
        t = t[: max_len - 1].rstrip() + "…"
    return t


def friendly_status_phrase(status: str | None) -> str:
    s = (status or "").strip().lower()
    if s in {"done", "completed"}:
        return "実施済みです。"
    if s in {"cancelled", "canceled", "中止"}:
        return "中止です。"
    # scheduled / unknown → omit jargon like 「状態: scheduled」
    return ""


def friendly_calendar_answer(
    title: str,
    date: str,
    *,
    location: str = "",
    status: str | None = None,
    description: str = "",
    drive_url: str | None = None,
) -> str:
    parts = [f"{title}は {date} です。"]
    if location:
        parts.append(f"場所: {location}。")
    status_phrase = friendly_status_phrase(status)
    if status_phrase:
        parts.append(status_phrase)
    summary = clean_user_facing_text(description, max_len=200)
    if summary:
        # Keep useful notes / public URLs; avoid dumping internal ops text
        if summary.startswith("http"):
            parts.append(f"詳細: {summary}")
        else:
            parts.append(summary if summary.endswith("。") else summary + "。")
    if drive_url:
        parts.append(f"資料: {drive_url}")
    return " ".join(parts)


def load_drive_meet_folder_map() -> dict[str, str]:
    idx = ROOT / "input" / "external" / "drive" / "shared" / "大会" / "INDEX.md"
    out: dict[str, str] = {}
    if not idx.exists():
        return out
    for m in re.finditer(
        r"\[([^\]]+)\]\((https://drive\.google\.com/drive/folders/[^)]+)\)",
        idx.read_text(encoding="utf-8"),
    ):
        out[m.group(1)] = m.group(2)
    return out


def resolve_drive_meet_url(
    folder_name: str,
    title: str,
    drive_map: dict[str, str],
) -> str | None:
    if folder_name in drive_map:
        return drive_map[folder_name]
    # Prefer keys that share the leading date token (e.g. 1014-1015_)
    prefix = folder_name.split("_", 1)[0] if "_" in folder_name else ""
    candidates: list[tuple[str, str]] = []
    for key, url in drive_map.items():
        if key == title or key.endswith("_" + title) or key.endswith(folder_name):
            candidates.append((key, url))
        elif title and title in key:
            candidates.append((key, url))
        elif folder_name and folder_name in key:
            candidates.append((key, url))
    if not candidates:
        return None
    if prefix:
        pref = [c for c in candidates if c[0].startswith(prefix)]
        if pref:
            return sorted(pref, key=lambda x: -len(x[0]))[0][1]
    return sorted(candidates, key=lambda x: -len(x[0]))[0][1]


def drive_url_for_calendar(title: str, description: str, drive_map: dict[str, str]) -> str | None:
    """Best-effort Drive folder for calendar answers (from description path or title)."""
    m = re.search(r"大会/(20\d{2})年度/([^/\s]+)", description or "")
    if m:
        folder = m.group(2).rstrip("/")
        url = resolve_drive_meet_url(folder, re.sub(r"^\d{2,4}[-_]?", "", folder), drive_map)
        if url:
            return url
    # Known short titles
    aliases = {
        "荒玉中体連駅伝": "1014-1015_荒玉中体連駅伝",
        "荒玉中体連駅伝予備日": "1014-1015_荒玉中体連駅伝",
        "玉名郡ナイター中・長距離記録会": "0829_玉名郡ナイター中・長距離記録会",
    }
    folder = aliases.get(title)
    if folder:
        return drive_map.get(folder)
    return None


def friendly_meet_folder_answer(title: str, year: str, folder_name: str, drive_url: str | None) -> str:
    if drive_url:
        return (
            f"{title}（{year}）の大会フォルダ（Googleドライブ）です。\n"
            f"{drive_url}\n"
            "結果・オーダー・要項などの資料はこちらから確認できます。"
        )
    return (
        f"{title}（{year}）の大会資料フォルダは「{folder_name}」です。"
        "結果やオーダー表などの資料があります。"
    )


def entry(
    eid: str,
    questions: list[str],
    answer: str,
    sources: list[str],
    tags: list,
) -> dict:
    qs = []
    seen = set()
    for q in questions:
        q = re.sub(r"\s+", " ", q).strip()
        if not q or q in seen:
            continue
        seen.add(q)
        qs.append(q)
    if not qs:
        raise ValueError(f"no questions for {eid}")
    ans = answer.strip() + "\n"
    return {
        "id": eid,
        "questions": qs,
        "answer": ans,
        "sources": sources,
        "tags": tags,
    }


def load_years(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    years = data["years"]
    if isinstance(years, dict):
        return {str(k): v for k, v in years.items()}
    out = {}
    for y in years:
        out[str(y["year"])] = y
    return out


def gen_aragyoku_winners(existing_ids: set[str]) -> list[dict]:
    men = load_years(MEN_FULL)
    women = load_years(WOMEN_FULL)
    out: list[dict] = []
    for gender, years, src in (
        ("女子", women, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", men, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        for year, yd in sorted(years.items()):
            teams = yd.get("teams") or []
            if len(teams) < 2:
                continue
            w, r = teams[0], teams[1]
            for kind, team, other in (
                ("winner", w, r),
                ("runnerup", r, w),
            ):
                eid = f"aragyoku-{year}-{gender}-{kind}"
                if eid in existing_ids:
                    continue
                if kind == "winner":
                    qs = [
                        f"{year}年荒玉駅伝{gender}の優勝校は？",
                        f"{year}年荒玉{gender}優勝は？",
                        f"{year}年の荒玉{gender}1位はどこ？",
                    ]
                    ans = (
                        f"{year}年荒玉駅伝{gender}の優勝は{team['team']}（{team.get('total','?')}）、"
                        f"準優勝は{other['team']}（{other.get('total','?')}）です。"
                    )
                else:
                    qs = [
                        f"{year}年荒玉駅伝{gender}の準優勝校は？",
                        f"{year}年荒玉{gender}準優勝は？",
                        f"{year}年の荒玉{gender}2位はどこ？",
                    ]
                    ans = (
                        f"{year}年荒玉駅伝{gender}の準優勝は{team['team']}（{team.get('total','?')}）です。"
                        f"優勝は{other['team']}（{other.get('total','?')}）です。"
                    )
                out.append(
                    entry(
                        eid,
                        qs,
                        ans,
                        [src, "input/aragyoku/winners-by-year.md"],
                        ["aragyoku", "result", gender, int(year)],
                    )
                )
    return out


def _leg_bits(team: dict) -> list[str]:
    bits: list[str] = []
    for lg in team.get("legs") or []:
        runner = (lg.get("name") or "").replace(" ", "")
        if not runner:
            continue
        leg_no = lg.get("leg")
        grade = lg.get("grade")
        split = lg.get("split") or ""
        bit = f"{leg_no}区{runner}"
        if grade not in (None, ""):
            bit += f"（{grade}年）"
        if split:
            bit += f"{split}"
        bits.append(bit)
    return bits


def team_result_questions(year: int, gender: str, name: str) -> list[str]:
    """Natural phrasings including 去年/結果は？ without forcing 荒玉-first word order."""
    qs = [
        f"{year}年荒玉駅伝{gender}の{name}は何位？",
        f"{year}年荒玉{gender}{name}の順位は？",
        f"{year}年の荒玉{gender}で{name}の成績は？",
        f"{year}年の{name}の{gender}の結果は？",
        f"{year}年{name}{gender}の結果は？",
        f"{year}年荒玉駅伝の{name}の{gender}の結果は？",
        f"{year}年の荒玉駅伝{name}{gender}の結果",
        f"{year}年{name}の{gender}の荒玉の結果は？",
    ]
    # 相対年（今年度のひとつ前＝2025）
    if year == 2025:
        qs.extend(
            [
                f"去年の{name}の{gender}の結果は？",
                f"昨年の{name}の{gender}の結果は？",
                f"去年の{name}{gender}の結果は？",
                f"昨年の{name}{gender}の結果",
                f"去年の荒玉駅伝の{name}の{gender}の結果は？",
                f"昨年の荒玉駅伝{gender}の{name}の結果は？",
                f"去年の荒玉の{name}{gender}の結果は？",
                f"昨年の荒玉{gender}で{name}は？",
            ]
        )
        if gender == "女子":
            qs.append(f"去年の荒玉女子で{name}は？")
        else:
            qs.append(f"去年の荒玉男子で{name}は何位？")
    return qs


def format_team_result_answer(year: int, gender: str, team: dict) -> str:
    name = team.get("team") or ""
    rank = team.get("rank")
    total = team.get("total") or "?"
    ans = f"{year}年荒玉駅伝{gender}の{name}は{rank}位・総合{total}です。"
    for leg in team.get("legs") or []:
        grade = f"（{leg['grade']}年）" if leg.get("grade") is not None else ""
        split_rank = f"{leg['split_rank']}位" if leg.get("split_rank") is not None else "未確認"
        passing_rank = f"{leg['passing_rank']}位" if leg.get("passing_rank") is not None else "未確認"
        ans += (f"\n・{leg['leg']}区: {leg.get('name') or '未確認'}{grade} "
                f"区間タイム {leg.get('split') or '未確認'}（区間順位 {split_rank}） / "
                f"通過タイム {leg.get('cumulative') or '未確認'}（通過順位 {passing_rank}）")
    return ans


def gen_aragyoku_team_ranks(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        years = load_years(path)
        # Prefer recent years first
        for year in sorted(years.keys(), reverse=True):
            yd = years[year]
            for team in yd.get("teams") or []:
                name = team.get("team") or ""
                rank = team.get("rank")
                if not name or not rank:
                    continue
                # Keep focus teams always; others only recent years
                if name not in FOCUS_TEAMS and int(year) < 2020:
                    continue
                eid = f"aragyoku-{year}-{gender}-team-{slug(name)}-rank"
                if eid in existing_ids:
                    continue
                qs = team_result_questions(int(year), gender, name)
                ans = format_team_result_answer(int(year), gender, team)
                out.append(
                    entry(
                        eid,
                        qs,
                        ans,
                        [
                            src,
                            f"input/aragyoku/transcripts/{year}-{gender}.json",
                            f"out/analysis/aragyoku-teams/{name}.md",
                        ],
                        ["aragyoku", "team", "result", gender, int(year)],
                    )
                )
                if len(out) >= limit:
                    return out
    return out


def gen_aragyoku_legs(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        years = load_years(path)
        for year in sorted(years.keys(), reverse=True):
            yd = years[year]
            for team in yd.get("teams") or []:
                name = team.get("team") or ""
                if name not in FOCUS_TEAMS:
                    continue
                # 岱明: all years; others: 2018+
                if name != "岱明" and int(year) < 2018:
                    continue
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
                        f"{year}年の{name}{gender}{leg_no}区は？",
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


def gen_calendar(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    interesting = re.compile(
        r"駅伝|ジュニア|なごみ|荒玉|記録会|選手権|金栗|練習会|BBQ|玉名|熊日|通信|中学|長距離|オリンピック|国体|国スポ|合同|桃田|さくら|マスターズ|私学|谷口|天草|荒尾記録|交通費|厚底|伸び代|地域部"
    )
    for year, path in ((2026, EVENTS_2026), (2025, EVENTS_2025)):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        events = data.get("events") or []
        for ev in events:
            title = (ev.get("title") or "").strip()
            date = ev.get("date") or ev.get("start")
            if not title or not date:
                continue
            blob = " ".join(
                [
                    title,
                    str(ev.get("tags") or ""),
                    str(ev.get("description") or "")[:200],
                    str(ev.get("category") or ""),
                ]
            )
            if not interesting.search(blob):
                continue
            # skip pure practice:daiming daily runs unless titled specially
            tags = ev.get("tags") or []
            if "practice:daiming" in tags and not interesting.search(title):
                continue
            eid = f"cal-{year}-{str(date).replace('-', '')}-{slug(title)[:28]}"
            if eid in existing_ids:
                continue
            status = ev.get("status") or "scheduled"
            loc = ev.get("location") or ""
            desc = (ev.get("description") or "").strip()
            # 年なし質問は今年度のみ。過去年は西暦付きに固定（ADR 059）
            if int(year) == 2026:
                qs = [
                    f"{title}はいつ？",
                    f"{year}年の{title}の日程は？",
                    f"{title}について教えて",
                    f"今年の{title}はいつ？",
                ]
            else:
                qs = [
                    f"{year}年の{title}はいつ？",
                    f"{year}年の{title}の日程は？",
                    f"{year}年の{title}について教えて",
                ]
            if str(date)[:10] != str(date):
                pass
            drive_map = getattr(gen_calendar, "_drive_map", None)
            if drive_map is None:
                drive_map = load_drive_meet_folder_map()
                gen_calendar._drive_map = drive_map  # type: ignore[attr-defined]
            ans = friendly_calendar_answer(
                title,
                str(date),
                location=str(loc or ""),
                status=str(status) if status else None,
                description=desc,
                drive_url=drive_url_for_calendar(title, desc, drive_map),
            )
            src = f"input/events.{year}.yaml"
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [src],
                    ["calendar", "schedule", year],
                )
            )
            if len(out) >= limit:
                return out
    return out


def gen_sb(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    if not SB_2026.exists():
        return out
    rows = list(csv.DictReader(SB_2026.open(encoding="utf-8")))
    # Priority: 岱明 / ATRC / 金栗 first, then others with SB採用
    prioritized = []
    others = []
    for r in rows:
        if str(r.get("SB採用", "")).upper() != "TRUE":
            continue
        aff = r.get("所属") or ""
        if any(p in aff for p in PRIORITY_AFFILIATIONS):
            prioritized.append(r)
        else:
            others.append(r)
    ordered = prioritized + others
    seen_keys = set()
    for r in ordered:
        name = (r.get("名前") or "").strip()
        dist = (r.get("距離") or "").strip()
        mark = (r.get("記録") or "").strip()
        aff = (r.get("所属") or "").strip()
        meet = (r.get("大会名") or "").strip()
        date = (r.get("日付") or "").strip()
        gender = (r.get("性別") or "").strip()
        if not name or not dist or not mark:
            continue
        key = f"{name}|{dist}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        eid = f"sb-2026-{slug(name)}-{slug(dist)}"
        if eid in existing_ids:
            continue
        qs = [
            f"{name}の{dist}の自己ベストは？",
            f"{name}の{dist}SBは？",
            f"{name}の{dist}記録は？",
        ]
        ans = f"{name}（{aff}/{gender}）の2026年度・{dist}シーズンベスト（SB採用）は {mark} です。"
        if meet or date:
            ans += f" 大会: {meet}（{date}）。"
        out.append(
            entry(
                eid,
                qs,
                ans,
                ["input/idaten-corpus/drive-text/記録データベース/2026年度/中学生記録.csv"],
                ["sb", "athlete", gender, dist],
            )
        )
        if len(out) >= limit:
            break

    # School×distance fastest among SB
    by_school_dist: dict[tuple[str, str], list] = defaultdict(list)
    for r in prioritized:
        aff = (r.get("所属") or "").strip()
        dist = (r.get("距離") or "").strip()
        if not aff or not dist:
            continue
        school = re.sub(r"(中学校|中学|中)$", "", aff) or aff
        by_school_dist[(school, dist)].append(r)
    for (school, dist), group in sorted(by_school_dist.items()):
        try:
            best = min(group, key=lambda x: float(x.get("SB秒") or x.get("記録秒") or 1e9))
        except ValueError:
            continue
        eid = f"sb-school-{slug(school)}-{slug(dist)}-best"
        if eid in existing_ids or any(e["id"] == eid for e in out):
            continue
        name = best.get("名前")
        mark = best.get("記録")
        qs = [
            f"{school}の{dist}最速は誰？",
            f"{school}{dist}のトップは？",
            f"{school}で{dist}が一番速い選手は？",
        ]
        ans = f"{school}の{dist}最速（SB採用）は{name}の {mark} です。"
        out.append(
            entry(
                eid,
                qs,
                ans,
                ["input/idaten-corpus/drive-text/記録データベース/2026年度/中学生記録.csv"],
                ["sb", "school", dist],
            )
        )
        if len(out) >= limit:
            break
    return out[:limit]


def gen_course_pace(existing_ids: set[str]) -> list[dict]:
    out: list[dict] = []
    # Distance per leg facts
    men_legs = [
        (1, 3.00),
        (2, 2.855),
        (3, 3.00),
        (4, 3.00),
        (5, 2.855),
        (6, 3.00),
    ]
    women_legs = [
        (1, 3.00),
        (2, 1.855),
        (3, 2.00),
        (4, 2.00),
        (5, 3.00),
    ]
    for gender, legs in (("男子", men_legs), ("女子", women_legs)):
        for leg, km in legs:
            eid = f"aragyoku-distance-{gender}-leg{leg}"
            if eid in existing_ids:
                continue
            qs = [
                f"荒玉{gender}{leg}区の距離は？",
                f"荒玉駅伝{gender}の{leg}区は何km？",
                f"{gender}{leg}区の距離を教えて",
            ]
            ans = (
                f"荒玉駅伝{gender}・現行の{leg}区は {km}km です。"
                + ("（男子は2024年以降の定義）" if gender == "男子" else "（女子は全年度共通）")
            )
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [
                        "docs/aragyoku-ekiden-distance-definitions.md",
                        "out/analysis/aragyoku-overview.md",
                    ],
                    ["aragyoku", "distance", gender],
                )
            )
            # Pace examples: 3:30/km, 4:00/km
            for pace_label, sec_per_km in (("3分30秒", 210), ("4分00秒", 240), ("3分45秒", 225)):
                eid2 = f"aragyoku-pace-{gender}-leg{leg}-{slug(pace_label)}"
                if eid2 in existing_ids:
                    continue
                total_sec = int(round(km * sec_per_km))
                mm, ss = divmod(total_sec, 60)
                qs2 = [
                    f"荒玉{gender}{leg}区を{pace_label}/kmで走ると何分？",
                    f"{gender}{leg}区{pace_label}ペースのタイムは？",
                ]
                ans2 = (
                    f"荒玉{gender}{leg}区（{km}km）を{pace_label}/kmで走ると、"
                    f"およそ {mm}:{ss:02d} です。"
                )
                out.append(
                    entry(
                        eid2,
                        qs2,
                        ans2,
                        ["docs/aragyoku-ekiden-distance-definitions.md"],
                        ["aragyoku", "pace", gender],
                    )
                )
    # Course points paraphrases
    extras = [
        (
            "course-loop-4855",
            ["荒玉の1周は何キロ？", "荒玉コース1周の距離は？", "共通ポイントの1周距離は？"],
            "荒玉駅伝の男女共通ポイントの1周は 4.855km です。",
            ["input/aragyoku/course-points.md"],
            ["aragyoku", "course"],
        ),
        (
            "course-men-start-145",
            ["男子スタートはどこから？", "荒玉男子のスタート位置は？", "Cの手前何m？"],
            "荒玉男子のスタートは共通ポイントCの 145m 手前です。",
            ["input/aragyoku/course-points.md"],
            ["aragyoku", "course"],
        ),
        (
            "course-bridge-1km",
            ["橋の上の1km地点はどこ？", "女子1区の1km地点は？", "荒玉の1km地点は橋の上？"],
            "荒玉駅伝の女子1区1km地点は橋の上です（男女共通ポイントの一部）。",
            ["input/aragyoku/course-points.md"],
            ["aragyoku", "course"],
        ),
        (
            "course-points-order",
            ["荒玉のポイント進行順は？", "D E A B C の順番は？", "共通ポイントの順番は？"],
            "荒玉駅伝の共通ポイント進行順は D → 1km（橋） → E → A → B → C → D です。",
            ["input/aragyoku/course-points.md"],
            ["aragyoku", "course"],
        ),
    ]
    for eid, qs, ans, srcs, tags in extras:
        if eid in existing_ids:
            continue
        out.append(entry(eid, qs, ans, srcs, tags))
    return out


def gen_meta_paraphrases(existing_ids: set[str]) -> list[dict]:
    """High-frequency meta / ops / clarify variants not in the first 100."""
    seeds = [
        (
            "help-what-can-ask",
            ["何が聞ける？", "どんな質問ができる？", "このボットで聞けることは？"],
            "いだてん岱明のカレンダー・練習・荒玉/ジュニア/なごみの結果・コース図/動画・自己ベストなどを質問できます。雑談や他競技は対象外です。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["meta", "help"],
        ),
        (
            "help-how-to-ask-result",
            ["結果の聞き方は？", "大会結果を聞くには？", "成績はどう聞けばいい？"],
            "「大会名＋年＋男女＋結果」が確実です。例: 「2025年荒玉男子の岱明は何位？」「ジュニア駅伝の結果PDFは？」",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["meta", "help"],
        ),
        (
            "relative-year-kotoshi",
            ["今年って何年扱い？", "今年は西暦何年？", "相対年の基準は？"],
            "「今年」「去年」は質問時点の既定年度（通常は年度の西暦）に展開して解釈します。曖昧なときは年を付けて聞いてください。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["meta", "clarify"],
        ),
        (
            "scope-refuse-chat",
            ["天気の雑談して", "他のスポーツの話して", "仮想通貨どう？"],
            "このボットはいだてん岱明の陸上・駅伝・練習・カレンダーに関する質問向けです。対象外の話題はお答えできません。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["meta", "scope"],
        ),
        (
            "pdf-how-to-open",
            ["PDFの開き方は？", "Driveのリンクが開けない", "成績表URLの見方は？"],
            "回答中の Google ドライブ URL をタップすると成績表や資料が開きます。開けない場合は権限やネット接続を確認し、コーチに連絡してください。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["meta", "pdf"],
        ),
        (
            "junior-vs-aragyoku",
            ["ジュニアと荒玉の違いは？", "県ジュニアと荒玉は同じ？", "荒玉はジュニア？"],
            "荒玉（玉名荒尾中体連駅伝）と県ジュニア駅伝は別大会です。質問では大会名を区別してください。",
            ["input/events.2026.yaml", "out/analysis/aragyoku-overview.md"],
            ["junior", "aragyoku", "meta"],
        ),
        (
            "nagomi-vs-kanaguri",
            ["なごみと金栗は同じ？", "金栗駅伝となごみの違いは？", "なごみ大会って金栗？"],
            "「中学駅伝金栗四三生誕の地なごみ大会」はなごみ駅伝として扱います。別の「金栗駅伝」「金栗記念」などと混同しないでください。",
            ["input/events.2026.yaml"],
            ["nagomi", "meta"],
        ),
        (
            "daiming-practice-tag",
            ["いだてん岱明練習って何？", "practice:daiming とは？", "岱明の練習予定の印は？"],
            "カレンダー上のいだてん岱明練習（practice:daiming）は、岱明関連の練習セッション予定です。日時はカレンダー質問で確認できます。",
            ["input/events.2026.yaml", "input/idaten-corpus/calendar/events.daiming.yaml"],
            ["practice", "calendar"],
        ),
        (
            "ask-with-year-gender",
            ["聞き方のコツは？", "うまく答えさせる聞き方は？", "質問のコツは？"],
            "年・男女・大会名・学校名を入れると定型回答に当たりやすいです。例: 「2025年荒玉女子の南関は何位？」「角田亜美の1500mSBは？」",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["meta", "help"],
        ),
        (
            "prepared-vs-rag",
            ["定型回答とAI回答の違いは？", "用意された答えってある？", "ナレッジ回答とは？"],
            "想定質問は定型回答（Prepared Q&A）を優先します。ヒットしないときだけ検索＋生成で答えます。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["meta"],
        ),
        (
            "source-paths-meaning",
            ["sourcesって何？", "根拠パスとは？", "回答の出典はどこ？"],
            "定型回答には根拠ファイルパス（events YAML、成績JSON、Driveコーパス等）が付きます。詳細はそれらのファイルを参照してください。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["meta"],
        ),
        (
            "line-image-course",
            ["コース図は画像で来る？", "LINEでコース画像は届く？", "図はメッセージで見られる？"],
            "コース図・コース動画の質問では、動的回答や定型回答で Drive リンク／画像案内を返します。動画・画像の専用質問が確実です。",
            ["input/aragyoku/course-points.md", "input/aragyoku/course-videos.md"],
            ["aragyoku", "course", "meta"],
        ),
        (
            "update-frequency",
            ["データはいつ更新される？", "成績の更新タイミングは？", "新しい結果はすぐ入る？"],
            "大会結果やカレンダーはリポジトリへの取り込み後に反映されます。直前の大会が無い場合はコーチ確認か、成績表PDFリンクを確認してください。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["meta", "ops"],
        ),
        (
            "who-is-daiming",
            ["岱明ってどのチーム？", "いだてん岱明とは？", "岱明中の陸上は？"],
            "岱明は玉名市の中学校チーム（いだてん岱明）です。荒玉・ジュニア・なごみなど地区/県大会の結果や練習予定をこのボットで確認できます。",
            ["out/analysis/aragyoku-overview.md", "input/events.2026.yaml"],
            ["daiming", "meta"],
        ),
        (
            "men-women-legs-count",
            ["荒玉は男女何区間？", "男子と女子の区間数は？", "何区まである？"],
            "荒玉駅伝は男子6区間、女子5区間です。距離定義は年度（特に男子2024年再編）で変わるので、距離質問は男女を指定してください。",
            ["out/analysis/aragyoku-overview.md", "docs/aragyoku-ekiden-distance-definitions.md"],
            ["aragyoku", "distance", "meta"],
        ),
        (
            "sb-how-to-ask",
            ["自己ベストの聞き方は？", "SBを聞くには？", "記録の質問例は？"],
            "「選手名＋距離＋自己ベスト/SB」が確実です。例: 「松野の1500mSBは？」「南関の3000m最速は誰？」",
            ["input/idaten-corpus/drive-text/記録データベース/2026年度/中学生記録.csv"],
            ["sb", "help"],
        ),
        (
            "calendar-how-to-ask",
            ["予定の聞き方は？", "カレンダー質問の例は？", "日程を聞くには？"],
            "大会名や日付を入れて聞いてください。例: 「荒玉中体連駅伝はいつ？」「2026-10-14の予定は？」",
            ["input/events.2026.yaml"],
            ["calendar", "help"],
        ),
        (
            "ambiguous-fallback",
            ["曖昧なときはどうなる？", "似た質問が複数あると？", "答えが定まらないときは？"],
            "似た定型回答が僅差のときは無理に当てず、検索ベースの回答に回します。年・男女・学校名を足すと定型ヒットしやすくなります。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["meta", "clarify"],
        ),
        (
            "coach-when",
            ["コーチに聞くべきことは？", "ボットで分からないときは？", "最終確認は誰に？"],
            "直前のオーダー変更・欠席判断・未取り込みの結果など、リポジトリに無い最新判断はコーチに確認してください。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["meta", "ops"],
        ),
    ]
    out = []
    for eid, qs, ans, srcs, tags in seeds:
        if eid in existing_ids:
            continue
        out.append(entry(eid, qs, ans, srcs, tags))
    return out


def gen_meet_results_index(existing_ids: set[str], limit: int) -> list[dict]:
    """Index notable meet folders under drive-text/大会."""
    root = ROOT / "input" / "idaten-corpus" / "drive-text" / "大会"
    out: list[dict] = []
    if not root.exists():
        return out
    drive_map = load_drive_meet_folder_map()
    for year_dir in sorted(root.iterdir()):
        if not year_dir.is_dir():
            continue
        year = year_dir.name.replace("年度", "")
        for meet_dir in sorted(year_dir.iterdir()):
            if not meet_dir.is_dir():
                continue
            name = meet_dir.name
            # strip leading date prefix like 0926_
            title = re.sub(r"^\d{4}[-_]?", "", name)
            title = re.sub(r"^\d{2,4}_", "", title)
            eid = f"meet-folder-{slug(year)}-{slug(title)[:40]}"
            if eid in existing_ids:
                continue
            rel = str(meet_dir.relative_to(ROOT))
            if str(year).startswith("2026"):
                qs = [
                    f"{title}の資料はどこ？",
                    f"{title}の結果フォルダは？",
                    f"{year}の{title}について",
                ]
            else:
                qs = [
                    f"{year}年{title}の資料はどこ？",
                    f"{year}年{title}の結果フォルダは？",
                    f"{year}の{title}について",
                ]
            drive_url = resolve_drive_meet_url(name, title, drive_map)
            ans = friendly_meet_folder_answer(title, str(year), name, drive_url)
            sources = [rel]
            idx_path = "input/external/drive/shared/大会/INDEX.md"
            if drive_url:
                sources.append(idx_path)
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    sources,
                    ["meet", "result", year],
                )
            )
            if len(out) >= limit:
                return out
    return out


def gen_practice_notes(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    roots = [
        ROOT / "input" / "idaten-corpus" / "drive-text" / "練習",
        ROOT / "input" / "idaten-corpus" / "drive-text" / "personal",
    ]
    patterns = ("*.md", "*.txt", "*.csv")
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for pat in patterns:
            files.extend(root.rglob(pat))
    for p in sorted(files)[:400]:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            continue
        title = lines[0].lstrip("# ").strip()[:60] or p.stem
        if len(title) < 2:
            continue
        eid = f"practice-doc-{slug(p.stem)[:40]}"
        if eid in existing_ids or any(e["id"] == eid for e in out):
            continue
        snippet = " ".join(lines[1:6])[:240]
        qs = [
            f"{title}の内容は？",
            f"{title}について教えて",
            f"練習資料「{title}」は？",
        ]
        ans = f"練習資料「{title}」: {snippet or '（本文先頭を参照）'}"
        out.append(
            entry(
                eid,
                qs,
                ans,
                [str(p.relative_to(ROOT))],
                ["practice"],
            )
        )
        if len(out) >= limit:
            break
    # Also surface daiming calendar practice titles
    cal = ROOT / "input" / "idaten-corpus" / "calendar" / "events.daiming.yaml"
    if cal.exists() and len(out) < limit:
        data = yaml.safe_load(cal.read_text(encoding="utf-8"))
        for ev in data.get("events") or []:
            title = (ev.get("title") or "").strip()
            date = ev.get("date")
            if not title or not date:
                continue
            if "練習" not in title and "practice:daiming" not in (ev.get("tags") or []):
                continue
            eid = f"practice-cal-{str(date).replace('-', '')}-{slug(title)[:24]}"
            if eid in existing_ids or any(e["id"] == eid for e in out):
                continue
            qs = [
                f"{date}の練習は？",
                f"{date}の{title}は？",
                f"{title}（{date}）について",
            ]
            desc = (ev.get("description") or "").strip()
            parts = [f"{date} の予定「{title}」です。"]
            status_phrase = friendly_status_phrase(str(ev.get("status") or ""))
            if status_phrase:
                parts.append(status_phrase)
            summary = clean_user_facing_text(desc, max_len=180)
            if summary:
                parts.append(summary if summary.endswith("。") else summary + "。")
            ans = " ".join(parts)
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    ["input/idaten-corpus/calendar/events.daiming.yaml"],
                    ["practice", "calendar"],
                )
            )
            if len(out) >= limit:
                break
    return out


def gen_analysis_docs(existing_ids: set[str], limit: int) -> list[dict]:
    root = ROOT / "out" / "analysis"
    out: list[dict] = []
    if not root.exists():
        return out
    for p in sorted(root.glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            continue
        title = lines[0].lstrip("# ").strip()[:70]
        eid = f"analysis-{slug(p.stem)[:48]}"
        if eid in existing_ids:
            continue
        snippet = " ".join(lines[1:8])[:260]
        qs = [
            f"{title}の要点は？",
            f"{p.stem}について教えて",
            f"分析「{title}」は？",
        ]
        ans = f"分析ドキュメント「{title}」: {snippet}"
        out.append(
            entry(
                eid,
                qs,
                ans,
                [str(p.relative_to(ROOT))],
                ["analysis", "aragyoku"],
            )
        )
        if len(out) >= limit:
            break
    return out


def gen_quiz(existing_ids: set[str], limit: int) -> list[dict]:
    quiz = ROOT / "input" / "idaten-corpus" / "aragyoku" / "quiz" / "荒玉駅伝○×クイズ.csv"
    out: list[dict] = []
    if not quiz.exists():
        return out
    # try utf-8 then cp932
    for enc in ("utf-8", "cp932"):
        try:
            rows = list(csv.DictReader(quiz.open(encoding=enc)))
            break
        except Exception:
            rows = []
    if not rows:
        return out
    keys = rows[0].keys()
    # heuristic columns
    qkey = next((k for k in keys if "問" in k or "question" in k.lower() or "問題" in k), None)
    akey = next((k for k in keys if "答" in k or "answer" in k.lower() or "正解" in k), None)
    if not qkey:
        # fall back to first two cols
        cols = list(keys)
        qkey, akey = cols[0], cols[1] if len(cols) > 1 else cols[0]
    for i, r in enumerate(rows[:limit], 1):
        q = (r.get(qkey) or "").strip()
        a = (r.get(akey) or "").strip() if akey else ""
        if not q:
            continue
        eid = f"quiz-aragyoku-{i:03d}"
        if eid in existing_ids:
            continue
        ans = f"○×クイズ: {q} → 正解: {a}" if a else f"○×クイズ問題: {q}"
        out.append(
            entry(
                eid,
                [q, f"クイズ: {q}", f"荒玉クイズ {i}問目"],
                ans,
                ["input/idaten-corpus/aragyoku/quiz/荒玉駅伝○×クイズ.csv"],
                ["aragyoku", "quiz"],
            )
        )
    return out


def take(bucket: list[dict], n: int, used: set[str]) -> list[dict]:
    out = []
    for e in bucket:
        if e["id"] in used:
            continue
        used.add(e["id"])
        out.append(e)
        if len(out) >= n:
            break
    return out


def build_new_1000(base_entries: list[dict]) -> list[dict]:
    existing_ids = {e["id"] for e in base_entries}
    used = set(existing_ids)

    buckets = {
        "winners": gen_aragyoku_winners(existing_ids),
        "team_ranks": gen_aragyoku_team_ranks(existing_ids, 400),
        "legs": gen_aragyoku_legs(existing_ids, 800),
        "calendar": gen_calendar(existing_ids, 400),
        "sb": gen_sb(existing_ids, 400),
        "course": gen_course_pace(existing_ids),
        "meta": gen_meta_paraphrases(existing_ids),
        "meets": gen_meet_results_index(existing_ids, 120),
        "practice": gen_practice_notes(existing_ids, 120),
        "analysis": gen_analysis_docs(existing_ids, 80),
        "quiz": gen_quiz(existing_ids, 80),
    }
    for k, v in buckets.items():
        print(f"  bucket {k}: {len(v)}")

    # Quotas summing to 1000 (adjust if short)
    quotas = [
        ("winners", 54),
        ("team_ranks", 160),
        ("legs", 180),
        ("calendar", 180),
        ("sb", 200),
        ("course", 60),
        ("meta", 20),
        ("meets", 40),
        ("practice", 50),
        ("analysis", 30),
        ("quiz", 26),
    ]
    selected: list[dict] = []
    for name, n in quotas:
        got = take(buckets[name], n, used)
        selected.extend(got)
        print(f"  took {name}: {len(got)}/{n}")

    if len(selected) < 1000:
        # fill from remaining in priority order
        for name, _ in quotas:
            if len(selected) >= 1000:
                break
            need = 1000 - len(selected)
            selected.extend(take(buckets[name], need, used))
    # still short? pull more legs/team/sb
    if len(selected) < 1000:
        for name in ("legs", "team_ranks", "sb", "calendar", "meets"):
            if len(selected) >= 1000:
                break
            selected.extend(take(buckets[name], 1000 - len(selected), used))

    selected = selected[:1000]
    print(f"  FINAL new: {len(selected)}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = data.get("entries") or []
    base = entries[:100]
    if len(base) < 100:
        raise SystemExit(f"expected at least 100 base entries, got {len(base)}")
    print(f"base entries: {len(base)}")

    new_entries = build_new_1000(base)
    if len(new_entries) != 1000:
        raise SystemExit(f"expected 1000 new entries, got {len(new_entries)}")

    all_entries = base + new_entries
    # uniqueness
    ids = [e["id"] for e in all_entries]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate ids in final set")

    payload = {
        "version": 1,
        "total": len(all_entries),
        "note": (
            "想定質問への定型回答（ADR 059）。初版100 + 追加1000（多様化: 荒玉結果/区間・"
            "カレンダー・SB・コース/ペース・大会資料・メタ）。\n"
            "ヒット時は本文をほぼそのまま返す。未ヒット時のみ RAG/LLM。\n"
        ),
        "entries": all_entries,
    }
    if args.dry_run:
        print("dry-run OK", payload["total"])
        return 0

    # Dump with stable YAML style
    FAQ.write_text(
        yaml.dump(
            payload,
            allow_unicode=True,
            sort_keys=False,
            width=100,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {FAQ.relative_to(ROOT)} total {len(all_entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
