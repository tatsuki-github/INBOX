#!/usr/bin/env python3
"""Add ~5000 edge-case prepared FAQ entries (ADR 059).

「重箱の隅」向け: 既に枯れた主要テーマの外側を、一次データから事実だけで埋める。

Focus:
  - 2012–2023 荒玉地区 athlete×meet 大会別記録（2024–2026 は既存）
  - 荒玉「○年○位はどの学校」「区間上位」「平均ペース」「通過順位」「学年」
  - 既存ギャップの残り（calendar / careers / year ranks）

Usage:
  python3 scripts/generate_prepared_qa_edge_5000.py --dry-run
  python3 scripts/generate_prepared_qa_edge_5000.py --target 5000
  python3 scripts/generate_prepared_qa_edge_5000.py && python3 scripts/sync_prepared_qa.py
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import (  # noqa: E402
    MEN_FULL,
    WOMEN_FULL,
    entry,
    load_years,
    slug,
)
from generate_prepared_qa_knowledge_1000 import load_keywords, take  # noqa: E402
from generate_prepared_qa_knowledge_5000 import (  # noqa: E402
    _truthy_sb,
    gen_calendar_gap,
    gen_runner_careers,
    meet_url,
    short_meet,
)
from gap_crush_prepared_1000 import gen_year_team_ranks  # noqa: E402

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
PACE_MD = ROOT / "out" / "analysis" / "aragyoku_all_teams_average_pace.md"
LOG = ROOT / "backend" / "data" / "eval-gaps" / "edge-5000-rounds.jsonl"
HIST_YEARS = tuple(range(2012, 2024))  # 2024–2026 already covered
DEFAULT_YEAR = 2026


def load_race_rows(year: int) -> list[dict[str, str]]:
    path = BY_YEAR_CSV / f"{year}-single-table.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def gen_historical_races(existing_ids: set[str], limit: int) -> list[dict]:
    """Athlete × meet for 2012–2023 (荒玉地区所属のみ)."""
    keywords = load_keywords()
    out: list[dict] = []
    # Prefer recent historical years first (more likely asked)
    for year in sorted(HIST_YEARS, reverse=True):
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
            # skip obviously broken marks
            if not re.search(r"\d", mark):
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
        # Prefer meets with a public URL, then more rows
        ranked = sorted(
            groups.items(),
            key=lambda kv: (
                -sum(1 for r in kv[1] if meet_url(r)),
                -len(kv[1]),
                kv[0][0],
                kv[0][1],
            ),
        )
        for (name, sm), rows in ranked:
            eid = f"race-{year}-{slug(name)}-{slug(sm)}"
            if eid in existing_ids or any(e["id"] == eid for e in out):
                continue
            info = meta[(name, sm)]
            lines: list[str] = []
            for r in sorted(rows, key=lambda x: (x.get("日付") or "", x.get("距離") or "")):
                date = (r.get("日付") or "").strip()
                dist = (r.get("距離") or "").strip()
                mark = (r.get("記録") or "").strip()
                bit = f"{date} {dist} {mark}".strip()
                if _truthy_sb(r.get("SB採用")):
                    bit += "【SB】"
                u = meet_url(r)
                if u:
                    bit += f" 大会結果: {u}"
                lines.append(bit)
            if not lines:
                continue
            who = f"{name}（{info['aff']}"
            if info["gender"]:
                who += f"/{info['gender']}"
            who += "）"
            # Past years: every question carries the year (ADR 059)
            qs = [
                f"{year}年{name}の{sm}の記録は？",
                f"{year}年{name}の{sm}の結果",
                f"{year}年{name}は{sm}で何分？",
                f"{year}年{name}の{sm}タイム",
            ]
            ans = (
                f"{who}の{year}年度・{sm}の記録は{len(lines)}件です"
                f"（大会名: {info['meet_full']}）。\n" + "\n".join(lines)
            )
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [
                        f"input/external/drive/personal/t-tsuchiyama/sb/by-year/{year}-single-table.csv"
                    ],
                    ["race", "athlete", "meet", "edge5k", year, sm],
                )
            )
            if len(out) >= limit:
                return out
    return out


def gen_who_at_rank(existing_ids: set[str], limit: int) -> list[dict]:
    """○年荒玉○性の○位はどの学校？"""
    out: list[dict] = []
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        for year, yd in sorted(load_years(path).items(), key=lambda kv: kv[0], reverse=True):
            for team in yd.get("teams") or []:
                name = team.get("team") or ""
                rank = team.get("rank")
                total = team.get("total") or "—"
                if not name or not rank:
                    continue
                eid = f"edge5k-who-rank-{year}-{gender}-{rank}"
                if eid in existing_ids or any(e["id"] == eid for e in out):
                    continue
                # Ambiguous ties: if multiple teams share rank, skip singleton claim
                same = [
                    t
                    for t in (yd.get("teams") or [])
                    if t.get("rank") == rank and t.get("team")
                ]
                if len(same) != 1:
                    continue
                qs = [
                    f"{year}年荒玉{gender}の{rank}位はどの学校？",
                    f"{year}年荒玉駅伝{gender}{rank}位は？",
                    f"{year}荒玉{gender}総合{rank}位の学校",
                    f"{year}年の荒玉{gender}{rank}位校は？",
                ]
                ans = (
                    f"{year}年荒玉駅伝{gender}の総合{rank}位は{name}"
                    f"（{total}）です。"
                )
                out.append(
                    entry(
                        eid,
                        qs,
                        ans,
                        [src],
                        ["aragyoku", "rank", "edge5k", gender, int(year)],
                    )
                )
                if len(out) >= limit:
                    return out
    return out


def gen_split_rank_top(existing_ids: set[str], limit: int) -> list[dict]:
    """区間1〜3位（選手・学校・タイム）。"""
    out: list[dict] = []
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        for year, yd in sorted(load_years(path).items(), key=lambda kv: kv[0], reverse=True):
            by_leg: dict[int, list[tuple]] = defaultdict(list)
            for team in yd.get("teams") or []:
                tname = team.get("team") or ""
                for lg in team.get("legs") or []:
                    name = (lg.get("name") or "").replace(" ", "")
                    sr = lg.get("split_rank")
                    leg = lg.get("leg")
                    split = lg.get("split") or "?"
                    if not name or not sr or not leg:
                        continue
                    try:
                        sr_i = int(sr)
                        leg_i = int(leg)
                    except (TypeError, ValueError):
                        continue
                    if sr_i < 1 or sr_i > 3:
                        continue
                    grade = lg.get("grade")
                    by_leg[leg_i].append((sr_i, name, tname, split, grade))
            for leg, rows in sorted(by_leg.items()):
                # group by rank (ties allowed)
                by_r: dict[int, list[tuple]] = defaultdict(list)
                for row in rows:
                    by_r[row[0]].append(row)
                for sr, group in sorted(by_r.items()):
                    eid = f"edge5k-splitrank-{year}-{gender}-leg{leg}-r{sr}"
                    if eid in existing_ids or any(e["id"] == eid for e in out):
                        continue
                    bits = []
                    for _, name, tname, split, grade in sorted(group, key=lambda x: x[1]):
                        gbit = f"{grade}年・" if grade not in (None, "", "?") else ""
                        bits.append(f"{name}（{gbit}{tname}）{split}")
                    label = {1: "区間賞", 2: "区間2位", 3: "区間3位"}.get(sr, f"区間{sr}位")
                    qs = [
                        f"{year}年荒玉{gender}{leg}区の{label}は誰？",
                        f"{year}年荒玉駅伝{gender}の{leg}区{sr}位",
                        f"{year}荒玉{gender}{leg}区{sr}位の選手",
                    ]
                    if sr == 1:
                        qs.append(f"{year}年荒玉{gender}{leg}区の区間賞は？")
                    ans = (
                        f"{year}年荒玉駅伝{gender}の{leg}区{label}は"
                        + "、".join(bits)
                        + "です。"
                    )
                    out.append(
                        entry(
                            eid,
                            qs,
                            ans,
                            [src, "out/analysis/aragyoku_leg_awards.md"],
                            ["aragyoku", "split-rank", "edge5k", gender, int(year)],
                        )
                    )
                    if len(out) >= limit:
                        return out
    return out


def gen_team_pace(existing_ids: set[str], limit: int) -> list[dict]:
    """年度×順位×学校の平均ペース（pace MD の散文行）。"""
    out: list[dict] = []
    if not PACE_MD.exists():
        return out
    text = PACE_MD.read_text(encoding="utf-8")
    # 2012年荒玉駅伝男子1位 玉名 のチーム全体平均ペースは 3:14.2/km（総合 63:47／19.71km）。
    pat = re.compile(
        r"(\d{4})年荒玉駅伝(男子|女子)(\d+)位\s+(\S+)\s+のチーム全体平均ペースは\s+"
        r"([0-9:./km]+)\s*（総合\s*([^／]+)／([^）]+)）。"
    )
    rows = list(pat.finditer(text))
    # Prefer recent years (file is chronological)
    for m in reversed(rows):
        year, gender, rank, school, pace, total, dist = m.groups()
        eid = f"edge5k-pace-{year}-{gender}-rank{rank}-{slug(school)}"
        if eid in existing_ids or any(e["id"] == eid for e in out):
            continue
        qs = [
            f"{year}年荒玉{gender}{school}の平均ペースは？",
            f"{year}年荒玉駅伝{gender}{rank}位のペース",
            f"{year}荒玉{gender}の{school}は何分/km？",
            f"{year}年{school}の荒玉{gender}平均ペース",
        ]
        ans = (
            f"{year}年荒玉駅伝{gender}{rank}位・{school}のチーム全体平均ペースは"
            f"{pace}（総合{total.strip()}／{dist.strip()}）です。"
        )
        out.append(
            entry(
                eid,
                qs,
                ans,
                ["out/analysis/aragyoku_all_teams_average_pace.md"],
                ["aragyoku", "pace", "edge5k", gender, int(year), school],
            )
        )
        if len(out) >= limit:
            return out
    return out


def gen_passing_rank(existing_ids: set[str], limit: int) -> list[dict]:
    """中継所通過順位（通過順位がある区間）。"""
    out: list[dict] = []
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        for year, yd in sorted(load_years(path).items(), key=lambda kv: kv[0], reverse=True):
            for team in yd.get("teams") or []:
                tname = team.get("team") or ""
                if not tname:
                    continue
                for lg in team.get("legs") or []:
                    pr = lg.get("passing_rank")
                    leg = lg.get("leg")
                    name = (lg.get("name") or "").replace(" ", "")
                    if pr in (None, "", "?") or not leg or not name:
                        continue
                    try:
                        pr_i = int(pr)
                        leg_i = int(leg)
                    except (TypeError, ValueError):
                        continue
                    eid = f"edge5k-pass-{year}-{gender}-{slug(tname)}-leg{leg_i}"
                    if eid in existing_ids or any(e["id"] == eid for e in out):
                        continue
                    cum = lg.get("cumulative") or "?"
                    qs = [
                        f"{year}年荒玉{gender}{tname}の{leg_i}区通過順位は？",
                        f"{year}年荒玉駅伝{gender}{tname}{leg_i}区の中継順位",
                        f"{year}荒玉{gender}{tname}{leg_i}区通過何位？",
                    ]
                    ans = (
                        f"{year}年荒玉駅伝{gender}・{tname}{leg_i}区（{name}）の"
                        f"通過順位は{pr_i}位（累計{cum}）です。"
                    )
                    out.append(
                        entry(
                            eid,
                            qs,
                            ans,
                            [src],
                            ["aragyoku", "passing-rank", "edge5k", gender, int(year)],
                        )
                    )
                    if len(out) >= limit:
                        return out
    return out


def gen_leg_grade(existing_ids: set[str], limit: int) -> list[dict]:
    """○年○校○区走者の学年。"""
    out: list[dict] = []
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        for year, yd in sorted(load_years(path).items(), key=lambda kv: kv[0], reverse=True):
            for team in yd.get("teams") or []:
                tname = team.get("team") or ""
                for lg in team.get("legs") or []:
                    name = (lg.get("name") or "").replace(" ", "")
                    grade = lg.get("grade")
                    leg = lg.get("leg")
                    if not name or grade in (None, "", "?") or not leg:
                        continue
                    try:
                        leg_i = int(leg)
                        grade_i = int(grade)
                    except (TypeError, ValueError):
                        continue
                    eid = f"edge5k-grade-{year}-{gender}-{slug(tname)}-leg{leg_i}"
                    if eid in existing_ids or any(e["id"] == eid for e in out):
                        continue
                    qs = [
                        f"{year}年荒玉{gender}{tname}{leg_i}区は何年生？",
                        f"{year}年荒玉駅伝{gender}の{tname}{leg_i}区の学年",
                        f"{year}荒玉{gender}{name}は何年？",
                    ]
                    ans = (
                        f"{year}年荒玉駅伝{gender}・{tname}{leg_i}区の{name}は"
                        f"{grade_i}年生です。"
                    )
                    out.append(
                        entry(
                            eid,
                            qs,
                            ans,
                            [src],
                            ["aragyoku", "grade", "edge5k", gender, int(year)],
                        )
                    )
                    if len(out) >= limit:
                        return out
    return out


def gen_historical_rank_matrix(existing_ids: set[str], limit: int) -> list[dict]:
    """順位別歴代平均ペース（男子/女子）。"""
    out: list[dict] = []
    if not PACE_MD.exists():
        return out
    text = PACE_MD.read_text(encoding="utf-8")
    for m in re.finditer(
        r"(男子|女子)の総合(\d+)位の歴代平均ペースは\s*([0-9:./km]+)\s*（(\d+)年度）。",
        text,
    ):
        gender, rank, pace, n_years = m.groups()
        eid = f"edge5k-hist-pace-{gender}-rank{rank}"
        if eid in existing_ids or any(e["id"] == eid for e in out):
            continue
        qs = [
            f"荒玉{gender}{rank}位の歴代平均ペースは？",
            f"荒玉駅伝{gender}総合{rank}位の平均ペース",
            f"{gender}{rank}位ペースの歴代平均",
        ]
        ans = (
            f"荒玉駅伝{gender}の総合{rank}位の歴代平均ペースは{pace}"
            f"（{n_years}年度）です。"
        )
        out.append(
            entry(
                eid,
                qs,
                ans,
                ["out/analysis/aragyoku_all_teams_average_pace.md"],
                ["aragyoku", "pace", "edge5k", gender],
            )
        )
        if len(out) >= limit:
            return out
    return out


def build_new_entries(existing_ids: set[str], target: int) -> list[dict]:
    # Quotas: race history is the main edge volume; aragyoku micro-facts for diversity
    quotas: list[tuple[str, int, Callable[[set[str], int], list[dict]]]] = [
        # 歴史大会記録が主量。区間上位・通過・学年など荒玉の細部で多様性を確保。
        ("hist_race", 3000, gen_historical_races),
        ("who_rank", 400, gen_who_at_rank),
        ("split_rank", 400, gen_split_rank_top),
        ("team_pace", 350, gen_team_pace),
        ("passing", 350, gen_passing_rank),
        ("grade", 200, gen_leg_grade),
        ("hist_pace", 40, gen_historical_rank_matrix),
        ("year_ranks", 220, gen_year_team_ranks),
        ("careers", 120, gen_runner_careers),
        ("calendar", 200, gen_calendar_gap),
    ]
    buckets: dict[str, list[dict]] = {}
    for name, n, fn in quotas:
        got = fn(existing_ids, n)
        buckets[name] = got
        print(f"  mine {name}: {len(got)}/{n}")

    selected: list[dict] = []
    used: set[str] = set(existing_ids)
    for name, n, _ in quotas:
        before = len(selected)
        selected.extend(take(buckets[name], n, used))
        print(f"  took {name}: {len(selected) - before}")

    if len(selected) < target:
        for name, _, _ in quotas:
            if len(selected) >= target:
                break
            selected.extend(take(buckets[name], target - len(selected), used))

    # Last resort: pull more historical races beyond quota
    if len(selected) < target:
        extra = gen_historical_races(used, target - len(selected) + 200)
        selected.extend(take(extra, target - len(selected), used))

    print(f"  FINAL new: {len(selected[:target])}")
    return selected[:target]


def validate_entry(e: dict) -> str | None:
    """Return error reason or None if ok."""
    ans = (e.get("answer") or "").strip()
    if len(ans) < 12:
        return "answer too short"
    if re.search(r"(?:^|[\s「])(?:input|out|docs|scripts)/", ans):
        return "repo path in answer"
    if "コーチに直接聞いてください" in ans:
        return "coach fallback"
    qs = e.get("questions") or []
    if not qs:
        return "no questions"
    # Past-year race / aragyoku edge facts must date the question
    eid = e.get("id") or ""
    m = re.match(r"(?:race|edge5k-\w+)-(\d{4})-", eid)
    if m:
        year = m.group(1)
        if int(year) != DEFAULT_YEAR and not all(year in q for q in qs):
            return f"past-year question missing {year}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--target", type=int, default=5000)
    args = ap.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = list(data.get("entries") or [])
    existing_ids = {e["id"] for e in entries}
    print(f"existing entries: {len(entries)}")

    new_entries = build_new_entries(existing_ids, args.target + 800)

    existing_q = {q for e in entries for q in (e.get("questions") or [])}
    cleaned: list[dict] = []
    rejected = Counter()
    for e in new_entries:
        reason = validate_entry(e)
        if reason:
            rejected[reason] += 1
            continue
        qs = [q for q in e["questions"] if q not in existing_q]
        if not qs:
            rejected["dup_questions"] += 1
            continue
        e = dict(e)
        e["questions"] = qs
        cleaned.append(e)
        for q in qs:
            existing_q.add(q)
        if len(cleaned) >= args.target:
            break

    print(f"cleaned: {len(cleaned)} rejected: {dict(rejected)}")
    if len(cleaned) < args.target:
        raise SystemExit(f"expected {args.target} new entries, got {len(cleaned)}")

    cleaned = cleaned[: args.target]
    rounds = [
        {
            "round": i + 1,
            "id": e["id"],
            "q": e["questions"][0],
            "tags": e.get("tags") or [],
        }
        for i, e in enumerate(cleaned)
    ]
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rounds) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {LOG.relative_to(ROOT)}")
    themes = Counter()
    for e in cleaned:
        tags = e.get("tags") or []
        if "race" in tags:
            themes["hist_race"] += 1
        elif "split-rank" in tags:
            themes["split_rank"] += 1
        elif "passing-rank" in tags:
            themes["passing"] += 1
        elif "pace" in tags:
            themes["pace"] += 1
        elif "grade" in tags:
            themes["grade"] += 1
        elif "rank" in tags:
            themes["rank"] += 1
        else:
            themes["other"] += 1
    print("themes:", dict(themes))
    for e in cleaned[:3] + cleaned[-2:]:
        print("SAMPLE", e["id"], e["questions"][0], "=>", e["answer"][:140].replace("\n", " | "))

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
    if "edge-5000" not in note:
        data["note"] = (
            note.rstrip()
            + "\nedge-5000: 重箱の隅向け想定Q&Aを事実ソースから5000件追加"
            "（2012–2023大会別記録・区間上位・通過順位・平均ペース等）。\n"
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
