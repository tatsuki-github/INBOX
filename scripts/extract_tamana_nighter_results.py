#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第25回玉名郡ナイター PDF（または raw txt）から中学生全結果.md を生成する。

Usage:
  python scripts/extract_tamana_nighter_results.py
  python scripts/extract_tamana_nighter_results.py --pdf /path/to/results.pdf
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEET = ROOT / "input/external/drive/shared/大会/2026年度/0829_玉名郡ナイター中・長距離記録会"
CORPUS = ROOT / "input/idaten-corpus/drive-text/大会/2026年度/0829_玉名郡ナイター中・長距離記録会"
DEFAULT_PDF = MEET / "第25回ナイター中長距離記録会_結果.pdf"
DEFAULT_RAW = MEET / "第25回ナイター中長距離記録会_結果_raw.txt"
OUT_MD = MEET / "全結果.md"

CLUB_HINTS = ("金栗PROJECT", "ATRC", "アスリーツ", "クラブ", "中学校", "RC")


def extract_pdf_text(pdf: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def distance_from_section(sec: str) -> str | None:
    if "1500" in sec:
        return "1500m"
    if "800" in sec:
        return "800m"
    if "3000" in sec:
        return "3000m"
    return None


def is_ms_row(section: str, grade: str, school: str) -> bool:
    if "小学" in section:
        return False
    if "高校・一般" in section and "1500" in section:
        return False
    if grade in ("中1", "中2", "中3"):
        return True
    if grade.isdigit() and 12 <= int(grade) <= 15 and "中学校" in school:
        return True
    if not grade and any(h in school for h in CLUB_HINTS):
        if "小学" not in section and "高校・一般" not in section:
            if "FORMULA" in school:
                return False
            return "1500" in section or "800" in section or "3000" in section
    return False


def parse_rows(raw: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    section = None
    for line in raw.splitlines():
        s = line.strip()
        if "※結果確定" in s:
            section = s
            continue
        if not s or s.startswith("順位"):
            continue
        body = re.sub(r"^\d+\s+\d+\s+", "", s)
        tm = re.search(r"(\d+)\s*分\s*(\d+)\s*秒\s*(\d+)\s*$", body)
        if not tm:
            continue
        before = body[: tm.start()].strip()
        gm = re.search(r"(中[123]|小[1-6]|高[123]|\d+)\s*$", before)
        if gm:
            grade = gm.group(1)
            left = before[: gm.start()].strip()
        else:
            grade = ""
            left = before
        nm = re.match(r"^(\S+)\s+(\S+)\s+(.+)$", left)
        if nm:
            name = f"{nm.group(1)} {nm.group(2)}"
            school = nm.group(3).strip()
        else:
            nm2 = re.match(r"^(\S+)\s+(\S+)\s*(.*)$", left)
            if not nm2:
                continue
            name = f"{nm2.group(1)} {nm2.group(2)}"
            school = (nm2.group(3) or "").strip()
        dist = distance_from_section(section or "")
        if not dist or not is_ms_row(section or "", grade, school):
            continue
        mins, secs, frac = int(tm.group(1)), int(tm.group(2)), tm.group(3)
        rows.append(
            {
                "distance": dist,
                "name": name,
                "school": school,
                "grade": grade or "—",
                "mark": f"{mins}:{secs:02d}.{frac}",
            }
        )
    return rows


def render_md(rows: list[dict[str, str]]) -> str:
    by_dist: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        by_dist[r["distance"]].append(r)
    lines = [
        "大会名: 第25回玉名郡ナイター中・長距離記録会",
        "日付: 2026-08-29",
        "ステータス: done",
        "場所: 和水町総合グラウンド",
        "ソース: 第25回ナイター中長距離記録会_結果.pdf（全校）",
        "",
        "中学生のみ抽出（小学・高校・一般は除外。年齢12–15かつ中学校所属、学年欠落のクラブ所属は含む）。",
        "",
    ]
    for dist in ("800m", "1500m", "3000m"):
        lines.append(f"## {dist}")
        lines.append("")
        lines.append("| 氏名 | 所属 | 学年 | 記録 |")
        lines.append("| --- | --- | --- | --- |")
        for r in by_dist[dist]:
            lines.append(f"| {r['name']} | {r['school']} | {r['grade']} | {r['mark']} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    args = parser.parse_args()

    if args.pdf.exists():
        raw = extract_pdf_text(args.pdf)
        args.raw.write_text(raw, encoding="utf-8")
        print(f"wrote {args.raw} ({len(raw)} chars)")
    elif args.raw.exists():
        raw = args.raw.read_text(encoding="utf-8")
        print(f"using existing raw {args.raw}")
    else:
        raise SystemExit(f"neither pdf nor raw found: {args.pdf} / {args.raw}")

    rows = parse_rows(raw)
    text = render_md(rows)
    OUT_MD.write_text(text, encoding="utf-8")
    CORPUS.mkdir(parents=True, exist_ok=True)
    (CORPUS / "全結果.md").write_text(text, encoding="utf-8")
    print(f"wrote {OUT_MD} ({len(rows)} middle-school rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
