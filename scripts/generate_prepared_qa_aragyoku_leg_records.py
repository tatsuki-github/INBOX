#!/usr/bin/env python3
"""Generate yearless Aragyoku all-leg meet-record prepared FAQ.

Covers「荒玉駅伝の男子の区間歴代記録は？」and women's equivalents from
`out/analysis/aragyoku_meet_records.md` (latest board year = 2025).

Usage:
  python3 scripts/generate_prepared_qa_aragyoku_leg_records.py --dry-run
  python3 scripts/generate_prepared_qa_aragyoku_leg_records.py
  python3 scripts/generate_prepared_qa_aragyoku_leg_records.py && python3 scripts/sync_prepared_qa.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import entry  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
MEET_RECORDS = ROOT / "out" / "analysis" / "aragyoku_meet_records.md"
SRC = "out/analysis/aragyoku_meet_records.md"
ID_PREFIX = "aragyoku-leg-records-"
BOARD_YEAR = 2025


def parse_section(text: str, year: int, gender: str) -> dict | None:
    pat = rf"## {year}年 {gender}\n\n(.*?)(?=\n## |\n生成:|\Z)"
    m = re.search(pat, text, re.S)
    if not m:
        return None
    body = m.group(1)
    era_m = re.search(r"course_era:\s*`([^`]+)`", body)
    total_m = re.search(
        r"\*\*総合大会記録\*\*:\s*([0-9:]+)\s*（(.+?)）\s*/\s*(\S+)",
        body,
    )
    legs = []
    for lm in re.finditer(
        r"\|\s*(\d+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9:]+)\s*\|\s*(.+?)\s*\|",
        body,
    ):
        legs.append(
            {
                "leg": int(lm.group(1)),
                "km": lm.group(2),
                "mark": lm.group(3),
                "holder": lm.group(4).strip(),
            }
        )
    if not legs or not total_m:
        return None
    return {
        "year": year,
        "gender": gender,
        "course_era": era_m.group(1) if era_m else "",
        "total": total_m.group(1),
        "total_team": total_m.group(2),
        "total_era": total_m.group(3),
        "legs": legs,
    }


def legs_summary(sec: dict) -> str:
    return "、".join(
        f"{row['leg']}区 {row['mark']}（{row['holder']}）" for row in sec["legs"]
    )


def gender_questions(gender: str) -> list[str]:
    g = gender
    return [
        f"荒玉駅伝の{g}の区間歴代記録は？",
        f"荒玉駅伝の{g}の区間歴代記録",
        f"荒玉駅伝{g}の区間歴代記録は？",
        f"荒玉{g}の区間歴代記録は？",
        f"荒玉{g}の区間記録一覧は？",
        f"荒玉駅伝{g}の大会区間記録一覧",
        f"荒玉{g}の大会区間記録は？",
        f"荒玉駅伝{g}の歴代区間記録",
        f"{g}の荒玉区間歴代記録は？",
        f"{g}荒玉の区間記録保持者一覧",
        f"荒玉{g}各区の大会記録は？",
        f"荒玉駅伝{g}の各区記録は？",
        f"今年の荒玉{g}の区間記録ボードは？",
        f"去年の荒玉{g}の区間歴代記録は？",
        f"2025年荒玉{g}の区間記録一覧",
        f"2025年荒玉駅伝{g}の大会区間記録一覧は？",
    ]


def build_entries(text: str) -> list[dict]:
    out: list[dict] = []
    men = parse_section(text, BOARD_YEAR, "男子")
    women = parse_section(text, BOARD_YEAR, "女子")
    men_old = parse_section(text, 2023, "男子")  # last pre-2024 board era

    if men:
        note = (
            f"荒玉駅伝男子の大会区間記録（ボード上部・{BOARD_YEAR}年表示、現行コース2024年以降）です。"
            f" 総合大会記録 {men['total']}（{men['total_team']}/{men['total_era']}）。"
            f" 区間: {legs_summary(men)}。"
            " 当日の区間賞・区間新とは別です。男子は2024年のコース再編で記録が分かれます。"
        )
        out.append(
            entry(
                f"{ID_PREFIX}男子-current",
                gender_questions("男子")
                + [
                    "荒玉男子の現行コース区間記録は？",
                    "荒玉男子2024以降の区間記録一覧",
                    "荒玉駅伝男子の区間記録ボード",
                ],
                note,
                [SRC],
                ["aragyoku", "record", "meet-records", "男子", "2025"],
            )
        )

    if women:
        note = (
            f"荒玉駅伝女子の大会区間記録（ボード上部・{BOARD_YEAR}年表示）です。"
            f" 総合大会記録 {women['total']}（{women['total_team']}/{women['total_era']}）。"
            f" 区間: {legs_summary(women)}。"
            " 当日の区間賞・区間新とは別です。"
        )
        out.append(
            entry(
                f"{ID_PREFIX}女子-current",
                gender_questions("女子")
                + [
                    "荒玉女子の区間記録ボード",
                    "荒玉駅伝女子の歴代区間記録一覧",
                ],
                note,
                [SRC],
                ["aragyoku", "record", "meet-records", "女子", "2025"],
            )
        )

    if men and women:
        out.append(
            entry(
                f"{ID_PREFIX}both-current",
                [
                    "荒玉駅伝の区間歴代記録は？",
                    "荒玉の区間歴代記録は？",
                    "荒玉駅伝の大会区間記録一覧",
                    "荒玉の各区記録は？",
                    "荒玉駅伝の歴代区間記録を教えて",
                    "荒玉の区間記録保持者一覧",
                ],
                (
                    f"荒玉駅伝の大会区間記録（ボード上部・{BOARD_YEAR}年表示）です。"
                    f" 男子（現行コース）: {legs_summary(men)}。"
                    f" 女子: {legs_summary(women)}。"
                    f" 総合は男子{men['total']}（{men['total_team']}）、女子{women['total']}（{women['total_team']}）。"
                    " 当日の区間賞とは別です。男子は2024年コース再編あり。"
                ),
                [SRC],
                ["aragyoku", "record", "meet-records", "2025"],
            )
        )

    if men_old:
        out.append(
            entry(
                f"{ID_PREFIX}男子-pre2024",
                [
                    "荒玉男子の旧コース区間記録は？",
                    "荒玉男子2023年までの区間歴代記録",
                    "荒玉駅伝男子の再編前の区間記録",
                    "男子荒玉の2023以前の大会区間記録一覧",
                    "荒玉男子旧コースの歴代区間記録は？",
                ],
                (
                    "荒玉駅伝男子・2023年以前コース（再編前）の大会区間記録（2023年ボード表示）です。"
                    f" 総合大会記録 {men_old['total']}（{men_old['total_team']}/{men_old['total_era']}）。"
                    f" 区間: {legs_summary(men_old)}。"
                    " 2024年以降の現行コース記録とは別です。"
                ),
                [SRC],
                ["aragyoku", "record", "meet-records", "男子", "pre2024"],
            )
        )

    return out


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
    marker = "aragyoku-leg-records"
    if marker not in text:
        text = text.replace(
            "brush-up-prepared-qa-ux2: meet-docダンプ・薄い案内・None漏れをユーザー向けに整理",
            "brush-up-prepared-qa-ux2: meet-docダンプ・薄い案内・None漏れをユーザー向けに整理\n\n"
            "  aragyoku-leg-records: 荒玉男女の区間歴代記録（ボード上部一覧）を想定Q&A化。",
            1,
        )
    # bump total
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
    text = MEET_RECORDS.read_text(encoding="utf-8")
    entries = build_entries(text)
    print(f"generated {len(entries)} entries")
    if args.dry_run:
        for e in entries:
            print("-", e["id"], len(e["questions"]), "qs")
            print(" ", e["answer"][:220].replace("\n", " "))
        return 0
    added, skipped = append_entries(entries)
    print(f"wrote {FAQ} (+{added} / skip {skipped})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
