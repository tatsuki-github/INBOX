#!/usr/bin/env python3
"""Add per-athlete all-records prepared FAQ (past 3 years, aragyoku district).

Covers questions like 「村上咲稀の今年度の全ての記録」 with track CSV rows
plus 駅伝・ロード等の大会結果（drive-text / 荒玉 transcripts）。

Usage:
  python3 scripts/generate_prepared_qa_athlete_all_records.py
  python3 scripts/generate_prepared_qa_athlete_all_records.py --dry-run
  python3 scripts/generate_prepared_qa_athlete_all_records.py --replace
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
    entry,
    load_drive_meet_folder_map,
    resolve_drive_meet_url,
    slug,
)
from generate_prepared_qa_knowledge_1000 import load_keywords  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
BY_YEAR_CSV = ROOT / "input" / "external" / "drive" / "personal" / "t-tsuchiyama" / "sb" / "by-year"
MEETS_ROOT = ROOT / "input" / "idaten-corpus" / "drive-text" / "大会"
ARAGYOKU_TX = ROOT / "input" / "aragyoku" / "transcripts"
YEARS = (2024, 2025, 2026)
DEFAULT_YEAR = 2026
ID_PREFIX = "records-athlete-"

ROAD_EKIDEN_FOLDER_RE = re.compile(r"駅伝|なごみ|マラソン")
RESULT_FILES = (
    "荒玉地区の結果.md",
    "岱明の結果.md",
    "記録.md",
    "女子成績表.md",
    "男子成績表.md",
)
CIRCLE_GRADE = str.maketrans("①②③④⑤⑥⑦⑧⑨", "123456789")
TIME_RE = re.compile(
    r"(?P<t>(?:\d{1,2}:)?\d{1,2}:\d{2}(?:\.\d+)?|\d{1,2}'\d{2}(?:\"\d{0,2})?|\d{1,2}分\d{1,2}秒(?:\d+)?)"
)


def _truthy_sb(val: object) -> bool:
    s = str(val or "").strip().upper()
    return s in {"TRUE", "__YES__", "YES", "1", "○", "採用"}


def normalize_athlete_name(name: str) -> str:
    n = (name or "").translate(CIRCLE_GRADE)
    n = re.sub(r"\s+", "", n)
    n = re.sub(r"[（(]\d年[）)]", "", n)
    n = re.sub(r"[①②③1-3]$", "", n)
    n = re.sub(r"\d$", "", n)  # trailing grade digit: 村上咲稀2
    return n.strip()


def normalize_mark(mark: str) -> str:
    m = (mark or "").strip()
    m = m.replace("'", ":").replace("’", ":").replace("″", "").replace('"', "")
    m = re.sub(r"分", ":", m)
    m = re.sub(r"秒", "", m)
    # 2:33:50 style from 2'33"50 → already partially handled; 9分37秒 → 9:37
    if re.fullmatch(r"\d+:\d{2}:\d{2}", m):
        # mm:ss:cs from 2'33"50 misparse — keep as mm:ss.cc if last is 2 digits
        parts = m.split(":")
        if len(parts) == 3 and len(parts[2]) == 2:
            m = f"{parts[0]}:{parts[1]}.{parts[2]}"
    return m


def fiscal_year(date: str) -> int | None:
    m = re.match(r"(20\d{2})[/-](\d{1,2})[/-](\d{1,2})", date or "")
    if not m:
        return None
    y, mo = int(m.group(1)), int(m.group(2))
    return y if mo >= 4 else y - 1


def load_year_rows(year: int) -> list[dict[str, str]]:
    path = BY_YEAR_CSV / f"{year}-single-table.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["_kind"] = "track"
        r["_source"] = str(path.relative_to(ROOT))
    return rows


def affiliation_match(aff: str, keywords: list[str]) -> bool:
    return any(k in aff for k in keywords)


def meet_date_from_dir(meet_dir: Path, year_label: int) -> str:
    for name in ("岱明の結果.md", "概要.md", "荒玉地区の結果.md", "記録.md"):
        p = meet_dir / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"日付:\s*(20\d{2}-\d{2}-\d{2})", text)
        if m:
            return m.group(1).replace("-", "/")
        m = re.search(r"（(20\d{2}-\d{2}-\d{2})）", text)
        if m:
            return m.group(1).replace("-", "/")
        m = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
        if m:
            return m.group(1).replace("-", "/")
    # folder prefix MMDD or MM-DD
    stem = meet_dir.name
    m = re.match(r"(\d{2})(\d{2})", stem)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{year_label}/{mo:02d}/{d:02d}"
    m = re.match(r"(\d{2})-(\d{2})", stem)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{year_label}/{mo:02d}/{d:02d}"
    return ""


def short_meet_title(folder: str) -> str:
    raw = folder
    title = re.sub(r"^\d{2,4}(?:-\d{2,4})?_", "", folder)
    if "ジュニア" in raw and "駅伝" in raw:
        return "県ジュニア駅伝"
    if "なごみ" in raw:
        return "なごみ駅伝"
    if "荒玉" in raw:
        return "荒玉駅伝"
    if "金栗駅伝" in raw:
        return "金栗駅伝"
    title = re.sub(r"[（(][^）)]*[）)]", "", title)
    for cut in (r"中学駅伝金栗四三生誕の地", r"第\d+回", r"令和\d+年度"):
        title = re.sub(cut, "", title)
    title = title.replace("なごみ大会", "なごみ駅伝")
    title = re.sub(r"\s+", "", title)
    if len(title) > 24:
        title = title[:23] + "…"
    return title or folder


def extract_ekiden_from_text(text: str) -> list[dict[str, str]]:
    """Pull leg performances: name + leg + mark (+ optional rank)."""
    out: list[dict[str, str]] = []
    # 2区 村上咲稀（3年）7:07（区間4位）
    # 1区 2.7km　村上咲稀（3年）9:58
    # 3区2.0km 村上咲稀 7:21 通過1位、区間1位
    # 1区　村上咲稀2　7位通過　11:02  区間7位
    patterns = [
        re.compile(
            r"(?P<leg>\d{1,2})区\s*(?:(?P<km>\d+(?:\.\d+)?)k?m)?\s*"
            r"(?P<name>[一-龥ぁ-んァ-ヶー]+(?:\s*[一-龥ぁ-んァ-ヶー]+)?)\s*"
            r"(?:[（(]?\d年[）)]?|[①②③1-3])?\s*"
            r"(?:(?P<pass>\d{1,2})位通過)?\s*"
            r"(?P<mark>(?:\d{1,2}:)?\d{1,2}:\d{2}(?:\.\d+)?|\d{1,2}分\d{1,2}秒|\d{1,2}'\d{2}(?:\"\d{0,2})?)"
            r"(?:\s*（?区間(?P<rank>\d{1,2})位)?"
        ),
        re.compile(
            r"\|\s*(?P<leg>\d{1,2})\s*\|\s*(?P<km>\d+(?:\.\d+)?)\s*\|\s*"
            r"(?P<name>[一-龥ぁ-んァ-ヶー\s]+?)[①②③]?\s*\|\s*"
            r"(?P<mark>\d{1,2}:\d{2}(?:\.\d+)?)\s*\|\s*(?P<rank>\d{1,2})?"
        ),
        re.compile(
            r"\|\s*(?P<leg>\d{1,2})区\s*\|\s*(?P<name>[一-龥ぁ-んァ-ヶー]+)\s*\|\s*\d+\s*\|\s*"
            r"(?P<mark>\d{1,2}:\d{2}(?:\.\d+)?)\s*\|\s*(?P<rank>\d{1,2})?"
        ),
    ]
    seen: set[tuple[str, str, str]] = set()
    for pat in patterns:
        for m in pat.finditer(text):
            name = normalize_athlete_name(m.group("name"))
            if len(name) < 2 or name in {"区間", "通過", "総合", "順位", "選手"}:
                continue
            mark = normalize_mark(m.group("mark"))
            leg = m.group("leg")
            key = (name, leg, mark)
            if key in seen:
                continue
            seen.add(key)
            km = m.groupdict().get("km") or ""
            rank = m.groupdict().get("rank") or ""
            dist = f"{leg}区"
            if km:
                dist = f"{leg}区{km}km"
            note = ""
            if rank:
                note = f"区間{rank}位"
            out.append(
                {
                    "名前": name,
                    "距離": dist,
                    "記録": mark,
                    "_leg": leg,
                    "_note": note,
                    "_kind": "ekiden",
                }
            )
    return out


def load_road_ekiden_rows(drive_map: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not MEETS_ROOT.exists():
        return rows
    for year_dir in sorted(MEETS_ROOT.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.endswith("年度"):
            continue
        try:
            year_label = int(year_dir.name.replace("年度", ""))
        except ValueError:
            continue
        for meet_dir in sorted(year_dir.iterdir()):
            if not meet_dir.is_dir():
                continue
            if not ROAD_EKIDEN_FOLDER_RE.search(meet_dir.name):
                continue
            # skip prediction-only stubs without results
            has_result = any((meet_dir / f).exists() for f in RESULT_FILES)
            if not has_result:
                continue
            date = meet_date_from_dir(meet_dir, year_label)
            title = short_meet_title(meet_dir.name)
            url = resolve_drive_meet_url(meet_dir.name, title, drive_map) or ""
            # avoid pulling pure SB予想 tables: prefer 荒玉地区/岱明の結果/記録 first
            texts: list[tuple[str, str]] = []
            for fname in RESULT_FILES:
                p = meet_dir / fname
                if p.exists():
                    texts.append((fname, p.read_text(encoding="utf-8", errors="ignore")))
            # skip folders that only have 予定/概要 without athlete marks in result files
            extracted: list[dict[str, str]] = []
            for fname, text in texts:
                if "SB予想" in fname or "オーダーリスト" in fname:
                    continue
                # skip scheduled stubs
                if re.search(r"ステータス:\s*scheduled", text) and "区間" not in text:
                    continue
                for hit in extract_ekiden_from_text(text):
                    hit = dict(hit)
                    hit["日付"] = date.replace("-", "/") if date else ""
                    hit["大会名"] = title
                    hit["所属"] = ""  # filled later from track if known
                    hit["参考"] = url
                    hit["_source"] = str((meet_dir / fname).relative_to(ROOT))
                    hit["_folder"] = meet_dir.name
                    extracted.append(hit)
            rows.extend(extracted)
    return rows


def load_aragyoku_ekiden_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not ARAGYOKU_TX.exists():
        return rows
    for path in sorted(ARAGYOKU_TX.glob("20*-*.json")):
        m = re.match(r"(20\d{2})-(男子|女子)\.json$", path.name)
        if not m:
            continue
        year, gender = int(m.group(1)), m.group(2)
        data = json.loads(path.read_text(encoding="utf-8"))
        teams = data.get("teams") or []
        # race date: October of that calendar year (荒玉 is mid-Oct)
        date = f"{year}/10/15"
        for team in teams:
            school = (team.get("team") or team.get("name") or "").strip()
            rank = team.get("rank")
            total = team.get("total") or team.get("time") or ""
            for leg in team.get("legs") or team.get("splits") or []:
                name = normalize_athlete_name(str(leg.get("name") or ""))
                if not name:
                    continue
                mark = normalize_mark(str(leg.get("time") or leg.get("split") or ""))
                if not mark:
                    continue
                leg_n = str(leg.get("leg") or leg.get("order") or "")
                split_rank = leg.get("split_rank") or leg.get("leg_rank")
                note = f"区間{split_rank}位" if split_rank else ""
                if rank:
                    note = (note + f"・総合{rank}位").strip("・")
                rows.append(
                    {
                        "名前": name,
                        "所属": school,
                        "性別": gender,
                        "日付": date,
                        "距離": f"{leg_n}区" if leg_n else "駅伝",
                        "記録": mark,
                        "大会名": "荒玉駅伝",
                        "参考": "",
                        "_kind": "ekiden",
                        "_note": note,
                        "_source": str(path.relative_to(ROOT)),
                        "_team_total": str(total),
                    }
                )
    return rows


def dedupe_key(r: dict[str, str]) -> tuple:
    return (
        normalize_athlete_name(r.get("名前") or ""),
        (r.get("日付") or "").replace("-", "/"),
        (r.get("距離") or "").replace(" ", ""),
        normalize_mark(r.get("記録") or ""),
    )


def merge_rows(
    track: list[dict[str, str]], extras: list[dict[str, str]]
) -> list[dict[str, str]]:
    by_name_aff: dict[str, str] = {}
    by_name_gender: dict[str, str] = {}
    for r in track:
        name = normalize_athlete_name(r.get("名前") or "")
        if name and r.get("所属"):
            by_name_aff.setdefault(name, r["所属"].strip())
        if name and r.get("性別"):
            by_name_gender.setdefault(name, r["性別"].strip())

    seen = {dedupe_key(r) for r in track}
    out = list(track)
    for r in extras:
        name = normalize_athlete_name(r.get("名前") or "")
        r = dict(r)
        r["名前"] = name
        if not r.get("所属"):
            r["所属"] = by_name_aff.get(name, "")
        if not r.get("性別"):
            r["性別"] = by_name_gender.get(name, "")
        # only keep athletes already in track CSV for the district, OR with 所属 set from aragyoku
        if name not in by_name_aff and not r.get("所属"):
            continue
        key = dedupe_key(r)
        if key in seen:
            continue
        # also skip if same name+date+mark already (distance label differs)
        soft = (name, (r.get("日付") or "").replace("-", "/"), normalize_mark(r.get("記録") or ""))
        if any(
            (
                normalize_athlete_name(x.get("名前") or ""),
                (x.get("日付") or "").replace("-", "/"),
                normalize_mark(x.get("記録") or ""),
            )
            == soft
            for x in out
        ):
            continue
        seen.add(key)
        out.append(r)
    return out


def group_by_athlete(
    rows: list[dict[str, str]], keywords: list[str]
) -> dict[str, list[dict[str, str]]]:
    by: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        aff = (r.get("所属") or "").strip()
        name = normalize_athlete_name(r.get("名前") or "")
        if not name:
            continue
        # track rows need affiliation keywords; ekiden may use short school names
        if r.get("_kind") == "track":
            if not aff or not affiliation_match(aff, keywords):
                continue
        elif aff and not affiliation_match(aff, keywords) and aff not in {
            "岱明",
            "玉高附属",
            "南関",
            "天水",
            "有明",
            "長洲",
            "菊水",
            "荒尾三",
            "荒尾四",
            "荒尾海陽",
            "玉名",
            "玉陵",
            "玉東",
            "玉南",
            "三加和",
        }:
            # allow if athlete known from track keywords via empty check later
            pass
        dist = (r.get("距離") or "").strip()
        mark = (r.get("記録") or "").strip()
        if not dist or not mark:
            continue
        by[name].append(r)
    return by


def sort_races(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    def key(r: dict[str, str]) -> tuple:
        kind_order = 0 if r.get("_kind") == "track" else 1
        return (
            r.get("日付") or "",
            kind_order,
            r.get("距離") or "",
            float(r.get("記録秒") or 1e12),
        )

    return sorted(rows, key=key)


def meet_url(r: dict[str, str]) -> str:
    for key in ("参考", "url", "URL"):
        u = (r.get(key) or "").strip()
        if u.startswith("http") and "notion.com" not in u and "notion.so" not in u:
            return u
    return ""


def shorten_meet(meet: str) -> str:
    m = re.sub(r"\s+", " ", (meet or "").strip())
    m = re.sub(r"^\d{4}\.\d{1,2}\.\d{1,2}\s*", "", m)
    if len(m) > 40:
        m = m[:39] + "…"
    return m


def format_race_line(r: dict[str, str]) -> str:
    date = (r.get("日付") or "").strip() or "?"
    dist = (r.get("距離") or "").strip()
    mark = (r.get("記録") or "").strip()
    meet = shorten_meet(r.get("大会名") or "")
    url = meet_url(r)
    kind = r.get("_kind") or "track"
    prefix = {"ekiden": "【駅伝】", "road": "【ロード】"}.get(kind, "")
    bit = f"{prefix}{date} {dist} {mark}".strip()
    if meet:
        bit += f"（{meet}）"
    note = (r.get("_note") or "").strip()
    if note:
        bit += f" {note}"
    if _truthy_sb(r.get("SB採用")):
        bit += "【SB】"
    if url:
        bit += f" 大会結果: {url}"
    return bit


def sb_summary(rows: list[dict[str, str]]) -> str:
    best: dict[str, dict[str, str]] = {}
    for r in rows:
        if r.get("_kind") and r["_kind"] != "track":
            continue
        if not _truthy_sb(r.get("SB採用")):
            continue
        dist = (r.get("距離") or "").strip()
        try:
            sec = float(r.get("SB秒") or r.get("記録秒") or 1e12)
        except (TypeError, ValueError):
            continue
        prev = best.get(dist)
        if prev is None or sec < float(prev.get("_sec") or 1e12):
            best[dist] = {**r, "_sec": str(sec)}
    if not best:
        return ""
    parts = []
    for dist in sorted(best.keys()):
        r = best[dist]
        mark = (r.get("SB") or r.get("記録") or "").strip()
        parts.append(f"{dist} {mark}")
    return "SB採用: " + "、".join(parts) + "。"


def build_year_answer(
    name: str, year: int, rows: list[dict[str, str]], *, yearless: bool = False
) -> str:
    races = sort_races(rows)
    aff = (races[0].get("所属") or "").strip()
    gender = (races[0].get("性別") or "").strip()
    who = f"{name}（{aff}" + (f"/{gender}" if gender else "") + "）"
    label = "今年度" if yearless else f"{year}年度"
    n_track = sum(1 for r in races if (r.get("_kind") or "track") == "track")
    n_ekiden = sum(1 for r in races if r.get("_kind") == "ekiden")
    n_road = sum(1 for r in races if r.get("_kind") == "road")
    lines = [format_race_line(r) for r in races]
    scope = f"全{len(lines)}件"
    extras = []
    if n_track:
        extras.append(f"トラック{n_track}")
    if n_ekiden:
        extras.append(f"駅伝{n_ekiden}")
    if n_road:
        extras.append(f"ロード{n_road}")
    if extras and (n_ekiden or n_road):
        scope += f"（{'・'.join(extras)}）"
    ans = f"{who}の{label}の記録は{scope}です。\n" + "\n".join(lines)
    sb = sb_summary(races)
    if sb:
        ans += "\n" + sb
    return ans


def build_3y_answer(name: str, by_year: dict[int, list[dict[str, str]]]) -> str:
    years = sorted(by_year.keys())
    aff = ""
    gender = ""
    for y in reversed(years):
        if by_year[y]:
            aff = (by_year[y][0].get("所属") or "").strip()
            gender = (by_year[y][0].get("性別") or "").strip()
            break
    who = f"{name}（{aff}" + (f"/{gender}" if gender else "") + "）"
    chunks: list[str] = []
    total = 0
    for y in years:
        races = sort_races(by_year[y])
        total += len(races)
        chunks.append(f"【{y}年度・{len(races)}件】")
        chunks.extend(format_race_line(r) for r in races)
        sb = sb_summary(races)
        if sb:
            chunks.append(sb)
    head = f"{who}の過去3年（{years[0]}–{years[-1]}）の記録は全{total}件です。"
    return "\n".join([head, *chunks])


def filter_extras_for_year(
    extras: list[dict[str, str]], year: int
) -> list[dict[str, str]]:
    out = []
    for r in extras:
        fy = fiscal_year(r.get("日付") or "")
        if fy is None:
            # fall back: aragyoku Oct → calendar year as fiscal
            m = re.match(r"(20\d{2})/", r.get("日付") or "")
            if m and int(m.group(1)) == year:
                out.append(r)
            continue
        if fy == year:
            out.append(r)
    return out


def gen_entries(
    existing_ids: set[str], *, replace: bool
) -> list[dict]:
    keywords = load_keywords()
    for extra in ("ＮＪＡＣ", "NJAC", "玉東クラブ", "玉名アスリーツ", "岱明", "岱明中"):
        if extra not in keywords:
            keywords.append(extra)

    drive_map = load_drive_meet_folder_map()
    ekiden_rows = load_road_ekiden_rows(drive_map) + load_aragyoku_ekiden_rows()

    per_year: dict[int, dict[str, list[dict[str, str]]]] = {}
    for year in YEARS:
        track = load_year_rows(year)
        extras = filter_extras_for_year(ekiden_rows, year)
        # only attach extras for athletes in track CSV (district coverage)
        track_names = {
            normalize_athlete_name(r.get("名前") or "")
            for r in track
            if affiliation_match(r.get("所属") or "", keywords)
        }
        extras = [r for r in extras if normalize_athlete_name(r.get("名前") or "") in track_names]
        merged = merge_rows(track, extras)
        per_year[year] = group_by_athlete(merged, keywords)

    out: list[dict] = []
    src_base = "input/external/drive/personal/t-tsuchiyama/sb/by-year"

    for year in YEARS:
        for name, rows in sorted(per_year[year].items()):
            eid = f"{ID_PREFIX}{year}-{slug(name)}"
            if eid in existing_ids and not replace:
                continue
            qs = [
                f"{year}年{name}の全ての記録",
                f"{name}の{year}年の全ての記録",
                f"{year}年の{name}の全記録は？",
                f"{name}の{year}年度の記録一覧",
                f"{year}年度{name}のレース結果一覧",
            ]
            if year == DEFAULT_YEAR:
                qs.extend(
                    [
                        f"{name}の今年度の全ての記録",
                        f"{name}の今年の全ての記録",
                        f"{name}の全ての記録",
                        f"{name}の全記録は？",
                        f"{name}の記録一覧",
                        f"{name}の今季の全記録",
                    ]
                )
            ans = build_year_answer(name, year, rows, yearless=(year == DEFAULT_YEAR))
            sources = [f"{src_base}/{year}-single-table.csv"]
            for r in rows:
                src = r.get("_source") or ""
                if src and src not in sources and not src.endswith(".csv"):
                    sources.append(src)
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    sources[:12],
                    ["records", "athlete", "all", year, name],
                )
            )

    names = sorted({n for ymap in per_year.values() for n in ymap})
    for name in names:
        by_year = {y: per_year[y][name] for y in YEARS if name in per_year[y]}
        if not by_year:
            continue
        eid = f"{ID_PREFIX}3y-{slug(name)}"
        if eid in existing_ids and not replace:
            continue
        qs = [
            f"{name}の過去3年の全ての記録",
            f"{name}の直近3年の記録一覧",
            f"{name}の3年分の全記録は？",
            f"{name}の過去三年のレース結果",
        ]
        sources = [f"{src_base}/{y}-single-table.csv" for y in sorted(by_year)]
        out.append(
            entry(
                eid,
                qs,
                build_3y_answer(name, by_year),
                sources,
                ["records", "athlete", "all", "3y", name],
            )
        )

    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing records-athlete-* entries (default when not dry-run)",
    )
    args = parser.parse_args()
    # Always rebuild records-athlete-* (append-only would leave track-only answers stale).
    replace = True

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = list(data.get("entries") or [])
    before = len(entries)
    entries = [e for e in entries if not str(e.get("id", "")).startswith(ID_PREFIX)]
    print(f"removed old {ID_PREFIX}* entries: {before - len(entries)}")

    existing_ids = {e["id"] for e in entries}
    print(f"existing entries: {len(entries)}")

    new_entries = gen_entries(existing_ids, replace=replace)
    print(f"new athlete-all-records: {len(new_entries)}")

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
    print(f"after question dedupe: {len(cleaned)}")

    for sample_name in ("村上咲稀", "南本幸治郎", "松野凛空"):
        sample = next((e for e in cleaned if sample_name in e["id"] and "2026" in e["id"]), None)
        if sample:
            print("SAMPLE", sample["id"])
            print(sample["answer"][:700])
            print("---")

    if args.dry_run:
        return 0

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
    if "駅伝・ロード" not in note:
        data["note"] = (
            note.rstrip()
            + "\n選手の年度別・過去3年全記録（トラックCSV＋駅伝・ロード等）を収録。\n"
        )
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
    print(f"wrote {FAQ.relative_to(ROOT)} total={len(uniq)} (+{len(cleaned)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
