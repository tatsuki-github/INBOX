#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2025 なごみ駅伝: 成績表の文字起こし出力 + レース前 SB 予想 + 予実比較。"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import generate_nagomi_order_sb_preview as g
import nagomi_2025_results_data as results

ROOT = Path(__file__).resolve().parents[1]
MEET_DIR = (
    ROOT
    / "input/external/drive/shared/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会"
)
CORPUS_MEET = (
    ROOT
    / "input/idaten-corpus/drive-text/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会"
)
SB_2025 = ROOT / "input/external/sb/middle-school/by-year/2025-sb-adopted.json"
AS_OF = "2025-09-20"
EVENT_DATE = "2025-09-21"
PHOTO_SRC = Path(
    "/Users/t-tsuchiyama/.cursor/projects/Users-t-tsuchiyama-Desktop-INBOX/assets/"
    "_____-864034b4-3c86-437b-8d39-70542b4565c8.jpg"
)
MEN_PDF_1 = Path("/Users/t-tsuchiyama/Downloads/男子の結果1.pdf")
MEN_PDF_2 = Path("/Users/t-tsuchiyama/Downloads/男子の結果2.pdf")


def _dual_write(text: str, name: str) -> None:
    MEET_DIR.mkdir(parents=True, exist_ok=True)
    CORPUS_MEET.mkdir(parents=True, exist_ok=True)
    (MEET_DIR / name).write_text(text, encoding="utf-8")
    (CORPUS_MEET / name).write_text(text, encoding="utf-8")


def copy_source_binaries() -> list[str]:
    copied: list[str] = []
    MEET_DIR.mkdir(parents=True, exist_ok=True)
    mapping = [
        (MEN_PDF_1, MEET_DIR / "男子の結果1.pdf"),
        (MEN_PDF_2, MEET_DIR / "男子の結果2.pdf"),
        (PHOTO_SRC, MEET_DIR / "女子成績表.jpg"),
    ]
    for src, dest in mapping:
        if src.exists():
            shutil.copy2(src, dest)
            copied.append(dest.name)
    return copied


def teams_to_order(teams: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, team in enumerate(teams, start=1):
        legs = [(leg.get("name") or "") for leg in team["legs"]]
        while len(legs) < 4:
            legs.append("")
        no = team["rank"] if team.get("rank") is not None else 90 + i
        rows.append(
            {
                "no": no,
                "team": team["team"],
                "legs": legs[:4],
                "reserves": ["", "", ""],
            }
        )
    return rows


def annotate_2025(report: dict[str, Any], gender: str) -> dict[str, Any]:
    report["year"] = 2025
    report["event_date"] = EVENT_DATE
    report["as_of_note"] = (
        f"as_of: {AS_OF} / 出走は {EVENT_DATE} 成績表 / "
        "2025年度 SB採用（レース前日以前のみ。ナイター・Notion 上書きなし）"
    )
    report["sb_note"] = (
        f"- **SB反映**: `2025-sb-adopted.json` の SB採用行。"
        f"日付が {AS_OF} 以前だけを使う（レース後の記録で後知恵しない）"
    )
    report["heading"] = f"なごみ駅伝2025 {gender} 出走メンバー × レース前SB・予想"
    report["pdf_title"] = f"なごみ駅伝2025 {gender} 出走×SB・予想"
    report["pdf_lead"] = (
        f"出走は{EVENT_DATE}成績表。SBは2025年度・{AS_OF}以前。"
        "参考順位は記録欠落区間を中央値補完。"
    )
    return report


def attach_actuals(report: dict[str, Any], teams: list[dict[str, Any]]) -> None:
    by_team = {t["team"]: t for t in teams}
    for row in report["teams"]:
        actual = by_team.get(row["team"])
        if not actual:
            continue
        row["actual_rank"] = actual.get("rank")
        row["actual_total"] = g.parse_seconds(actual.get("total"))
        row["official"] = actual.get("official", True)
        for det, leg in zip(row["legs"], actual["legs"]):
            det["actual"] = g.parse_seconds(leg.get("split"))
            det["actual_rank"] = leg.get("split_rank")
            det["grade"] = leg.get("grade")
            if det["pred"] is not None and det["actual"] is not None:
                det["delta"] = det["actual"] - det["pred"]
            else:
                det["delta"] = None
        if row.get("actual_total") is not None and row.get("total_ref") is not None:
            row["total_delta"] = row["actual_total"] - row["total_ref"]
        else:
            row["total_delta"] = None


def signed_sec(delta: float | None) -> str:
    if delta is None:
        return ""
    sign = "+" if delta >= 0 else "−"
    return f"{sign}{g.fmt_time(abs(delta), 1)}"


def render_results_md(gender: str, teams: list[dict[str, Any]], leg_km: int, total_km: int) -> str:
    ev = results.EVENT
    lines = [
        f"# {ev['title']} {gender}成績表",
        "",
        f"- 日付: {ev['date']}",
        f"- 会場: {ev['venue']}",
        f"- 各区 {leg_km}km / 総合 {total_km}km",
        "- 上段: 選手氏名・学年 / 中段: (順位)通過記録 / 下段: (順位)区間記録",
        "- 文字起こし正本（女子は成績表写真、男子は結果PDF）。OCR 後に目視校正。",
        "",
        "| 順位 | チーム | 総合 | 1区 | 2区 | 3区 | 4区 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for team in teams:
        rank = "OP" if team.get("rank") is None else str(team["rank"])
        total = team.get("total") or "—"
        cells = []
        for leg in team["legs"]:
            if not leg.get("name"):
                cells.append("")
                continue
            grade = f"{leg['grade']}" if leg.get("grade") is not None else ""
            split_r = f"({leg['split_rank']})" if leg.get("split_rank") is not None else ""
            cells.append(f"{leg['name']}{grade} {split_r}{leg.get('split') or ''}")
        lines.append("| " + " | ".join([rank, team["team"], total, *cells]) + " |")
    lines.append("")
    lines.append("## 区間詳細")
    lines.append("")
    for team in teams:
        rank = "OP" if team.get("rank") is None else f"{team['rank']}位"
        total = team.get("total") or "—"
        lines.append(f"### {rank} {team['team']}　総合 {total}")
        lines.append("")
        lines.append("| 区間 | 選手 | 学年 | 区間 | 区間順 | 通過 | 通過順 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for i, leg in enumerate(team["legs"], start=1):
            if not leg.get("name") and not leg.get("split"):
                lines.append(f"| {i}区 |  |  |  |  |  |  |")
                continue
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"{i}区",
                        str(leg.get("name") or ""),
                        str(leg.get("grade") or ""),
                        str(leg.get("split") or ""),
                        str(leg.get("split_rank") or ""),
                        str(leg.get("cum") or ""),
                        str(leg.get("cum_rank") or ""),
                    ]
                )
                + " |"
            )
        lines.append("")
    if gender == "女子":
        lines.append("## 校正メモ")
        lines.append("")
        lines.append("- 1区 金栗PROJECT は SB 照合で **坂井優花**（写真の「優／凛」を校正）。")
        lines.append("- 荒尾第四 2区 **松山杏海**、京陵 2区 **小原佳澄**、4区 **川崎百香** は SB 所属と一致。")
        lines.append("- 鹿南 2区 **塚本夏穂** は SB 照合（写真「夏稀」を校正）。")
        lines.append("- SB に無い氏名（積房愛梨、堀山結衣、吉野紗也香 等）は成績表の漢字をそのまま残した。")
        lines.append("")
    else:
        lines.append("## 校正メモ")
        lines.append("")
        lines.append("- 岱明B 1区は成績表どおり **山本哲瑠**（メモ `岱明の結果.md` の「悟瑠」は誤記）。")
        lines.append("- 南関A 4区 **田中翔大**、金栗B **津口晃誠** / **松浦眞大**、京陵B **小森謙吾** は SB 照合。")
        lines.append("- SB に無い氏名は成績表の読みを残した。")
        lines.append("")
    return "\n".join(lines)


def render_gap_markdown(women: dict[str, Any], men: dict[str, Any]) -> str:
    lines = [
        "# なごみ駅伝2025 SB予想と実績の乖離",
        "",
        f"出走: {EVENT_DATE} 成績表。予想: 2025年度 SB採用（{AS_OF} 以前）に 2026 と同じ換算式。",
        "",
        "## 読み方",
        "",
        "- **差** は `実績 − 予想`。プラスは SB 換算より遅かった。",
        "- 予想総合は参考順位と同じ（欠測区間は中央値補完。※）。",
        "- 完全記録のみのチームは 4 区間とも SB 由来の予想がある。",
        "",
    ]
    for report in (women, men):
        gend = report["gender"]
        lines.append(f"## {gend}")
        lines.append("")
        deltas = [
            t["total_delta"]
            for t in report["teams"]
            if t.get("official", True) and t.get("total_delta") is not None
        ]
        if deltas:
            mae = sum(abs(x) for x in deltas) / len(deltas)
            mean = sum(deltas) / len(deltas)
            lines.append(
                f"- 公式完走かつ予想総合あり: {len(deltas)} チーム / "
                f"平均差 `{signed_sec(mean)}` / MAE `{g.fmt_time(mae, 1)}`"
            )
        lines.append("")
        lines.append("| 実順 | チーム | 実総合 | 予想総合 | 差 | 予想順 | 順位差 | 補完 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        official = [t for t in report["teams"] if t.get("official", True) and t.get("actual_rank")]
        for t in official:
            rank_delta = ""
            if t.get("rank_ref") and t.get("actual_rank"):
                rank_delta = str(t["actual_rank"] - t["rank_ref"])
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(t.get("actual_rank") or ""),
                        t["team"],
                        g.fmt_clock(t.get("actual_total")),
                        g.fmt_clock(t.get("total_ref")),
                        signed_sec(t.get("total_delta")),
                        str(t.get("rank_ref") or ""),
                        rank_delta,
                        "※" if t.get("imputed") else "",
                    ]
                )
                + " |"
            )
        lines.append("")
        lines.append(f"### {gend} 区間ごと")
        lines.append("")
        lines.append("| チーム | 区間 | 選手 | 実績 | 予想 | 差 | 備考 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for t in official:
            for det in t["legs"]:
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            t["team"],
                            f"{det['leg']}区",
                            det["name"] or "",
                            g.fmt_time(det.get("actual"), 0) if det.get("actual") is not None else "",
                            g.fmt_time(det.get("pred"), 1) if det.get("pred") is not None else "",
                            signed_sec(det.get("delta")),
                            det.get("note") or "",
                        ]
                    )
                    + " |"
                )
        lines.append("")
    lines.append("## 注意")
    lines.append("")
    lines.append("トラック SB と駅伝は路面・気象・タスキ条件が異なる。本表は換算式の後知恵検証用。")
    lines.append("")
    return "\n".join(lines)


def render_gap_pdf(women: dict[str, Any], men: dict[str, Any], path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font_name = "NotoSansJP"
    if g.FONT_PATH.exists():
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, str(g.FONT_PATH)))
    else:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        font_name = "HeiseiKakuGo-W5"
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "GapTitle", parent=styles["Title"], fontName=font_name, fontSize=14, leading=18
    )
    h_style = ParagraphStyle(
        "GapH", parent=styles["Heading2"], fontName=font_name, fontSize=11, leading=14, spaceBefore=8
    )
    cell = ParagraphStyle(
        "GapCell", parent=styles["Normal"], fontName=font_name, fontSize=6.5, leading=8
    )

    def p(text: str, style: ParagraphStyle = cell) -> Paragraph:
        return Paragraph(escape(text).replace("\n", "<br/>"), style)

    story: list[Any] = [
        p("なごみ駅伝2025 SB予想と実績の乖離", title_style),
        p(
            f"出走 {EVENT_DATE} / SB は {AS_OF} 以前の 2025-sb-adopted。"
            "差 = 実績 − 予想（プラスは換算より遅い）。",
            cell,
        ),
        Spacer(1, 4 * mm),
    ]
    for report in (women, men):
        story.append(p(report["gender"], h_style))
        header = ["実順", "チーム", "実総合", "予想", "差", "予想順", "順位差"]
        data: list[list[Any]] = [[p(h) for h in header]]
        official = [t for t in report["teams"] if t.get("official", True) and t.get("actual_rank")]
        for t in official:
            rank_delta = ""
            if t.get("rank_ref") and t.get("actual_rank"):
                rank_delta = str(t["actual_rank"] - t["rank_ref"])
            data.append(
                [
                    p(str(t.get("actual_rank") or "")),
                    p(t["team"]),
                    p(g.fmt_clock(t.get("actual_total"))),
                    p(g.fmt_clock(t.get("total_ref"))),
                    p(signed_sec(t.get("total_delta"))),
                    p(str(t.get("rank_ref") or "")),
                    p(rank_delta),
                ]
            )
        tbl = Table(
            data,
            colWidths=[12 * mm, 42 * mm, 18 * mm, 18 * mm, 18 * mm, 16 * mm, 16 * mm],
            repeatRows=1,
        )
        tbl.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F5")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D5DD")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(tbl)
        story.append(Spacer(1, 6 * mm))

    doc = SimpleDocTemplate(
        str(path),
        pagesize=landscape(A4),
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
        title="なごみ駅伝2025 予実比較",
    )
    doc.build(story)


def load_2025_sb(gender: str) -> dict[str, g.AthleteSB]:
    index, _ = g.load_sb_index(
        SB_2025,
        as_of=AS_OF,
        include_notion=False,
        include_nighter=False,
        gender=gender,
    )
    return index


def build_2025_report(gender: str, teams: list[dict[str, Any]]) -> dict[str, Any]:
    sb = load_2025_sb(gender)
    report = g.build_gender_report(gender, teams_to_order(teams), sb)
    annotate_2025(report, gender)
    attach_actuals(report, teams)
    return report


def write_results_json() -> None:
    payload = {
        "event": results.EVENT,
        "as_of_sb": AS_OF,
        "women": results.WOMEN,
        "men": results.MEN,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _dual_write(text, "成績表.json")


def main() -> int:
    copied = copy_source_binaries()
    print("copied binaries:", ", ".join(copied) or "(none)")
    write_results_json()
    women_md = render_results_md("女子", results.WOMEN, 2, 8)
    men_md = render_results_md("男子", results.MEN, 3, 12)
    _dual_write(women_md, "女子成績表.md")
    _dual_write(men_md, "男子成績表.md")

    women = build_2025_report("女子", results.WOMEN)
    men = build_2025_report("男子", results.MEN)

    for report, stem in (
        (women, "女子区間オーダー_SB予想"),
        (men, "男子区間オーダー_SB予想"),
    ):
        md = g.render_markdown(report)
        _dual_write(md, f"{stem}.md")
        pdf_path = MEET_DIR / f"{stem}.pdf"
        g.render_pdf(report, pdf_path)
        g.write_coverage_csv(report, MEET_DIR / f"{stem}_coverage.csv")
        g.write_coverage_csv(report, CORPUS_MEET / f"{stem}_coverage.csv")
        print(f"wrote {pdf_path}")

    gap_md = render_gap_markdown(women, men)
    _dual_write(gap_md, "予実比較.md")
    gap_pdf = MEET_DIR / "予実比較.pdf"
    render_gap_pdf(women, men, gap_pdf)
    print(f"wrote {gap_pdf}")

    for report in (women, men):
        for t in report["teams"]:
            if "岱明" in t["team"]:
                print(
                    report["gender"],
                    t["team"],
                    "actual",
                    g.fmt_clock(t.get("actual_total")),
                    "pred",
                    g.fmt_clock(t.get("total_ref")),
                    "delta",
                    signed_sec(t.get("total_delta")),
                    [(d["name"], g.fmt_time(d.get("actual"), 0), g.fmt_time(d.get("pred"), 1), signed_sec(d.get("delta"))) for d in t["legs"]],
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
