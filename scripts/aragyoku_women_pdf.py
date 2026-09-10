#!/usr/bin/env python3
"""荒玉女子駅伝 上位4校 × トラック走力 PDF レポート生成。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOINED = ROOT / "out/analysis/aragyoku_women_track_joined.json"
DEFAULT_PDF = ROOT / "out/analysis/荒玉女子駅伝_上位4校_トラック走力.pdf"
DEFAULT_FONT = ROOT / "assets/fonts/NotoSansJP-Regular.ttf"
FONT_NAME = "NotoSansJP"
FALLBACK_FONT = "HeiseiKakuGo-W5"

EVENTS = ("800m", "1000m", "1500m", "3000m")


def register_font(font_path: Path | None = None) -> str:
    path = font_path or DEFAULT_FONT
    if path.exists() and path.suffix.lower() in {".ttf", ".ttc"}:
        if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(FONT_NAME, str(path)))
        return FONT_NAME
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    if FALLBACK_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(FALLBACK_FONT))
    return FALLBACK_FONT


def shorten_url(url: str, max_len: int = 42) -> str:
    u = url.replace("https://", "").replace("http://", "")
    if len(u) <= max_len:
        return u
    return u[: max_len - 1] + "…"


def link_para(url: str | None, style: ParagraphStyle, label: str | None = None) -> Paragraph:
    if not url:
        return Paragraph("—", style)
    text = escape(label or shorten_url(url))
    href = escape(url, {'"': "&quot;"})
    return Paragraph(f'<a href="{href}" color="#1A56DB">{text}</a>', style)


def mark_with_link(pack: dict[str, Any] | None, style: ParagraphStyle) -> Paragraph:
    if not pack or not pack.get("mark"):
        return Paragraph("—", style)
    mark = escape(str(pack["mark"]))
    url = pack.get("url")
    if url:
        href = escape(url, {'"': "&quot;"})
        return Paragraph(f'<a href="{href}" color="#1A56DB">{mark}</a>', style)
    return Paragraph(mark, style)


def build_styles(font_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "AwTitle",
            parent=base["Title"],
            fontName=font_name,
            fontSize=16,
            leading=22,
            spaceAfter=6,
            textColor=colors.HexColor("#111827"),
        ),
        "h1": ParagraphStyle(
            "AwH1",
            parent=base["Heading1"],
            fontName=font_name,
            fontSize=13,
            leading=18,
            spaceBefore=4,
            spaceAfter=6,
            textColor=colors.HexColor("#111827"),
        ),
        "h2": ParagraphStyle(
            "AwH2",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=11,
            leading=15,
            spaceBefore=6,
            spaceAfter=4,
            textColor=colors.HexColor("#1F2937"),
        ),
        "body": ParagraphStyle(
            "AwBody",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#374151"),
        ),
        "note": ParagraphStyle(
            "AwNote",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=4,
        ),
        "cell": ParagraphStyle(
            "AwCell",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#111827"),
        ),
        "cell_small": ParagraphStyle(
            "AwCellSmall",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=6.5,
            leading=8.5,
            textColor=colors.HexColor("#374151"),
        ),
    }


def cover_page(data: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    meta = data["meta"]
    stats = meta.get("stats") or {}
    story: list[Any] = []
    story.append(Paragraph(escape(meta.get("title") or "荒玉女子駅伝トラック走力"), styles["title"]))
    story.append(
        Paragraph(
            f"対象年: {', '.join(str(y) for y in meta.get('years') or [])}　"
            f"欠落年: {', '.join(str(y) for y in meta.get('missing_years') or [])}",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            f"選手数 {stats.get('athletes', 0)} / "
            f"トラック記録あり {stats.get('with_any_track', 0)} / "
            f"SBあり {stats.get('with_sb', 0)} / "
            f"大会URLあり {stats.get('with_url', 0)}",
            styles["body"],
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            escape(meta.get("drive_source_note") or ""),
            styles["note"],
        )
    )
    story.append(
        Paragraph(
            escape(meta.get("guide_note") or ""),
            styles["note"],
        )
    )
    story.append(
        Paragraph(
            "タイムの青字は大会結果URLへのリンクです。クリックでブラウザが開きます。"
            " 2012〜2023年は利用可能なトラック記録資料がないため空欄です。"
            " 2025年のトラックDBは収録途中です。",
            styles["note"],
        )
    )
    story.append(
        Paragraph(
            f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            styles["note"],
        )
    )
    story.append(PageBreak())
    return story


def athlete_rows(team: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[list[Any]]:
    header = [
        Paragraph("<b>区</b>", styles["cell"]),
        Paragraph("<b>選手</b>", styles["cell"]),
        Paragraph("<b>学年</b>", styles["cell"]),
        Paragraph("<b>駅伝</b>", styles["cell"]),
        Paragraph("<b>目安</b>", styles["cell"]),
        Paragraph("<b>800 SB/直近</b>", styles["cell"]),
        Paragraph("<b>1000 SB/直近</b>", styles["cell"]),
        Paragraph("<b>1500 SB/直近</b>", styles["cell"]),
        Paragraph("<b>3000 SB/直近</b>", styles["cell"]),
        Paragraph("<b>換算メモ</b>", styles["cell"]),
    ]
    rows = [header]
    for ath in team.get("athletes") or []:
        te = ath.get("track_events") or {}

        def pair(event: str) -> Paragraph:
            ev = te.get(event) or {}
            sb = ev.get("sb")
            recent = ev.get("recent")
            parts = []
            if sb and sb.get("mark"):
                if sb.get("url"):
                    href = escape(sb["url"], {'"': "&quot;"})
                    parts.append(f'SB <a href="{href}" color="#1A56DB">{escape(sb["mark"])}</a>')
                else:
                    parts.append(f'SB {escape(sb["mark"])}')
            if recent and recent.get("mark"):
                same = sb and sb.get("mark") == recent.get("mark") and sb.get("url") == recent.get("url")
                if not same:
                    if recent.get("url"):
                        href = escape(recent["url"], {'"': "&quot;"})
                        parts.append(
                            f'直 <a href="{href}" color="#1A56DB">{escape(recent["mark"])}</a>'
                        )
                    else:
                        parts.append(f'直 {escape(recent["mark"])}')
            if not parts:
                return Paragraph("—", styles["cell_small"])
            return Paragraph("<br/>".join(parts), styles["cell_small"])

        est = ath.get("ekiden_estimate") or {}
        grade = ath.get("grade")
        rows.append(
            [
                Paragraph(str(ath.get("leg") or ""), styles["cell"]),
                Paragraph(escape(ath.get("name") or ""), styles["cell"]),
                Paragraph("" if grade in (None, "") else str(grade), styles["cell"]),
                Paragraph(escape(ath.get("ekiden_mark") or "—"), styles["cell"]),
                Paragraph(escape(est.get("estimated_mark") or "—"), styles["cell"]),
                pair("800m"),
                pair("1000m"),
                pair("1500m"),
                pair("3000m"),
                Paragraph(escape(est.get("note") or "—"), styles["cell_small"]),
            ]
        )
    return rows


def year_section(yblock: dict[str, Any], styles: dict[str, ParagraphStyle], font_name: str) -> list[Any]:
    story: list[Any] = []
    year = yblock["year"]
    date = yblock.get("date") or ""
    conf = yblock.get("source_confidence") or ""
    drive_id = yblock.get("source_file_id") or ""
    title = f"{year}年 玉名荒尾中体連駅伝・女子 上位4校"
    if date:
        title += f"（{date}）"
    story.append(Paragraph(escape(title), styles["h1"]))
    notes = []
    if conf:
        notes.append(f"画像照合: {conf}")
    if drive_id:
        drive_url = f"https://drive.google.com/file/d/{drive_id}/view"
        href = escape(drive_url, {'"': "&quot;"})
        notes.append(f'結果画像: <a href="{href}" color="#1A56DB">Drive</a>')
    seasons = yblock.get("sb_seasons") or []
    if seasons:
        notes.append(f"参照SBシーズン: {', '.join(seasons)}")
    if notes:
        story.append(Paragraph(" ／ ".join(notes), styles["note"]))

    col_widths = [
        8 * mm,
        22 * mm,
        10 * mm,
        14 * mm,
        14 * mm,
        25 * mm,
        25 * mm,
        25 * mm,
        25 * mm,
        45 * mm,
    ]

    for team in yblock.get("teams") or []:
        school = team.get("school") or ""
        total = team.get("total_mark") or "—"
        story.append(
            Paragraph(
                escape(f"{team.get('rank')}位　{school}　総合 {total}"),
                styles["h2"],
            )
        )
        data = athlete_rows(team, styles)
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#FAFAFA")],
                    ),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 3 * mm))

    story.append(PageBreak())
    return story


def missing_year_section(year: int, styles: dict[str, ParagraphStyle]) -> list[Any]:
    return [
        Paragraph(f"{year}年 玉名荒尾中体連駅伝・女子", styles["h1"]),
        Paragraph(
            "Google Drive「荒玉駅伝歴代」および公開Web情報を確認しましたが、"
            "女子結果の原資料を確認できませんでした。"
            "検証不能な値を補完せず、この年の上位4校・各区間記録・トラック記録は未掲載とします。",
            styles["body"],
        ),
        PageBreak(),
    ]


def build_pdf(data: dict[str, Any], output: Path, font_path: Path | None = None) -> Path:
    font_name = register_font(font_path)
    styles = build_styles(font_name)
    output.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output),
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=data["meta"].get("title") or "荒玉女子駅伝トラック走力",
    )
    story: list[Any] = []
    story.extend(cover_page(data, styles))
    year_blocks = {int(y["year"]): y for y in data.get("years") or []}
    missing_years = {int(year) for year in data.get("meta", {}).get("missing_years") or []}
    all_years = sorted(set(year_blocks) | missing_years, reverse=True)
    for year in all_years:
        if year in year_blocks:
            story.extend(year_section(year_blocks[year], styles, font_name))
        else:
            story.extend(missing_year_section(year, styles))
    if story and isinstance(story[-1], PageBreak):
        story.pop()
    doc.build(story)
    return output


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="荒玉女子駅伝トラック走力 PDF を生成します。")
    p.add_argument("--joined", type=Path, default=DEFAULT_JOINED)
    p.add_argument("--output", type=Path, default=DEFAULT_PDF)
    p.add_argument("--font", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.joined.exists():
        print(f"joined JSON がありません: {args.joined}", file=sys.stderr)
        print("先に scripts/aragyoku_women_track.py を実行してください。", file=sys.stderr)
        return 1
    data = json.loads(args.joined.read_text(encoding="utf-8"))
    path = build_pdf(data, args.output, font_path=args.font)
    print(f"PDF 生成: {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
