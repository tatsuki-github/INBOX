#!/usr/bin/env python3
"""Generate per-school / per-club roster prepared FAQ from 2026 track records.

いだてん岱明は Notion 公式名簿（id: roster）を正とする。
他校・クラブは notion_records_2026 に競技記録がある選手一覧として返す
（公式部員名簿ではない旨を明記）。

Usage:
  python3 scripts/generate_prepared_qa_school_rosters.py
  python3 scripts/generate_prepared_qa_school_rosters.py --dry-run
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

from generate_prepared_qa_bulk import entry, slug  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
RECORDS = ROOT / "out" / "analysis" / "notion_records_2026.json"
ID_PREFIX = "roster-aff-"
SEASON = 2026

# affiliation in notion_records → display + question aliases
AFFILIATIONS: list[dict] = [
    {
        "aff": "玉名附中",
        "display": "玉名高校附属中（玉名附中）",
        "aliases": [
            "玉名附属中",
            "玉名付属中",
            "玉名高校附属中",
            "玉高附属",
            "玉名附中",
            "玉名附属",
            "玉名付属",
        ],
    },
    {
        "aff": "南関中",
        "display": "南関中",
        "aliases": ["南関中", "南関"],
    },
    {
        "aff": "天水中",
        "display": "天水中",
        "aliases": ["天水中", "天水"],
    },
    {
        "aff": "玉名中",
        "display": "玉名中",
        "aliases": ["玉名中", "玉名"],
    },
    {
        "aff": "荒尾第四中",
        "display": "荒尾第四中（荒尾四）",
        "aliases": ["荒尾第四中", "荒尾第四", "荒尾四", "荒尾四中"],
    },
    {
        "aff": "荒尾三中",
        "display": "荒尾第三中（荒尾三）",
        "aliases": ["荒尾第三中", "荒尾第三", "荒尾三", "荒尾三中"],
    },
    {
        "aff": "荒尾海陽中",
        "display": "荒尾海陽中",
        "aliases": ["荒尾海陽中", "荒尾海陽"],
    },
    {
        "aff": "長洲中",
        "display": "長洲中",
        "aliases": ["長洲中", "長洲"],
    },
    {
        "aff": "玉・有明中",
        "display": "有明中（玉・有明中）",
        "aliases": ["有明中", "有明", "玉・有明中"],
    },
    {
        "aff": "ATRC",
        "display": "ATRC",
        "aliases": ["ATRC", "atrc"],
    },
    {
        "aff": "金栗PROJECT",
        "display": "金栗PROJECT",
        "aliases": ["金栗PROJECT", "金栗プロジェクト", "金栗project"],
    },
    {
        "aff": "玉名アスリーツ",
        "display": "玉名アスリーツ",
        "aliases": ["玉名アスリーツ", "アスリーツ"],
    },
    {
        "aff": "玉東クラブ",
        "display": "玉東クラブ",
        "aliases": ["玉東クラブ"],
    },
    {
        "aff": "熊本大附中",
        "display": "熊本大附中",
        "aliases": ["熊本大附中", "熊本大附属中"],
    },
]

GENDER_SHORT = {"男子": "男", "女子": "女", "男": "男", "女": "女"}


def load_people_by_aff() -> dict[str, dict[str, dict]]:
    rows = json.loads(RECORDS.read_text(encoding="utf-8"))
    by: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        aff = str(r.get("affiliation") or "").strip()
        name = str(r.get("name") or "").strip()
        if not aff or not name:
            continue
        grade = r.get("grade")
        try:
            grade_i = int(grade) if grade is not None else None
        except (TypeError, ValueError):
            grade_i = None
        gender = str(r.get("gender") or "").strip()
        cur = by[aff].get(name)
        if cur is None:
            by[aff][name] = {"grade": grade_i, "gender": gender}
        else:
            if grade_i is not None:
                cur["grade"] = grade_i
            if gender and not cur.get("gender"):
                cur["gender"] = gender
    return by


def format_roster(display: str, people: dict[str, dict]) -> str:
    by_grade: dict[int, list[str]] = {3: [], 2: [], 1: []}
    unknown: list[str] = []
    for name in sorted(people):
        meta = people[name]
        g = meta.get("grade")
        sex = GENDER_SHORT.get(meta.get("gender") or "", "")
        label = f"{name}（{sex}）" if sex else name
        if g in by_grade:
            by_grade[g].append(label)
        else:
            unknown.append(label)
    parts = []
    for g in (3, 2, 1):
        if by_grade[g]:
            parts.append(f"{g}年: " + "、".join(by_grade[g]))
    if unknown:
        parts.append("学年不明: " + "、".join(unknown))
    n = len(people)
    body = " ".join(parts) if parts else "（該当選手なし）"
    return (
        f"{display}の生徒・選手一覧（{SEASON}年度・競技記録がある選手{n}名）です。 "
        f"{body} "
        "公式の部員名簿ではなく、2026年度の中学生記録に登場した選手です。個人の連絡先は扱いません。"
    )


def questions_for(aliases: list[str]) -> list[str]:
    qs: list[str] = []
    for a in aliases:
        qs.extend(
            [
                f"{a}の生徒一覧",
                f"{a}の生徒一覧は？",
                f"{a}の部員名簿",
                f"{a}の部員名簿は？",
                f"{a}の部員一覧",
                f"{a}の陸上部員は誰？",
                f"{a}の選手一覧",
                f"{SEASON}年の{a}の生徒一覧",
                f"今年の{a}の部員名簿",
            ]
        )
    return qs


def gen_entries() -> list[dict]:
    by_aff = load_people_by_aff()
    out: list[dict] = []
    for conf in AFFILIATIONS:
        people = by_aff.get(conf["aff"]) or {}
        if len(people) < 1:
            continue
        eid = f"{ID_PREFIX}{slug(conf['aff'])}"
        ans = format_roster(conf["display"], people)
        out.append(
            entry(
                eid,
                questions_for(conf["aliases"]),
                ans,
                [
                    "out/analysis/notion_records_2026.json",
                    f"out/analysis/arato-tamana-teams/{conf['aff']}.md",
                ],
                ["roster", "affiliation", SEASON, conf["aff"]],
            )
        )
    return out


def tighten_daiming_roster(entries: list[dict]) -> None:
    """汎用『名簿を見せて』が他校質問を吸わないよう、岱明専用へ寄せる。"""
    for e in entries:
        if e.get("id") != "roster":
            continue
        qs = [
            q
            for q in (e.get("questions") or [])
            if q
            not in {
                "部員名簿は？",
                "名簿を見せて",
            }
        ]
        # 岱明明示の汎用質問は残しつつ、曖昧質問は岱明付きに置換
        qs.extend(
            [
                "岱明の部員名簿は？",
                "いだてん岱明の名簿を見せて",
                "岱明の名簿を見せて",
            ]
        )
        # dedupe
        seen: set[str] = set()
        cleaned = []
        for q in qs:
            if q in seen:
                continue
            seen.add(q)
            cleaned.append(q)
        e["questions"] = cleaned
        # clarify answer already says いだてん岱明
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = list(data.get("entries") or [])
    before = len(entries)
    entries = [e for e in entries if not str(e.get("id", "")).startswith(ID_PREFIX)]
    print(f"removed old {ID_PREFIX}* : {before - len(entries)}")

    tighten_daiming_roster(entries)

    new_entries = gen_entries()
    print(f"new affiliation rosters: {len(new_entries)}")
    for e in new_entries:
        if "玉名附" in e["id"] or e["id"].endswith("ATRC") or "南関" in e["id"]:
            print("SAMPLE", e["id"])
            print(e["answer"][:400])
            print("---")

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

    if args.dry_run:
        return 0

    merged = entries + cleaned
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
    if "所属別生徒一覧" not in note:
        data["note"] = note.rstrip() + "\n所属別生徒一覧（記録登場選手）を収録。岱明は公式名簿。\n"
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
    print(f"wrote {FAQ.relative_to(ROOT)} total={len(uniq)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
