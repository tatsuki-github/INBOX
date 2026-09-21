#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""なごみ駅伝 2025/2026 の SB 予実ギャップ分析 HTML/MD を生成する。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_nagomi_2025_sb_vs_actual as nagomi2025  # noqa: E402
import generate_nagomi_order_sb_preview as g  # noqa: E402
import nagomi_2025_results_data as results2025  # noqa: E402
import nagomi_2026_results_data as results2026  # noqa: E402
import nagomi_sb_gap_analysis as gap  # noqa: E402

OUT_HTML = ROOT / "out/analysis/nagomi_sb_gap_analysis.html"

MEET_2025 = nagomi2025.MEET_DIR
CORPUS_2025 = nagomi2025.CORPUS_MEET
MEET_2026 = ROOT / "input/external/drive/shared/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会"
CORPUS_2026 = ROOT / "input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会"

ORDER_2026 = {
    "女子": CORPUS_2026 / "女子区間オーダーリスト.md",
    "男子": CORPUS_2026 / "男子区間オーダーリスト.md",
}


def _dual_write(text: str, meet: Path, corpus: Path, name: str) -> None:
    meet.mkdir(parents=True, exist_ok=True)
    corpus.mkdir(parents=True, exist_ok=True)
    (meet / name).write_text(text, encoding="utf-8")
    (corpus / name).write_text(text, encoding="utf-8")


def build_2025_year() -> dict[str, Any]:
    women = nagomi2025.build_2025_report("女子", results2025.WOMEN)
    men = nagomi2025.build_2025_report("男子", results2025.MEN)
    genders = []
    for report in (women, men):
        teams, legs = gap.build_analysis_rows(report, year=2025)
        genders.append({"gender": report["gender"], "teams": teams, "legs": legs, "report": report})
    return {
        "year": 2025,
        "event_date": nagomi2025.EVENT_DATE,
        "as_of": nagomi2025.AS_OF,
        "genders": genders,
    }


def build_2026_report(gender: str, result_teams: list[dict[str, Any]]) -> dict[str, Any]:
    order_path = ORDER_2026[gender]
    order_rows = g.parse_order_md(order_path)
    sb_index, _ = g.load_sb_index(gender=gender)
    report = g.build_gender_report(gender, order_rows, sb_index)
    report["year"] = 2026
    report["event_date"] = results2026.EVENT["date"]
    report["as_of_note"] = "as_of: 2026-09-18 オーダー / 2026年度 SB + ナイター更新"
    gap.attach_actuals_by_no(report, result_teams)
    return report


def build_2026_year() -> dict[str, Any]:
    women = build_2026_report("女子", results2026.WOMEN)
    men = build_2026_report("男子", results2026.MEN)
    genders = []
    for report in (women, men):
        teams, legs = gap.build_analysis_rows(report, year=2026)
        genders.append({"gender": report["gender"], "teams": teams, "legs": legs, "report": report})
    return {
        "year": 2026,
        "event_date": results2026.EVENT["date"],
        "as_of": "2026-09-18",
        "genders": genders,
    }


def _public_genders(year_block: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"gender": gnd["gender"], "teams": gnd["teams"], "legs": gnd["legs"]}
        for gnd in year_block["genders"]
    ]


def main() -> int:
    y2025 = build_2025_year()
    y2026 = build_2026_year()
    full_payload = {
        "years": [
            {
                "year": y["year"],
                "event_date": y["event_date"],
                "as_of": y["as_of"],
                "genders": _public_genders(y),
            }
            for y in (y2025, y2026)
        ]
    }
    html_full = gap.render_html(full_payload)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html_full, encoding="utf-8")
    print(f"wrote {OUT_HTML}")

    for y, meet, corpus in (
        (y2025, MEET_2025, CORPUS_2025),
        (y2026, MEET_2026, CORPUS_2026),
    ):
        year_payload = {
            "years": [
                {
                    "year": y["year"],
                    "event_date": y["event_date"],
                    "as_of": y["as_of"],
                    "genders": _public_genders(y),
                }
            ]
        }
        md = gap.render_gap_markdown(
            year=y["year"],
            event_date=y["event_date"],
            as_of=y["as_of"],
            genders=_public_genders(y),
        )
        html_year = gap.render_html(year_payload)
        _dual_write(md, meet, corpus, "予実比較.md")
        _dual_write(html_year, meet, corpus, "予実比較.html")
        print(f"wrote {meet / '予実比較.md'}")

    for y in (y2025, y2026):
        for gnd in y["genders"]:
            counts = gap.summarize_counts(gnd["teams"])
            print(
                y["year"],
                gnd["gender"],
                "teams",
                counts,
                "legs_known",
                gap.summarize_counts([x for x in gnd["legs"] if x.get("delta") is not None]),
            )
            for t in gnd["teams"]:
                if "岱明" in t["team"]:
                    print(
                        " ",
                        t["team"],
                        gap.signed_sec(t.get("total_delta")),
                        gap.label_ja(t["class"]),
                    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
