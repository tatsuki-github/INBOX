#!/usr/bin/env python3
"""Generate Aragyoku leg-time → split-rank estimate prepared FAQ.

Covers「荒玉駅伝男子の1区を9:30で走ると区間何位くらいになる？」for
all genders/legs from 2024–2025 transcripts (men = current course era).

Also writes `out/analysis/aragyoku_leg_time_rank_guide.md` as the human/
audit-facing projection table.

Usage:
  python3 scripts/generate_prepared_qa_aragyoku_leg_time_rank.py --dry-run
  python3 scripts/generate_prepared_qa_aragyoku_leg_time_rank.py
  python3 scripts/generate_prepared_qa_aragyoku_leg_time_rank.py && python3 scripts/sync_prepared_qa.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import entry  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
GUIDE = ROOT / "out" / "analysis" / "aragyoku_leg_time_rank_guide.md"
MEN_JSON = ROOT / "input" / "aragyoku" / "men_full_2012_2025.json"
WOMEN_JSON = ROOT / "input" / "aragyoku" / "women_full_2012_2025.json"
ID_PREFIX = "aragyoku-leg-time-rank-"
YEARS = (2024, 2025)
PAD_BEFORE = 15
PAD_AFTER = 20
OUTLIER_JUMP = 45


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


def load_year_splits(data: dict, year: int, leg: int) -> list[dict]:
    rows: list[dict] = []
    year_block = data["years"].get(str(year))
    if not year_block:
        return rows
    for team in year_block.get("teams") or []:
        for lg in team.get("legs") or []:
            if int(lg.get("leg") or 0) != leg:
                continue
            sec = parse_split(lg.get("split"))
            if sec is None:
                continue
            rows.append(
                {
                    "sec": sec,
                    "split": lg.get("split") or fmt_clock(sec),
                    "team": str(team.get("team") or ""),
                    "name": str(lg.get("name") or ""),
                    "split_rank": lg.get("split_rank"),
                }
            )
    rows.sort(key=lambda r: (r["sec"], r["team"], r["name"]))
    return rows


def trim_range(secs: list[int]) -> tuple[int, int]:
    s = sorted(secs)
    if not s:
        raise ValueError("empty splits")
    keep = [s[0]]
    for x in s[1:]:
        if x - keep[-1] > OUTLIER_JUMP and x - s[0] > 90:
            break
        keep.append(x)
    return keep[0], keep[-1]


def equivalent_rank(rows: list[dict], target: int) -> int:
    """Rank if `target` were inserted into that year's field (1 = fastest)."""
    faster = sum(1 for r in rows if r["sec"] < target)
    return faster + 1


def same_time_examples(rows: list[dict], target: int, limit: int = 3) -> list[str]:
    out: list[str] = []
    for r in rows:
        if r["sec"] != target:
            continue
        name = r["name"] if r["name"] and r["name"] != "unknown" else "選手名未詳"
        out.append(f"{name}（{r['team']}）")
        if len(out) >= limit:
            break
    return out


def build_leg_matrix(gender: str, data: dict, leg: int) -> dict:
    by_year = {y: load_year_splits(data, y, leg) for y in YEARS}
    all_secs = [r["sec"] for rows in by_year.values() for r in rows]
    lo, hi = trim_range(all_secs)
    start, end = lo - PAD_BEFORE, hi + PAD_AFTER
    targets = list(range(start, end + 1))
    return {
        "gender": gender,
        "leg": leg,
        "by_year": by_year,
        "targets": targets,
        "field_lo": lo,
        "field_hi": hi,
    }


def answer_for(matrix: dict, target: int) -> str:
    gender = matrix["gender"]
    leg = matrix["leg"]
    clock = fmt_clock(target)
    bits: list[str] = []
    for y in sorted(YEARS, reverse=True):
        rows = matrix["by_year"][y]
        if not rows:
            continue
        rank = equivalent_rank(rows, target)
        field = len(rows)
        if target < rows[0]["sec"]:
            tip = f"{y}年なら区間1位級（当時最速{rows[0]['split']}より速い）"
        elif target > rows[-1]["sec"]:
            tip = f"{y}年なら区間{field}位前後（当時最遅{rows[-1]['split']}より遅い）"
        else:
            tip = f"{y}年なら区間{rank}位相当（{field}チーム中）"
        examples = same_time_examples(rows, target)
        if examples:
            tip += f"・同タイム: {'、'.join(examples)}"
        bits.append(tip)
    joined = "。".join(bits) + "。"
    return (
        f"荒玉駅伝{gender}{leg}区を{clock}で走った場合の区間順位目安"
        f"（現行コース・{YEARS[0]}–{YEARS[1]}実績）です。"
        f"{joined}"
        "年によって前後します。通過順位ではなく区間タイム順位の目安です。"
    )


def questions_for(gender: str, leg: int, clock: str) -> list[str]:
    g, n, t = gender, leg, clock
    return [
        f"荒玉駅伝{g}の{n}区を{t}で走ると区間何位くらいになる？",
        f"荒玉駅伝{g}の{n}区を{t}で走ると区間何位くらい？",
        f"荒玉{g}{n}区を{t}で走ったら区間何位？",
        f"荒玉{g}{n}区{t}は区間何位くらい？",
        f"{g}{n}区を{t}で走ると荒玉で何位？",
        f"荒玉駅伝の{g}{n}区{t}は何位相当？",
        f"2025年荒玉{g}{n}区を{t}で走ると何位？",
        f"去年の荒玉{g}{n}区で{t}は区間何位くらい？",
        f"荒玉駅伝{g}{n}区{t}だと区間順位は？",
        f"{g}の荒玉{n}区を{t}で走ると何位くらい？",
    ]


def sources_for(gender: str) -> list[str]:
    return [
        f"input/aragyoku/transcripts/2024-{gender}.json",
        f"input/aragyoku/transcripts/2025-{gender}.json",
        "out/analysis/aragyoku_leg_time_rank_guide.md",
        (
            "input/aragyoku/men_full_2012_2025.json"
            if gender == "男子"
            else "input/aragyoku/women_full_2012_2025.json"
        ),
    ]


def build_matrices() -> list[dict]:
    men = json.loads(MEN_JSON.read_text(encoding="utf-8"))
    women = json.loads(WOMEN_JSON.read_text(encoding="utf-8"))
    out: list[dict] = []
    for gender, data, nlegs in (("男子", men, 6), ("女子", women, 5)):
        for leg in range(1, nlegs + 1):
            out.append(build_leg_matrix(gender, data, leg))
    return out


def build_entries(matrices: list[dict] | None = None) -> list[dict]:
    matrices = matrices or build_matrices()
    out: list[dict] = []
    for matrix in matrices:
        gender = matrix["gender"]
        leg = matrix["leg"]
        src = sources_for(gender)
        for target in matrix["targets"]:
            clock = fmt_clock(target)
            eid = f"{ID_PREFIX}{gender}-leg{leg}-{clock.replace(':', '-')}"
            out.append(
                entry(
                    eid,
                    questions_for(gender, leg, clock),
                    answer_for(matrix, target),
                    src,
                    ["aragyoku", "leg-time-rank", gender, f"leg{leg}", "2024", "2025"],
                )
            )
    return out


def gen_entries() -> list[dict]:
    """Read-only rebuild for audit_prepared_qa_facts source_projection."""
    return build_entries()


def write_guide(matrices: list[dict]) -> None:
    lines = [
        "# 荒玉駅伝 区間タイム→区間順位目安（2024–2025）",
        "",
        "現行コース実績（男子は2024年再編以降）の区間タイムを、その年のフィールドに当てはめた区間順位目安。",
        "通過順位ではなく区間タイム順位。年によって前後する。",
        "",
        "正本: `input/aragyoku/transcripts/{year}-{gender}.json` / `men_full`・`women_full`。",
        f"生成: `scripts/generate_prepared_qa_aragyoku_leg_time_rank.py`",
        "",
    ]
    for matrix in matrices:
        gender = matrix["gender"]
        leg = matrix["leg"]
        lines.append(f"## {gender}{leg}区")
        lines.append("")
        lines.append(
            f"観測レンジ {fmt_clock(matrix['field_lo'])}–{fmt_clock(matrix['field_hi'])}"
            f"（生成 {fmt_clock(matrix['targets'][0])}–{fmt_clock(matrix['targets'][-1])}）。"
        )
        lines.append("")
        for y in YEARS:
            rows = matrix["by_year"][y]
            board = "、".join(
                f"{r['split_rank']}位{r['split']}（{r['team']}）" for r in rows[:8]
            )
            lines.append(f"- {y}年上位: {board}")
        lines.append("")
        lines.append("| タイム | 2025相当 | 2024相当 | 同タイム例 |")
        lines.append("|---:|---:|---:|---|")
        for target in matrix["targets"]:
            clock = fmt_clock(target)
            r25 = equivalent_rank(matrix["by_year"][2025], target)
            r24 = equivalent_rank(matrix["by_year"][2024], target)
            ex = same_time_examples(matrix["by_year"][2025], target) or same_time_examples(
                matrix["by_year"][2024], target
            )
            lines.append(
                f"| {clock} | {r25} | {r24} | {'、'.join(ex) if ex else '—'} |"
            )
        lines.append("")
        # prose anchors for source clock extraction / RAG
        for target in matrix["targets"]:
            clock = fmt_clock(target)
            r25 = equivalent_rank(matrix["by_year"][2025], target)
            r24 = equivalent_rank(matrix["by_year"][2024], target)
            lines.append(
                f"{gender}{leg}区 {clock} は2025年区間{r25}位相当・2024年区間{r24}位相当。"
            )
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
    marker = "aragyoku-leg-time-rank"
    if marker not in text:
        text = text.replace(
            "note: |",
            "note: |\n"
            "  aragyoku-leg-time-rank: 荒玉男女の区間タイム→区間順位目安（2024-2025）を想定Q&A化。",
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
    ap.add_argument("--skip-guide", action="store_true")
    args = ap.parse_args()
    matrices = build_matrices()
    entries = build_entries(matrices)
    print(
        f"generated {len(entries)} entries across "
        f"{len(matrices)} gender×leg matrices"
    )
    sample = next(
        e for e in entries if e["id"] == "aragyoku-leg-time-rank-男子-leg1-9-30"
    )
    print("SAMPLE", sample["id"])
    print(sample["answer"][:260].replace("\n", " "))
    if args.dry_run:
        for matrix in matrices:
            print(
                "-",
                matrix["gender"],
                f"leg{matrix['leg']}",
                len(matrix["targets"]),
                "targets",
                fmt_clock(matrix["targets"][0]),
                "→",
                fmt_clock(matrix["targets"][-1]),
            )
        return 0
    if not args.skip_guide:
        write_guide(matrices)
        print(f"wrote {GUIDE}")
    added, skipped = append_entries(entries)
    print(f"wrote {FAQ} (+{added} / skip {skipped})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
