#!/usr/bin/env python3
"""Improve prepared FAQ answer accuracy (ADR 059).

- Clean OCR analysis dumps → Drive-link answers; narrow questions to PDF/資料
- Rebuild 2026 school-expand / order preview answers from drive-text facts
- Add yearless per-leg distance Q&A from distance definitions
- Route 数式予想/戦力分析 questions onto structured preview entries

Usage:
  python3 scripts/improve_prepared_qa_accuracy.py --dry-run
  python3 scripts/improve_prepared_qa_accuracy.py && python3 scripts/sync_prepared_qa.py
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
DIST = ROOT / "docs" / "aragyoku-ekiden-distance-definitions.md"
MEET_DIR = (
    ROOT
    / "input"
    / "idaten-corpus"
    / "drive-text"
    / "大会"
    / "2026年度"
    / "1014-1015_荒玉中体連駅伝"
)
ARAGYOKU_FOLDER = "https://drive.google.com/drive/folders/1G8IlaBp9xVmXUynBAjV9ZZQPfFqzj4Yi"
OCR_PDF = {
    "男子": (
        "input/external/drive/shared/分析/2026年度荒玉男子.pdf",
        "https://drive.google.com/file/d/17wQY9f09Y6qPsp1rHkGGoiVMIs7QuuXA/view",
    ),
    "女子": (
        "input/external/drive/shared/分析/2026年荒玉女子.pdf",
        "https://drive.google.com/file/d/1d1oEtMhvMte6d0JvXhZMNL5GigTYcR-i/view",
    ),
}

MEN_LEGS_2024 = {
    1: "3.00km",
    2: "2.855km",
    3: "3.00km",
    4: "3.00km",
    5: "2.855km",
    6: "3.00km",
}
WOMEN_LEGS = {
    1: "3.00km",
    2: "1.855km",
    3: "2.00km",
    4: "2.00km",
    5: "3.00km",
}


def load_faq() -> dict:
    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise SystemExit("invalid FAQ")
    return data


def upsert(entries: list[dict], new_entries: list[dict]) -> tuple[int, int]:
    by_id = {e["id"]: i for i, e in enumerate(entries)}
    claimed = {q for e in entries for q in (e.get("questions") or [])}
    added = updated = 0
    for e in new_entries:
        eid = e["id"]
        qs = []
        for q in e["questions"]:
            if q in claimed and (
                eid not in by_id or q not in (entries[by_id[eid]].get("questions") or [])
            ):
                continue
            qs.append(q)
            claimed.add(q)
        if not qs:
            continue
        e["questions"] = qs
        if eid in by_id:
            old = entries[by_id[eid]]
            old["answer"] = e["answer"]
            old["sources"] = e["sources"]
            mq = list(old.get("questions") or [])
            for q in qs:
                if q not in mq:
                    mq.append(q)
            old["questions"] = mq
            tags = list(old.get("tags") or [])
            for t in e.get("tags") or []:
                if t not in tags:
                    tags.append(t)
            old["tags"] = tags
            updated += 1
        else:
            entries.append(e)
            by_id[eid] = len(entries) - 1
            added += 1
    return added, updated


def fix_ocr_entries(entries: list[dict]) -> int:
    n = 0
    for e in entries:
        eid = str(e.get("id") or "")
        if not eid.startswith("analysis-ocr-2026-"):
            continue
        gender = "男子" if "男子" in eid else "女子" if "女子" in eid else None
        if not gender:
            continue
        # chunk entries: keep narrow questions only; never return raw OCR dumps
        if re.search(r"-c\d+$", eid):
            e["questions"] = [
                q
                for q in (e.get("questions") or [])
                if "パート" in q or "メモ" in q or "OCR" in q
            ] or e["questions"][:1]
            e["answer"] = (
                f"2026年荒玉{gender}分析OCRの抜粋パートです。"
                f" 詳細は分析PDFを参照してください。"
                f" 資料: {OCR_PDF[gender][1]}\n"
            )
            n += 1
            continue
        pdf_rel, pdf_url = OCR_PDF[gender]
        e["questions"] = [
            f"2026年荒玉{gender}の分析PDFは？",
            f"今年の荒玉{gender}分析資料",
            f"荒玉{gender}の分析PDFを見せて",
            f"2026荒玉{gender}OCR資料は？",
        ]
        e["answer"] = (
            f"2026年荒玉駅伝{gender}の分析資料（PDF）です。"
            f" 資料: {pdf_url}"
            f" 数式予想や校別展開は「今年の荒玉戦力分析（校別）は？」"
            f"「2026荒玉{gender}の区間オーダー予想は？」で聞けます。\n"
        )
        e["sources"] = [pdf_rel.replace(".pdf", ".ocr.md"), pdf_rel]
        tags = list(e.get("tags") or [])
        for t in ("aragyoku", "analysis", "2026", gender, "pdf"):
            if t not in tags:
                tags.append(t)
        e["tags"] = tags
        n += 1
    return n


def summary_from_school_expand(path: Path, *, gender: str, limit_teams: int = 6) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    section = re.search(
        rf"##\s*{gender}\s*\n(.*?)(?=\n##\s+|\Z)",
        text,
        re.S,
    )
    if not section:
        return ""
    rows = re.findall(
        r"\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*([0-9:]+)\s*\|",
        section.group(1),
    )
    bits = [f"{r}位{school}（{tot}）" for r, school, tot in rows[:limit_teams]]
    return "、".join(bits)


def rebuild_preview_entries(entries: list[dict]) -> list[dict]:
    out: list[dict] = []
    expand = MEET_DIR / "校別展開_数式予想.md"
    men_sum = summary_from_school_expand(expand, gender="男子")
    women_sum = summary_from_school_expand(expand, gender="女子")
    if men_sum or women_sum:
        ans = (
            "2026年荒玉駅伝の校別展開・数式予想（基準日2026-09-27、大会2026-10-14、公式オーダー未着）です。"
            + (f" 男子上位: {men_sum}。" if men_sum else "")
            + (f" 女子上位: {women_sum}。" if women_sum else "")
            + " 断定順位ではなく説明可能な予想です。"
            + f" 資料: {ARAGYOKU_FOLDER}"
        )
        out.append(
            entry(
                "meet-2026-aragyoku-school-expand",
                [
                    "2026荒玉の校別展開予想は？",
                    "今年の荒玉戦力分析（校別）は？",
                    "荒玉2026の数式予想まとめ",
                    "今年の荒玉男子の数式予想は？",
                    "荒玉男子の戦力分析は？",
                    "2026年荒玉男子の校別展開は？",
                    "今年の荒玉女子の数式予想は？",
                    "荒玉女子の戦力分析は？",
                ],
                ans,
                [
                    "input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝/校別展開_数式予想.md",
                    "out/analysis/aragyoku_2026_formula_report.md",
                ],
                ["aragyoku", "analysis", "formula", "2026", "preview"],
            )
        )

    for gender, fname, tag in (
        ("男子", "男子区間オーダー_数式予想.md", "men-order"),
        ("女子", "女子区間オーダー_数式予想.md", "women-order"),
    ):
        p = MEET_DIR / fname
        if not p.exists():
            continue
        # Keep short pointer + top line facts from school expand for that gender
        top = summary_from_school_expand(expand, gender=gender, limit_teams=3)
        ans = (
            f"2026年荒玉駅伝{gender}の区間オーダー・数式予想です。"
            + (f" 校別合計の上位目安: {top}。" if top else "")
            + " 仮オーダーを含み、確定ではありません。"
            + f" 資料: {ARAGYOKU_FOLDER}"
        )
        out.append(
            entry(
                f"meet-2026-aragyoku-{tag}",
                [
                    f"2026荒玉{gender}の区間オーダー予想は？",
                    f"今年の荒玉{gender}オーダー予想",
                    f"荒玉{gender}の2026区間予想まとめ",
                    f"{gender}の荒玉数式オーダーは？",
                ],
                ans,
                [
                    f"input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝/{fname}",
                    "out/analysis/aragyoku_2026_formula_report.md",
                ],
                ["aragyoku", "analysis", "formula", "2026", gender],
            )
        )

    # also refresh meet-doc school expand answer if present
    for e in entries:
        if e.get("id") == "meet-doc-2026-荒玉中体連駅伝-校別展開_数式予想" and men_sum:
            e["answer"] = (
                "荒玉中体連駅伝（2026）の校別展開・数式予想です。"
                f" 男子上位: {men_sum}。女子上位: {women_sum}。"
                " 公式オーダー未着の仮予想です。"
                f" 資料: {ARAGYOKU_FOLDER}\n"
            )
    return out


def gen_leg_distances() -> list[dict]:
    out: list[dict] = []
    src = [
        "docs/aragyoku-ekiden-distance-definitions.md",
        "out/analysis/aragyoku-overview.md",
    ]
    for leg, dist in MEN_LEGS_2024.items():
        out.append(
            entry(
                f"aragyoku-distance-current-男子-leg{leg}",
                [
                    f"荒玉男子{leg}区の距離は？",
                    f"荒玉駅伝男子{leg}区は何km？",
                    f"男子{leg}区の距離を教えて",
                    f"荒玉男子{leg}区何キロ？",
                ],
                f"荒玉駅伝男子・現行（2024年以降）の{leg}区は{dist}です。",
                src,
                ["aragyoku", "distance", "男子", "current"],
            )
        )
    for leg, dist in WOMEN_LEGS.items():
        out.append(
            entry(
                f"aragyoku-distance-current-女子-leg{leg}",
                [
                    f"荒玉女子{leg}区の距離は？",
                    f"荒玉駅伝女子{leg}区は何km？",
                    f"女子{leg}区の距離を教えて",
                ],
                f"荒玉駅伝女子の{leg}区は{dist}です（全年度共通）。",
                src,
                ["aragyoku", "distance", "女子"],
            )
        )
    # multi-leg ask
    out.append(
        entry(
            "aragyoku-distance-current-男子-leg2-leg3",
            [
                "荒玉男子2区と3区の距離は？",
                "男子2区と3区は何km？",
                "荒玉駅伝男子2区3区の距離",
            ],
            "荒玉駅伝男子・現行（2024年以降）は2区2.855km、3区3.00kmです。",
            src,
            ["aragyoku", "distance", "男子", "current"],
        )
    )
    # genderless per-leg: men/women differ on several legs — answer both
    for leg in sorted(set(MEN_LEGS_2024) | set(WOMEN_LEGS)):
        md = MEN_LEGS_2024.get(leg)
        wd = WOMEN_LEGS.get(leg)
        if not md or not wd:
            continue
        out.append(
            entry(
                f"aragyoku-distance-current-both-leg{leg}",
                [
                    f"荒玉{leg}区の距離は？",
                    f"{leg}区の距離は？",
                    f"荒玉駅伝{leg}区は何km？",
                    f"{leg}区は何キロ？",
                ],
                (
                    f"荒玉駅伝{leg}区の距離は、男子（現行2024年以降）{md}、"
                    f"女子{wd}です。男女どちらかを指定すると片方だけ答えます。"
                ),
                src,
                ["aragyoku", "distance", "current"],
            )
        )
    # total distance (genderless + both)
    out.append(
        entry(
            "gap1000-overview-distance",
            [
                "荒玉男子の総距離は？",
                "荒玉男子コースの合計kmは？",
                "荒玉男子は何km？",
                "荒玉の総距離は？",
                "荒玉は何km？",
                "荒玉駅伝の合計距離は？",
                "荒玉コースの総距離",
            ],
            "荒玉男子の現行（2024年以降）合計距離は17.71km、2023年以前は19.71kmです。女子は11.855km（年度共通）です。",
            ["out/analysis/aragyoku-overview.md", *src],
            ["gap1000", "digest", "aragyoku", "distance"],
        )
    )
    # enrich overview with per-leg asks
    out.append(
        entry(
            "aragyoku-men-distance",
            [
                "荒玉男子の区間距離は？",
                "荒玉駅伝男子の距離を教えて",
                "男子の区間距離は？",
                "荒玉男子各区の距離は？",
            ],
            "荒玉駅伝男子・現行（2024年以降）の区間距離は、1区3.00km、2区2.855km、3区3.00km、4区3.00km、5区2.855km、6区3.00km（合計17.71km）です。2023年以前は別定義です。",
            src,
            ["aragyoku", "distance", "男子"],
        )
    )
    return out


def patch_formula_questions(entries: list[dict]) -> int:
    n = 0
    extras = {
        "formula-2026-男子-岱明中-order": [
            "岱明男子の区間予想まとめ",
            "岱明の男子区間予想をまとめて",
        ],
        "formula-2026-女子-岱明中-order": [
            "岱明女子の区間予想まとめ",
        ],
    }
    claimed = {q for e in entries for q in (e.get("questions") or [])}
    by = {e["id"]: e for e in entries}
    for eid, qs in extras.items():
        e = by.get(eid)
        if not e:
            continue
        cur = list(e.get("questions") or [])
        for q in qs:
            if q in cur or q in claimed:
                continue
            cur.append(q)
            claimed.add(q)
            n += 1
        e["questions"] = cur
    return n


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = load_faq()
    entries: list[dict] = data["entries"]

    ocr_n = fix_ocr_entries(entries)
    preview = rebuild_preview_entries(entries)
    distances = gen_leg_distances()
    formula_n = patch_formula_questions(entries)
    added, updated = upsert(entries, preview + distances)

    print(f"ocr cleaned: {ocr_n}")
    print(f"formula questions patched: {formula_n}")
    print(f"preview+distance upsert added={added} updated={updated}")
    print(f"total entries: {len(entries)}")

    if args.dry_run:
        for eid in (
            "analysis-ocr-2026-男子",
            "meet-2026-aragyoku-school-expand",
            "aragyoku-distance-current-男子-leg2",
        ):
            e = next(x for x in entries if x["id"] == eid)
            print("SAMPLE", eid, e["questions"][:3], "=>", e["answer"][:140].replace("\n", " "))
        return 0

    data["entries"] = entries
    data["total"] = len(entries)
    FAQ.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    print(f"wrote {FAQ}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
