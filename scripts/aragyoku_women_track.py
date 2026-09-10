#!/usr/bin/env python3
"""荒玉女子駅伝 上位4校 × トラックSB/直近 突合。

データソース:
- input/aragyoku/women_top4_2012_2025.json（Drive結果ボードOCR）
- input/external/sb/middle-school/wide/中学生SB.csv
- input/external/sb/middle-school/by-year/{2012..2026}-sb-adopted.json
- input/external/drive/personal/t-tsuchiyama/sb/output_reg_中学生_女子.csv
"""

from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOP4_JSON = ROOT / "input/aragyoku/women_top4_2012_2025.json"
WIDE_SB = ROOT / "input/external/sb/middle-school/wide/中学生SB.csv"
OUTPUT_REG = ROOT / "input/external/drive/personal/t-tsuchiyama/sb/output_reg_中学生_女子.csv"
BY_YEAR_DIR = ROOT / "input/external/sb/middle-school/by-year"
NOTION_DBS = [
    (ROOT / "input/external/notion/databases/2024年度中学生/rows.json", "2024", "legacy"),
    (ROOT / "input/external/notion/databases/2025年度中学生記録/rows.json", "2025", "legacy"),
    (ROOT / "input/external/notion/databases/2026年度中学生記録/rows.json", "2026", "modern"),
]
OUT_JSON = ROOT / "out/analysis/aragyoku_women_track_joined.json"
OUT_CSV = ROOT / "out/analysis/aragyoku_women_track_joined.csv"

TRACK_EVENTS = ("800m", "1500m", "3000m")
TRUE_VALUES = {"1", "true", "yes", "y", "__yes__"}
NON_RESULT_MARKS = {"DNS", "DNF", "DQ"}
MAX_TRACK_SECONDS = 24 * 60 * 60
SCHOOL_ALIASES = {
    "荒尾第三": "荒尾三",
    "荒尾第四": "荒尾四",
}
# 荒玉中体連女子駅伝 上位4校で登場する中学校（他校所属の記録はクラブ扱いにしない）
ARAGYOKU_SCHOOLS = frozenset(
    {"南関", "岱明", "玉名", "玉東", "腹栄", "荒尾三", "荒尾四", "荒尾海陽", "菊水", "長洲"}
)

def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    return s.replace("\u3000", "").replace(" ", "").replace("　", "")


def norm_school(s: str) -> str:
    value = norm_name(s)
    value = re.sub(r"\([^)]*\)", "", value)
    # Notion 由来の「ﾀﾏﾅﾁｭｳ玉名中」→「玉名」など、先頭カタカナ接頭辞を除去
    value = re.sub(r"^[ァ-ヶー・]+", "", value)
    for suffix in ("中学校", "中"):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
            break
    return SCHOOL_ALIASES.get(value, value)


def parse_time_to_seconds(raw: str | None) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s in {"-", "—", "―", "DNS", "DNF", "DQ"}:
        return None
    s = s.replace("'", ":").replace("’", ":").replace("″", "").replace('"', "")
    if re.fullmatch(r"\d+(\.\d+)?", s):
        value = float(s)
        return value if 0 < value <= MAX_TRACK_SECONDS and math.isfinite(value) else None
    m = re.fullmatch(r"(\d+):(\d{2})(?:\.(\d+))?", s)
    if m:
        mins, secs, frac = m.group(1), m.group(2), m.group(3) or "0"
        if int(secs) >= 60:
            return None
        value = int(mins) * 60 + int(secs) + float(f"0.{frac}")
        return value if 0 < value <= MAX_TRACK_SECONDS else None
    m = re.fullmatch(r"(\d+):(\d{2}):(\d{2})(?:\.(\d+))?", s)
    if m:
        h, mins, secs, frac = m.group(1), m.group(2), m.group(3), m.group(4) or "0"
        if int(mins) >= 60 or int(secs) >= 60:
            return None
        value = int(h) * 3600 + int(mins) * 60 + int(secs) + float(f"0.{frac}")
        return value if 0 < value <= MAX_TRACK_SECONDS else None
    return None


def format_seconds(sec: float | None) -> str | None:
    if sec is None or not math.isfinite(sec) or not 0 < sec <= MAX_TRACK_SECONDS:
        return None
    mins = int(sec // 60)
    rem = sec - mins * 60
    if rem == int(rem):
        return f"{mins}:{int(rem):02d}"
    return f"{mins}:{rem:05.2f}"


def validate_record_seconds(mark: str, raw_seconds: Any, context: str) -> float:
    parsed = parse_time_to_seconds(mark) if mark else None
    if mark and parsed is None:
        raise ValueError(f"invalid track mark in {context}: {mark!r}")
    if raw_seconds in (None, ""):
        if parsed is None:
            raise ValueError(f"track mark and seconds are missing in {context}")
        return parsed
    try:
        seconds = float(raw_seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid track seconds in {context}: {raw_seconds!r}") from exc
    if not math.isfinite(seconds) or not 0 < seconds <= MAX_TRACK_SECONDS:
        raise ValueError(f"invalid track seconds in {context}: {raw_seconds!r}")
    if parsed is not None and abs(parsed - seconds) > 0.01:
        raise ValueError(
            f"track mark/seconds mismatch in {context}: {mark!r} != {raw_seconds!r}"
        )
    return seconds


def school_overlap(a: str, b: str) -> bool:
    a_n = norm_school(a)
    b_n = norm_school(b)
    if not a_n or not b_n:
        return False
    return a_n == b_n


def is_aragyoku_school_affiliation(affiliation: str) -> bool:
    """荒玉エリアの中学校所属か（他校の記録をクラブ扱いで混ぜないため）。"""
    aff = norm_school(affiliation)
    if not aff:
        return False
    return any(school_overlap(school, aff) for school in ARAGYOKU_SCHOOLS)


def is_club_affiliation(affiliation: str, ekiden_school: str) -> bool:
    """駅伝校以外のクラブ・プロジェクト所属か（ATRC, NJAC, 長洲JRC 等）。"""
    if school_overlap(ekiden_school, affiliation):
        return False
    return not is_aragyoku_school_affiliation(affiliation)


def parse_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    return str(value or "").strip().lower() in TRUE_VALUES


def _grade_number(value: Any) -> int | None:
    try:
        grade = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return grade if 1 <= grade <= 3 else None


def filter_records_for_athlete(
    records: list[dict[str, Any]], year: int, school: str, grade: Any
) -> list[dict[str, Any]]:
    """同名別人を除外し、同一暦年の本人と裏付けられる記録だけを返す。"""
    season = str(year)
    same_year = [r for r in records if str(r.get("season") or "") == season]
    athlete_grade = _grade_number(grade)

    if athlete_grade is not None:
        projected_grades: set[int] = set()
        for record in records:
            source_grade = _grade_number(record.get("grade"))
            try:
                source_year = int(str(record.get("season") or ""))
            except ValueError:
                continue
            if source_grade is None:
                continue
            projected = source_grade + year - source_year
            if 1 <= projected <= 3:
                projected_grades.add(projected)

        if projected_grades and athlete_grade not in projected_grades:
            return []
        if len(projected_grades) > 1:
            same_year = [
                r for r in same_year if _grade_number(r.get("grade")) == athlete_grade
            ]
        else:
            same_year = [
                r
                for r in same_year
                if _grade_number(r.get("grade")) in (None, athlete_grade)
            ]

    school_matches = [
        r for r in same_year if school_overlap(school, str(r.get("school") or ""))
    ]
    club_matches = [
        r
        for r in same_year
        if is_club_affiliation(str(r.get("school") or ""), school)
    ]
    seen: set[tuple[Any, ...]] = set()
    merged: list[dict[str, Any]] = []
    for record in school_matches + club_matches:
        key = (
            record.get("source"),
            record.get("season"),
            record.get("school"),
            record.get("event"),
            record.get("mark"),
            record.get("meet_date"),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(record)
    return merged


def seasons_for_ekiden_year(year: int) -> list[str]:
    """駅伝と同じ年度ファイルのトラック記録だけを参照する。"""
    return [str(year)]


def load_wide_like_csv(
    path: Path, source: str, season: str
) -> dict[str, list[dict[str, Any]]]:
    by_name: dict[str, list[dict[str, Any]]] = {}
    if not path.exists():
        raise FileNotFoundError(f"required track source is missing: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "女" not in (row.get("性別") or ""):
                continue
            name = norm_name(row.get("名前") or "")
            if not name:
                continue
            school = (row.get("所属") or "").strip()
            for event in TRACK_EVENTS:
                mark = (row.get(f"{event}SB") or "").strip()
                if not mark:
                    continue
                sec = parse_time_to_seconds(mark)
                if sec is None:
                    raise ValueError(f"invalid track mark in {path}: {name} {event}={mark!r}")
                url = (row.get(f"{event}SB参考") or "").strip() or None
                by_name.setdefault(name, []).append(
                    {
                        "source": source,
                        "season": season,
                        "school": school,
                        "grade": "",
                        "event": event,
                        "mark": mark,
                        "seconds": sec,
                        "meet": None,
                        "meet_date": None,
                        "url": url,
                        "is_sb": True,
                        "is_aggregate": True,
                    }
                )
    return by_name


def _preferred_url(*candidates: str | None) -> str | None:
    urls = [c.strip() for c in candidates if c and str(c).strip()]
    for u in urls:
        if u.startswith("http") and "notion.so" not in u and "notion.com" not in u:
            return u
    return urls[0] if urls else None


def load_by_year_json(directory: Path = BY_YEAR_DIR) -> dict[str, list[dict[str, Any]]]:
    by_name: dict[str, list[dict[str, Any]]] = {}
    paths = [directory / f"{year}-sb-adopted.json" for year in range(2012, 2027)]
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "required track sources are missing: " + ", ".join(str(path) for path in missing)
        )
    for path in paths:
        season = path.name.split("-")[0]
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid track JSON: {path}") from exc
        if not isinstance(rows, list):
            raise ValueError(f"track JSON must contain a list: {path}")
        for row in rows:
            if row.get("性別") != "女子" or row.get("カテゴリー") != "中学生":
                continue
            event = (row.get("距離") or "").strip()
            if event not in TRACK_EVENTS:
                continue
            name = norm_name(row.get("名前") or "")
            if not name:
                continue
            mark = (row.get("記録") or "").strip()
            sec = validate_record_seconds(
                mark,
                row.get("記録秒"),
                f"{path}: {name} {event}",
            )
            url = _preferred_url(row.get("参考"), row.get("url"))
            by_name.setdefault(name, []).append(
                {
                    "source": f"by_year_{season}",
                    "season": season,
                    "school": (row.get("所属") or "").strip(),
                    "grade": str(row.get("学年") or "").strip(),
                    "event": event,
                    "mark": mark or format_seconds(sec) or "",
                    "seconds": sec,
                    "meet": (row.get("大会名") or "").strip() or None,
                    "meet_date": (row.get("日付") or "").strip() or None,
                    "url": url,
                    "is_sb": parse_truthy(row.get("SB採用")),
                    "is_aggregate": True,
                }
            )
    return by_name


def load_notion_rows(
    databases: list[tuple[Path, str, str]] = NOTION_DBS,
) -> dict[str, list[dict[str, Any]]]:
    by_name: dict[str, list[dict[str, Any]]] = {}
    for path, season, kind in databases:
        if not path.exists():
            raise FileNotFoundError(f"required track source is missing: {path}")
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid track JSON: {path}") from exc
        if not isinstance(rows, list):
            raise ValueError(f"track JSON must contain a list: {path}")
        for row in rows:
            if kind == "modern":
                if row.get("gender") != "女子":
                    continue
                event = (row.get("distance") or "").strip()
                if event not in TRACK_EVENTS:
                    continue
                name = norm_name(row.get("name") or "")
                mark = (row.get("time_text") or "").strip()
                if mark in NON_RESULT_MARKS:
                    continue
                sec = validate_record_seconds(
                    mark,
                    row.get("record_seconds"),
                    f"{path}: {name} {event}",
                )
                school = (row.get("affiliation") or "").strip()
                grade = row.get("grade") or ""
                meet_date = (row.get("date") or "").strip() or None
                url = _preferred_url(row.get("url"))
                is_sb = parse_truthy(row.get("sb_adopted"))
                meet = None
            else:
                if row.get("性別") != "女子":
                    continue
                event = (row.get("距離") or "").strip()
                if event not in TRACK_EVENTS:
                    continue
                name = norm_name(row.get("名前") or "")
                mark = (row.get("記録") or "").strip()
                if mark in NON_RESULT_MARKS:
                    continue
                sec = validate_record_seconds(
                    mark,
                    row.get("記録秒"),
                    f"{path}: {name} {event}",
                )
                school = (row.get("所属") or "").strip()
                grade = row.get("学年") or ""
                meet_date = (row.get("日付") or "").strip() or None
                url = _preferred_url(row.get("参考"), row.get("url"))
                is_sb = parse_truthy(row.get("SB採用"))
                meet = (row.get("大会名") or "").strip() or None
            if not name:
                continue
            by_name.setdefault(name, []).append(
                {
                    "source": f"notion_{season}",
                    "season": season,
                    "school": school,
                    "grade": str(grade) if grade not in (None, "") else "",
                    "event": event,
                    "mark": mark or format_seconds(sec) or "",
                    "seconds": sec,
                    "meet": meet,
                    "meet_date": meet_date,
                    "url": url,
                    "is_sb": is_sb,
                    "is_aggregate": False,
                }
            )
    return by_name


def merge_records(*sources: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for src in sources:
        for name, recs in src.items():
            out.setdefault(name, []).extend(recs)
    return out


def pick_sb(records: list[dict[str, Any]], seasons: list[str], event: str) -> dict[str, Any] | None:
    for season in seasons:
        cands = [
            r
            for r in records
            if r.get("event") == event and (r.get("season") or "") == season
            and r.get("is_sb") is True
        ]
        if cands:
            csv_cands = [
                record
                for record in cands
                if str(record.get("source") or "").startswith("by_year_")
            ]
            if csv_cands:
                cands = csv_cands
            return min(cands, key=lambda r: r["seconds"])
    return None


def pick_recent(records: list[dict[str, Any]], seasons: list[str], event: str) -> dict[str, Any] | None:
    for season in seasons:
        cands = [
            r
            for r in records
            if r.get("event") == event
            and (r.get("season") or "") == season
            and not r.get("is_aggregate")
        ]
        dated = [r for r in cands if r.get("meet_date")]
        if dated:
            return max(dated, key=lambda r: r.get("meet_date") or "")
        if cands:
            return min(cands, key=lambda r: r["seconds"])
    return None


def pack_mark(rec: dict[str, Any] | None) -> dict[str, Any] | None:
    if not rec:
        return None
    return {
        "mark": rec["mark"],
        "seconds": rec["seconds"],
        "meet": rec.get("meet"),
        "meet_date": rec.get("meet_date"),
        "url": rec.get("url"),
        "season": rec.get("season") or None,
        "source": rec.get("source"),
        "school": rec.get("school") or None,
        "grade": rec.get("grade") or None,
    }


def build_joined() -> dict[str, Any]:
    top4 = json.loads(TOP4_JSON.read_text(encoding="utf-8"))
    # ワイドSBは2025年度、output_regは2026年度のスナップショット。
    # 年度を持たない形式なので、他年度へのフォールバックには使わない。
    wide = load_wide_like_csv(WIDE_SB, "wide_sb", "2025")
    oreg = load_wide_like_csv(OUTPUT_REG, "output_reg", "2026")
    by_year = load_by_year_json()
    notion = load_notion_rows()
    all_recs = merge_records(wide, oreg, by_year, notion)

    years_out: list[dict[str, Any]] = []
    stats = {"athletes": 0, "with_any_track": 0, "with_sb": 0, "with_url": 0}

    year_keys = sorted((top4.get("years") or {}).keys(), reverse=True)
    if not year_keys:
        raise ValueError("ekiden source has no year data")
    for ykey in year_keys:
        yblock = top4["years"][ykey]
        year = int(ykey)
        seasons = seasons_for_ekiden_year(year)
        teams_out = []
        for team in yblock.get("teams") or []:
            athletes_out = []
            school = team.get("team") or team.get("school") or ""
            for ath in team.get("legs") or team.get("athletes") or []:
                stats["athletes"] += 1
                name = ath["name"]
                nn = norm_name(name)
                recs = filter_records_for_athlete(
                    list(all_recs.get(nn, [])), year, school, ath.get("grade")
                )

                events_payload: dict[str, Any] = {}
                has_sb = False
                has_url = False
                for event in TRACK_EVENTS:
                    sb = pick_sb(recs, seasons, event)
                    recent = pick_recent(recs, seasons, event)
                    if not sb and not recent:
                        continue
                    # SB と recent が同一なら recent は省略せず明示
                    events_payload[event] = {
                        "sb": pack_mark(sb),
                        "recent": pack_mark(recent),
                    }
                    if sb:
                        has_sb = True
                        if sb.get("url"):
                            has_url = True
                    if recent and recent.get("url"):
                        has_url = True

                if events_payload:
                    stats["with_any_track"] += 1
                if has_sb:
                    stats["with_sb"] += 1
                if has_url:
                    stats["with_url"] += 1

                ekiden_mark = ath.get("split") or ath.get("mark")
                athletes_out.append(
                    {
                        "leg": ath["leg"],
                        "name": name,
                        "grade": ath.get("grade"),
                        "ekiden_mark": ekiden_mark,
                        "ekiden_seconds": parse_time_to_seconds(ekiden_mark),
                        "cumulative": ath.get("cumulative"),
                        "track_events": events_payload,
                        "match_count": len(recs),
                    }
                )
            teams_out.append(
                {
                    "rank": team["rank"],
                    "school": school,
                    "total_mark": team.get("total") or team.get("total_mark"),
                    "total_seconds": parse_time_to_seconds(team.get("total") or team.get("total_mark")),
                    "athletes": athletes_out,
                }
            )
        years_out.append(
            {
                "year": year,
                "sb_seasons": [s for s in seasons if s],
                "date": yblock.get("date"),
                "venue": yblock.get("venue"),
                "source_file_id": yblock.get("source_drive_id") or yblock.get("source_file_id"),
                "source_confidence": yblock.get("confidence")
                or yblock.get("source_confidence"),
                "teams": teams_out,
            }
        )

    if stats["athletes"] == 0:
        raise ValueError("ekiden source has no athlete rows")

    return {
        "meta": {
            "title": "荒玉（玉名荒尾）中体連駅伝・女子・上位4校 トラック走力突合",
            "years": [y["year"] for y in years_out],
            "missing_years": top4.get("missing_years") or top4.get("meta", {}).get("missing_years") or [2014],
            "verification": top4.get("meta", {}).get("verification") or {},
            "stats": stats,
            "guide_note": (
                "「駅伝」は大会当日の区間走結果（道路コース）です。女子は1〜5区がそれぞれ"
                "約3.0km・1.855km・2.0km・2.0km・3.0kmで、トラック種目（800m/1500m/3000m）"
                "とは距離・路面・気象・タスキ条件が異なります。トラックSB/直近は同年の走力指標として"
                "並記していますが、短い種目が強い選手ほど長い区間では相対的に伸び、逆も起こります。"
                "数式による換算ではなく、実際の駅伝タイムとトラック走力の両方を見て判断してください。"
            ),
            "drive_source_note": (
                "駅伝記録は Google Drive「荒玉駅伝歴代」の結果画像と全セルを目視照合済み。"
                "ただし2014年女子の原画像は同フォルダ内で確認できず、未掲載。"
                "選手名は同年度の中学生女子トラック記録CSVと照合し、表記が競合する場合はCSVを優先。"
                "トラック記録は2012〜2026年度CSVのうち、駅伝と同じ年度だけを参照。"
                "学校以外のクラブ所属（ATRC, NJAC, 長洲JRC, 金栗PROJECT 等）も、"
                "駅伝選手と同姓同名かつ学年が矛盾しない場合は同一人物として取り込む。"
            ),
            "sources": {
                "ekiden": str(TOP4_JSON.relative_to(ROOT)),
                "wide_sb": str(WIDE_SB.relative_to(ROOT)),
                "output_reg": str(OUTPUT_REG.relative_to(ROOT)),
                "by_year": str(BY_YEAR_DIR.relative_to(ROOT)),
                "notion": [str(p.relative_to(ROOT)) for p, _, _ in NOTION_DBS],
            },
        },
        "years": years_out,
    }


def write_csv(data: dict[str, Any]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for y in data["years"]:
        for team in y["teams"]:
            for ath in team["athletes"]:
                row: dict[str, Any] = {
                    "year": y["year"],
                    "rank": team["rank"],
                    "school": team["school"],
                    "leg": ath["leg"],
                    "name": ath["name"],
                    "grade": ath.get("grade") or "",
                    "ekiden_mark": ath.get("ekiden_mark") or "",
                }
                for event in TRACK_EVENTS:
                    ev = (ath.get("track_events") or {}).get(event) or {}
                    sb = ev.get("sb") or {}
                    recent = ev.get("recent") or {}
                    row[f"{event}_sb"] = sb.get("mark") or ""
                    row[f"{event}_sb_url"] = sb.get("url") or ""
                    row[f"{event}_recent"] = recent.get("mark") or ""
                    row[f"{event}_recent_url"] = recent.get("url") or ""
                rows.append(row)
    if not rows:
        raise ValueError("joined data has no athlete rows")
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def fact_check_joined(data: dict[str, Any] | None = None) -> list[str]:
    """突合結果の整合性を検証し、問題があれば説明文字列のリストを返す。"""
    issues: list[str] = []
    data = data or build_joined()
    wide = load_wide_like_csv(WIDE_SB, "wide_sb", "2025")
    oreg = load_wide_like_csv(OUTPUT_REG, "output_reg", "2026")
    by_year = load_by_year_json()
    notion = load_notion_rows()
    all_recs = merge_records(wide, oreg, by_year, notion)

    for yblock in data["years"]:
        year = yblock["year"]
        seasons = seasons_for_ekiden_year(year)
        for team in yblock["teams"]:
            school = team["school"]
            for ath in team["athletes"]:
                nn = norm_name(ath["name"])
                recs = filter_records_for_athlete(
                    list(all_recs.get(nn, [])), year, school, ath.get("grade")
                )
                for event, payload in (ath.get("track_events") or {}).items():
                    for kind in ("sb", "recent"):
                        shown = (payload or {}).get(kind)
                        if not shown:
                            continue
                        if shown.get("season") != str(year):
                            issues.append(
                                f"{year} {school} {ath['name']} {event} {kind}: "
                                f"season={shown.get('season')}"
                            )
                        expected = (
                            pick_sb(recs, seasons, event)
                            if kind == "sb"
                            else pick_recent(recs, seasons, event)
                        )
                        if expected and shown.get("mark") != expected.get("mark"):
                            issues.append(
                                f"{year} {school} {ath['name']} {event} {kind}: "
                                f"shown={shown.get('mark')} expected={expected.get('mark')}"
                            )
                        aff = shown.get("school") or ""
                        if aff and not school_overlap(school, aff) and not is_club_affiliation(
                            aff, school
                        ):
                            issues.append(
                                f"{year} {school} {ath['name']}: "
                                f"unclassified affiliation {aff!r}"
                            )
                        if (
                            kind == "sb"
                            and str(shown.get("source") or "").startswith("by_year_")
                        ):
                            source_rows = [
                                r
                                for r in by_year.get(nn, [])
                                if str(r.get("season")) == str(year)
                                and r.get("event") == event
                                and r.get("is_sb")
                            ]
                            if not source_rows:
                                issues.append(
                                    f"{year} {school} {ath['name']} {event}: "
                                    "SB missing in by_year source"
                                )
                            else:
                                best = min(source_rows, key=lambda r: r["seconds"])
                                if shown.get("mark") != best.get("mark"):
                                    issues.append(
                                        f"{year} {ath['name']} {event}: "
                                        f"SB {shown.get('mark')} != csv {best.get('mark')}"
                                    )
    return issues


def main() -> None:
    data = build_joined()
    issues = fact_check_joined(data)
    if issues:
        raise SystemExit("fact check failed:\n" + "\n".join(issues))
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(data)
    s = data["meta"]["stats"]
    print(
        f"athletes={s['athletes']} with_track={s['with_any_track']} "
        f"with_sb={s['with_sb']} with_url={s['with_url']}"
    )
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
