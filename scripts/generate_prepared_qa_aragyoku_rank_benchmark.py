#!/usr/bin/env python3
"""Generate Aragyoku Nth-place leg-time benchmark prepared FAQ.

Covers「荒玉駅伝女子の各区間5位の基準タイムは？」and per-leg variants
for men/women, all legs, ranks 1–15, from 2024–2025 results
(men = current course era).

Usage:
  python3 scripts/generate_prepared_qa_aragyoku_rank_benchmark.py --dry-run
  python3 scripts/generate_prepared_qa_aragyoku_rank_benchmark.py
  python3 scripts/generate_prepared_qa_aragyoku_rank_benchmark.py && python3 scripts/sync_prepared_qa.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import entry  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
GUIDE = ROOT / "out" / "analysis" / "aragyoku_rank_benchmark_guide.md"
MEN_JSON = ROOT / "input" / "aragyoku" / "men_full_2012_2025.json"
WOMEN_JSON = ROOT / "input" / "aragyoku" / "women_full_2012_2025.json"
ID_PREFIX = "aragyoku-rank-benchmark-"
YEARS = (2024, 2025)
RANKS = range(1, 16)


def parse_split(mark: str | None) -> int | None:
    if not mark or not isinstance(mark, str):
        return None
    upper = mark.upper()
    if any(tok in upper for tok in ("DNS", "DNF", "DSQ", "未", "不明")):
        return None
    if mark.strip() in {"-", "—", "−"}:
        return None
    parts = mark.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        return None
    return None


def fmt_clock(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}"


def load_leg_rows(data: dict, year: int, leg: int) -> list[dict]:
    rows: list[dict] = []
    block = data["years"].get(str(year))
    if not block:
        return rows
    for team in block.get("teams") or []:
        for lg in team.get("legs") or []:
            if int(lg.get("leg") or 0) != leg:
                continue
            sec = parse_split(lg.get("split"))
            if sec is None:
                continue
            sr = lg.get("split_rank")
            try:
                sr_i = int(sr) if sr is not None else None
            except (TypeError, ValueError):
                sr_i = None
            rows.append(
                {
                    "sec": sec,
                    "split": lg.get("split") or fmt_clock(sec),
                    "team": str(team.get("team") or ""),
                    "name": str(lg.get("name") or ""),
                    "split_rank": sr_i,
                }
            )
    rows.sort(key=lambda r: (r["sec"], r["team"], r["name"]))
    return rows


def athletes_at_rank(rows: list[dict], rank: int) -> list[dict]:
    return [r for r in rows if r.get("split_rank") == rank]


def nth_sorted(rows: list[dict], rank: int) -> dict | None:
    if rank < 1 or rank > len(rows):
        return None
    return rows[rank - 1]


def describe_rank(rows: list[dict], rank: int) -> str:
    """Human one-liner for a year's Nth-place benchmark on one leg."""
    if not rows:
        return "記録なし"
    at = athletes_at_rank(rows, rank)
    if at:
        clock = at[0]["split"]
        people = "、".join(
            (
                f"{(r['name'] if r['name'] and r['name'] != 'unknown' else '選手名未詳')}"
                f"（{r['team']}）"
            )
            for r in at[:3]
        )
        return f"{clock}（{people}）"
    nth = nth_sorted(rows, rank)
    if nth is None:
        return f"該当なし（出走{len(rows)}）"
    name = nth["name"] if nth["name"] and nth["name"] != "unknown" else "選手名未詳"
    return (
        f"公式区間{rank}位なし（タイで順位飛び）。"
        f"タイム順{rank}番目は{nth['split']}（{name}/{nth['team']}）"
    )


def clock_for_rank(rows: list[dict], rank: int) -> str | None:
    at = athletes_at_rank(rows, rank)
    if at:
        return at[0]["split"]
    nth = nth_sorted(rows, rank)
    return nth["split"] if nth else None


def sources_for(gender: str) -> list[str]:
    return [
        f"input/aragyoku/transcripts/2024-{gender}.json",
        f"input/aragyoku/transcripts/2025-{gender}.json",
        "out/analysis/aragyoku_rank_benchmark_guide.md",
        (
            "input/aragyoku/men_full_2012_2025.json"
            if gender == "男子"
            else "input/aragyoku/women_full_2012_2025.json"
        ),
    ]


def overview_questions(gender: str, rank: int) -> list[str]:
    g, r = gender, rank
    return [
        f"荒玉駅伝{g}の各区間{r}位の基準タイムは？",
        f"荒玉駅伝{g}の各区間{r}位の基準タイム",
        f"荒玉{g}の各区間{r}位タイムは？",
        f"荒玉{g}各区の区間{r}位の目安タイム",
        f"{g}荒玉の各区間{r}位基準タイム",
        f"荒玉駅伝{g}で区間{r}位のタイム目安は各区いくつ？",
        f"去年の荒玉{g}各区間{r}位のタイムは？",
        f"2025年荒玉{g}の各区間{r}位タイム",
        f"荒玉{g}区間{r}位の基準タイム一覧",
        f"{g}の荒玉で各区{r}位はどれくらいのタイム？",
    ]


def leg_questions(gender: str, leg: int, rank: int) -> list[str]:
    g, n, r = gender, leg, rank
    return [
        f"荒玉駅伝{g}の{n}区{r}位の基準タイムは？",
        f"荒玉{g}{n}区の区間{r}位タイムは？",
        f"荒玉{g}{n}区{r}位は何分くらい？",
        f"{g}{n}区で区間{r}位の目安タイムは？",
        f"荒玉駅伝{g}{n}区の{r}位タイム目安",
        f"去年の荒玉{g}{n}区{r}位のタイムは？",
        f"2025年荒玉{g}{n}区の区間{r}位は何タイム？",
        f"{g}荒玉{n}区{r}位の基準タイム",
        f"荒玉{g}の{n}区で{r}位相当はどれくらい？",
        f"荒玉駅伝{g}{n}区{r}位の記録は？",
    ]


def build_matrices() -> dict:
    men = json.loads(MEN_JSON.read_text(encoding="utf-8"))
    women = json.loads(WOMEN_JSON.read_text(encoding="utf-8"))
    out: dict = {}
    for gender, data, nlegs in (("男子", men, 6), ("女子", women, 5)):
        out[gender] = {"nlegs": nlegs, "legs": {}}
        for leg in range(1, nlegs + 1):
            out[gender]["legs"][leg] = {
                y: load_leg_rows(data, y, leg) for y in YEARS
            }
    return out


def overview_answer(matrix: dict, gender: str, rank: int) -> str:
    nlegs = matrix[gender]["nlegs"]
    year_blocks: list[str] = []
    for y in sorted(YEARS, reverse=True):
        parts = []
        for leg in range(1, nlegs + 1):
            rows = matrix[gender]["legs"][leg][y]
            clock = clock_for_rank(rows, rank)
            if clock is None:
                parts.append(f"{leg}区 該当なし")
            else:
                at = athletes_at_rank(rows, rank)
                if at:
                    parts.append(f"{leg}区 {clock}")
                else:
                    parts.append(f"{leg}区 {clock}（タイム順{rank}番目）")
        year_blocks.append(f"{y}年: " + "、".join(parts))
    detail_bits = []
    # richer 2025 detail with names when official rank exists
    for leg in range(1, nlegs + 1):
        detail_bits.append(
            f"{leg}区は{describe_rank(matrix[gender]['legs'][leg][2025], rank)}"
        )
    return (
        f"荒玉駅伝{gender}の各区間{rank}位の基準タイム目安"
        f"（現行コース・{YEARS[0]}–{YEARS[1]}実績）です。"
        f"{'。'.join(year_blocks)}。"
        f"2025年の内訳: {'。'.join(detail_bits)}。"
        "通過順位ではなく区間タイム順位です。年によって前後します。"
    )


def leg_answer(matrix: dict, gender: str, leg: int, rank: int) -> str:
    bits = []
    for y in sorted(YEARS, reverse=True):
        rows = matrix[gender]["legs"][leg][y]
        bits.append(f"{y}年は{describe_rank(rows, rank)}")
    return (
        f"荒玉駅伝{gender}{leg}区の区間{rank}位基準タイム目安"
        f"（現行コース・{YEARS[0]}–{YEARS[1]}実績）です。"
        f"{'。'.join(bits)}。"
        "通過順位ではなく区間タイム順位です。年によって前後します。"
    )


def build_entries(matrix: dict | None = None) -> list[dict]:
    matrix = matrix or build_matrices()
    out: list[dict] = []
    for gender, meta in matrix.items():
        src = sources_for(gender)
        nlegs = meta["nlegs"]
        for rank in RANKS:
            out.append(
                entry(
                    f"{ID_PREFIX}{gender}-rank{rank}-all-legs",
                    overview_questions(gender, rank),
                    overview_answer(matrix, gender, rank),
                    src,
                    ["aragyoku", "rank-benchmark", gender, f"rank{rank}", "2024", "2025"],
                )
            )
            for leg in range(1, nlegs + 1):
                out.append(
                    entry(
                        f"{ID_PREFIX}{gender}-leg{leg}-rank{rank}",
                        leg_questions(gender, leg, rank),
                        leg_answer(matrix, gender, leg, rank),
                        src,
                        [
                            "aragyoku",
                            "rank-benchmark",
                            gender,
                            f"leg{leg}",
                            f"rank{rank}",
                            "2024",
                            "2025",
                        ],
                    )
                )
    return out


def gen_entries() -> list[dict]:
    """Read-only rebuild for audit_prepared_qa_facts source_projection."""
    return build_entries()


def write_guide(matrix: dict) -> None:
    lines = [
        "# 荒玉駅伝 区間N位の基準タイム（2024–2025）",
        "",
        "現行コース実績の区間タイム順位N位（公式 split_rank）。",
        "タイで順位が飛ぶ場合はタイム順N番目を併記。",
        "",
        "正本: `input/aragyoku/transcripts/{year}-{gender}.json` / men_full・women_full。",
        "生成: `scripts/generate_prepared_qa_aragyoku_rank_benchmark.py`",
        "",
    ]
    for gender, meta in matrix.items():
        nlegs = meta["nlegs"]
        lines.append(f"## {gender}")
        lines.append("")
        for rank in RANKS:
            lines.append(f"### 区間{rank}位")
            lines.append("")
            for y in sorted(YEARS, reverse=True):
                parts = []
                for leg in range(1, nlegs + 1):
                    rows = meta["legs"][leg][y]
                    parts.append(f"{leg}区 {describe_rank(rows, rank)}")
                    clock = clock_for_rank(rows, rank)
                    if clock:
                        # ensure clocks appear for source extraction
                        lines.append(
                            f"{gender}{leg}区の区間{rank}位基準タイム（{y}）は{clock}。"
                        )
                lines.append(f"- {y}: " + " / ".join(parts))
            lines.append("")
    GUIDE.parent.mkdir(parents=True, exist_ok=True)
    GUIDE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def existing_ids(text: str) -> set[str]:
    return set(re.findall(r"(?m)^- id:\s*(\S+)\s*$", text))


def existing_questions(text: str) -> set[str]:
    qs: set[str] = set()
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("- ") and not s.startswith("- id:") and ":" not in s[2:48]:
            q = s[2:].strip().strip("'\"")
            if q and not q.startswith(("input/", "out/", "docs/")):
                qs.add(q)
    return qs


def append_entries(new_entries: list[dict]) -> tuple[int, int]:
    text = FAQ.read_text(encoding="utf-8")
    ids = existing_ids(text)
    claimed = existing_questions(text)
    added = skipped = 0
    chunks: list[str] = []
    for e in new_entries:
        if e["id"] in ids:
            skipped += 1
            continue
        qs = [q for q in e["questions"] if q not in claimed]
        if not qs:
            continue
        for q in qs:
            claimed.add(q)
        e["questions"] = qs
        block = yaml.safe_dump(e, allow_unicode=True, sort_keys=False, width=1000)
        lines = block.splitlines()
        chunks.append("- " + lines[0] + "\n")
        for line in lines[1:]:
            chunks.append("  " + line + "\n")
        ids.add(e["id"])
        added += 1
    if not chunks:
        return added, skipped
    if "aragyoku-rank-benchmark" not in text:
        text = text.replace(
            "note: |",
            "note: |\n"
            "  aragyoku-rank-benchmark: 荒玉男女の区間N位基準タイム（2024-2025）を想定Q&A化。",
            1,
        )
    m = re.search(r"(?m)^total:\s*(\d+)\s*$", text)
    if m:
        text = text.replace(
            f"total: {m.group(1)}",
            f"total: {int(m.group(1)) + added}",
            1,
        )
    if not text.endswith("\n"):
        text += "\n"
    text += "".join(chunks)
    FAQ.write_text(text, encoding="utf-8")
    return added, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    matrix = build_matrices()
    entries = build_entries(matrix)
    print(f"generated {len(entries)} entries")
    sample = next(
        e for e in entries if e["id"] == "aragyoku-rank-benchmark-女子-rank5-all-legs"
    )
    print("SAMPLE", sample["id"])
    print(sample["answer"][:320].replace("\n", " "))
    if args.dry_run:
        return 0
    write_guide(matrix)
    print(f"wrote {GUIDE}")
    added, skipped = append_entries(entries)
    print(f"wrote {FAQ} (+{added} / skip {skipped})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
