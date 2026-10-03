#!/usr/bin/env python3
"""Generate prepared FAQ: なごみ駅伝 チーム別結果（ADR 059）.

Yearless questions → 今年度（DEFAULT_YEAR）。リンクは Drive フォルダ URL のみ。

Usage:
  python3 scripts/generate_prepared_qa_nagomi_team_results.py
  python3 scripts/generate_prepared_qa_nagomi_team_results.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import entry, slug  # noqa: E402
from generate_prepared_qa_knowledge_5000 import DEFAULT_YEAR  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
ID_PREFIX = "nagomi-team-"

# school short name variants for questions (canon + common aliases)
TEAM_Q_NAMES: dict[str, list[str]] = {
    "荒尾第四": ["荒尾第四", "荒尾四", "荒尾第四中", "荒尾四中"],
    "荒尾第三": ["荒尾第三", "荒尾三", "荒尾第三中"],
    "荒尾海陽": ["荒尾海陽", "荒尾海陽中"],
    "岱明": ["岱明", "岱明中", "いだてん岱明"],
    "南関": ["南関", "南関中"],
    "天水": ["天水", "天水中"],
    "玉名高校附属": ["玉名高校附属", "玉高附属", "玉名附属", "玉名附中"],
    "玉名アスリーツ": ["玉名アスリーツ"],
}

DRIVE = {
    2026: "https://drive.google.com/drive/folders/1k-zW0irJ-OjDjqQwUQLZIs4C6PfuR211",
    2025: "https://drive.google.com/drive/folders/1NSx1uYMt2_N9ezohsnyZ4BPXIw-rfUb6",
}

MEET_DIRS = {
    2026: ROOT
    / "input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会",
    2025: ROOT
    / "input/idaten-corpus/drive-text/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会",
}

DATES = {2026: "2026-09-20", 2025: "2025-09-21"}

# 2026: | rank|No.|team|total|1区|2区|3区|4区|
ROW_RE_8 = re.compile(
    r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|$"
)
# 2025: | rank|team|total|1区|2区|3区|4区|
ROW_RE_7 = re.compile(
    r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|$"
)


def parse_leg_cell(cell: str) -> str:
    cell = (cell or "").strip()
    if not cell:
        return ""
    # 藤井祐吏3 (19)10:15 → 藤井祐吏 10:15
    m = re.match(
        r"([^\s(（]+?)(?:\d)?\s*(?:\([^)]+\))?(\d{1,2}:\d{2})",
        cell,
    )
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return cell


def parse_results_md(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        m8 = ROW_RE_8.match(line)
        m7 = ROW_RE_7.match(line) if not m8 else None
        if m8:
            rank, no, team, total = (
                m8.group(1).strip(),
                m8.group(2).strip(),
                m8.group(3).strip(),
                m8.group(4).strip(),
            )
            leg_cells = [m8.group(i) for i in range(5, 9)]
        elif m7:
            rank, team, total = (
                m7.group(1).strip(),
                m7.group(2).strip(),
                m7.group(3).strip(),
            )
            no = ""
            leg_cells = [m7.group(i) for i in range(4, 8)]
        else:
            continue
        if not re.fullmatch(r"[0-9]+|OP", rank) or not team or team in {"チーム", "---"}:
            continue
        if not re.search(r"\d+:\d{2}", total) and total not in {"—", "-", ""}:
            continue
        legs = [parse_leg_cell(c) for c in leg_cells]
        legs = [x for x in legs if x]
        out.append(
            {
                "rank": rank,
                "no": no,
                "team": team,
                "total": total,
                "legs": legs,
            }
        )
    return out


def base_team_key(team: str) -> str:
    t = team.strip()
    t = re.sub(r"[Ａ-ＺA-ZαΩβ]$", "", t)  # trailing Latin letter teams keep separate
    # keep A/B/C suffixes as distinct teams
    return t


def q_names_for(team: str) -> list[str]:
    # strip A/B/C for alias lookup of base school
    base = re.sub(r"[ABCＡＢＣ]$", "", team)
    base = re.sub(r"中学校$", "", base)
    names = TEAM_Q_NAMES.get(base) or TEAM_Q_NAMES.get(team)
    if names:
        # include full team string (荒尾第四A etc.)
        out = list(names)
        if team not in out:
            out.insert(0, team)
        return out
    return [team, re.sub(r"中学校$", "", team)]


def build_answer(
    year: int,
    gender: str,
    rows: list[dict],
) -> str:
    date = DATES[year]
    drive = DRIVE[year]
    parts: list[str] = []
    for r in rows:
        rank = r["rank"]
        if rank == "OP":
            rank_s = "オープン参加"
        else:
            rank_s = f"総合{rank}位"
        leg_s = "、".join(
            f"{i + 1}区{leg}" for i, leg in enumerate(r["legs"]) if leg
        )
        line = f"{gender}は{rank_s}・{r['total']}"
        if leg_s:
            line += f"（{leg_s}）"
        line += "。"
        if len(rows) > 1:
            line = f"{r['team']}: " + line
        parts.append(line)
    body = " ".join(parts)
    return (
        f"{year}年なごみ駅伝（{date}）の結果です。{body}"
        f" 資料: {drive}\n"
    )


def questions_for(year: int, team: str, *, yearless: bool) -> list[str]:
    names = q_names_for(team)
    meet_aliases = ["なごみ駅伝", "なごみ", "なごみ大会"]
    qs: list[str] = []
    for name in names:
        for meet in meet_aliases:
            if yearless:
                qs.extend(
                    [
                        f"{name}の{meet}の結果は？",
                        f"{meet}の{name}の結果は？",
                        f"{meet}で{name}はどうだった？",
                        f"今年の{meet}の{name}の結果",
                        f"今年の{meet}で{name}はどうだった？",
                        f"{name}の{meet}成績",
                        f"{meet}{name}の順位は？",
                    ]
                )
            else:
                qs.extend(
                    [
                        f"{year}年の{name}の{meet}の結果は？",
                        f"{year}年{meet}の{name}の結果は？",
                        f"{year}年の{meet}で{name}はどうだった？",
                    ]
                )
    # dedupe
    seen: set[str] = set()
    out: list[str] = []
    for q in qs:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def school_base(team: str) -> str:
    """荒尾第四A → 荒尾第四, 南関α → 南関α (keep greek), 岱明A → 岱明."""
    t = team.strip()
    t = re.sub(r"[ABCＡＢＣ]$", "", t)
    return t or team


def merge_answer(year: int, gender_rows: dict[str, list[dict]]) -> str:
    date = DATES[year]
    drive = DRIVE[year]
    lead = f"{year}年なごみ駅伝（{date}）の結果です。"
    chunks: list[str] = []
    for gender in ("男子", "女子"):
        rows = gender_rows.get(gender) or []
        if not rows:
            continue
        for r in rows:
            rank = r["rank"]
            rank_s = "オープン参加" if rank == "OP" else f"総合{rank}位"
            leg_s = "、".join(f"{i + 1}区{leg}" for i, leg in enumerate(r["legs"]) if leg)
            label = r["team"]
            line = f"{gender}・{label}は{rank_s}・{r['total']}"
            if leg_s:
                line += f"（{leg_s}）"
            chunks.append(line + "。")
    body = " ".join(chunks)
    return f"{lead}{body} 資料: {drive}\n"


def collect_year(year: int) -> list[dict]:
    d = MEET_DIRS[year]
    men = parse_results_md(d / "男子成績表.md")
    women = parse_results_md(d / "女子成績表.md")
    # group by exact team, and also by school base for aggregate Qs
    by_exact: dict[str, dict[str, list[dict]]] = {}
    by_base: dict[str, dict[str, list[dict]]] = {}
    for gender, rows in (("男子", men), ("女子", women)):
        for r in rows:
            by_exact.setdefault(r["team"], {}).setdefault(gender, []).append(r)
            by_base.setdefault(school_base(r["team"]), {}).setdefault(gender, []).append(r)

    entries: list[dict] = []
    src_base = str(d.relative_to(ROOT))
    sources = [f"{src_base}/男子成績表.md", f"{src_base}/女子成績表.md"]
    yearless = year == DEFAULT_YEAR

    # Prefer base-school entries (covers 荒尾第四 + A/B). Skip exact-only when base differs.
    for team, genders in sorted(by_base.items()):
        ans = merge_answer(year, genders)
        qs = questions_for(year, team, yearless=yearless)
        eid = f"{ID_PREFIX}{year}-{slug(team)[:40]}"
        entries.append(
            entry(eid, qs, ans, sources, ["nagomi", "team-result", year, team])
        )

    # Also keep distinct squad ids for A/B specific questions when different from base
    for team, genders in sorted(by_exact.items()):
        if school_base(team) == team:
            continue
        ans = merge_answer(year, genders)
        qs = questions_for(year, team, yearless=yearless)
        eid = f"{ID_PREFIX}{year}-{slug(team)[:40]}"
        entries.append(
            entry(eid, qs, ans, sources, ["nagomi", "team-result", year, team])
        )
    return entries


def upsert(existing: list[dict], new_entries: list[dict]) -> tuple[int, int]:
    by_id = {e["id"]: i for i, e in enumerate(existing)}
    added = updated = 0
    for e in new_entries:
        if e["id"] in by_id:
            existing[by_id[e["id"]]] = e
            updated += 1
        else:
            existing.append(e)
            by_id[e["id"]] = len(existing) - 1
            added += 1
    return added, updated


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = list(data.get("entries") or [])
    new_entries: list[dict] = []
    for year in (2026, 2025):
        got = collect_year(year)
        print(f"year {year}: {len(got)} teams")
        new_entries.extend(got)

    # highlight 荒尾第四
    arao = [e for e in new_entries if "荒尾第四" in e["id"] or "荒尾四" in e["id"]]
    for e in arao:
        print("---", e["id"])
        print("Q0:", e["questions"][0])
        print(e["answer"][:220].replace("\n", " | "))

    if args.dry_run:
        return 0

    # remove stale nagomi-team-* then upsert
    before = len(entries)
    entries = [e for e in entries if not str(e.get("id", "")).startswith(ID_PREFIX)]
    removed = before - len(entries)
    added, updated = upsert(entries, new_entries)
    data["entries"] = entries
    data["total"] = len(entries)
    note = data.get("note") or ""
    if "nagomi-team-results" not in note:
        data["note"] = (
            note.rstrip()
            + "\nnagomi-team-results: なごみ駅伝のチーム別結果を想定Q&A化。\n"
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
    print(f"removed {removed}; added {added}; updated {updated}; total {len(entries)}")
    print(f"wrote {FAQ.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
