"""ReportLab による荒尾・玉名地区 中学生記録 PDF 生成。"""

from __future__ import annotations

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
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from arato_tamana_ranking import GenderRankingTable, compute_affiliation_rankings, format_seconds
from arato_tamana_records import AffiliationSection, RecordRow, shorten_url

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FONT = ROOT / "assets" / "fonts" / "NotoSansJP-Regular.ttf"
FONT_NAME = "NotoSansJP"
FALLBACK_FONT = "HeiseiKakuGo-W5"

COLUMNS = ["名前", "学年", "性別", "距離", "記録", "日付", "URL"]
COL_WIDTHS = [28 * mm, 12 * mm, 12 * mm, 16 * mm, 24 * mm, 24 * mm, 48 * mm]


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


def _record_display(row: RecordRow, cell_style: ParagraphStyle) -> list[Any]:
    time_display = row.time_text
    if row.sb_adopted and time_display and "★" not in time_display:
        time_display = f"{time_display} ★"
    grade = "" if row.grade is None else str(row.grade)

    if row.url:
        label = escape(shorten_url(row.url))
        href = escape(row.url, {'"': "&quot;"})
        url_cell: Any = Paragraph(
            f'<a href="{href}" color="#1A56DB">{label}</a>',
            cell_style,
        )
    else:
        url_cell = ""

    return [
        row.name,
        grade,
        row.gender,
        row.distance,
        time_display,
        row.date,
        url_cell,
    ]


def _format_average(value: float | None) -> str:
    if value is None:
        return "—"
    return format_seconds(value)


def _build_ranking_table(table: GenderRankingTable, font_name: str) -> Table:
    headers = ["順位", "所属", "人数"] + [f"上位{n}人平均" for n in table.top_ns]
    col_widths = [12 * mm, 42 * mm, 12 * mm] + [24 * mm] * len(table.top_ns)
    data: list[list[Any]] = [headers]
    for entry in table.entries:
        row = [
            str(entry.rank),
            entry.affiliation,
            str(entry.athlete_count),
        ]
        row.extend(_format_average(entry.averages.get(n)) for n in table.top_ns)
        data.append(row)

    ranking_table = Table(data, colWidths=col_widths, repeatRows=1)
    ranking_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), font_name, 8),
                ("FONT", (0, 0), (-1, 0), font_name, 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return ranking_table


def _build_table(rows: list[RecordRow], font_name: str) -> Table:
    cell_style = ParagraphStyle(
        "TableCell",
        fontName=font_name,
        fontSize=8,
        leading=10,
    )
    data: list[list[Any]] = [COLUMNS]
    for row in rows:
        data.append(_record_display(row, cell_style))

    table = Table(data, colWidths=COL_WIDTHS, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), font_name, 8),
                ("FONT", (0, 0), (-1, 0), font_name, 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1A1A1A")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def build_pdf(
    sections: list[AffiliationSection],
    output_path: Path,
    title: str,
    font_path: Path | None = None,
) -> Path:
    font_name = register_font(font_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=title,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleJP",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=24,
        spaceAfter=8,
    )
    meta_style = ParagraphStyle(
        "MetaJP",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#444444"),
        spaceAfter=6,
    )
    section_style = ParagraphStyle(
        "SectionJP",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=13,
        leading=18,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor("#1A1A1A"),
    )
    gender_style = ParagraphStyle(
        "GenderJP",
        parent=styles["Heading3"],
        fontName=font_name,
        fontSize=11,
        leading=15,
        spaceBefore=4,
        spaceAfter=4,
        textColor=colors.HexColor("#333333"),
    )
    ranking_section_style = ParagraphStyle(
        "RankingSectionJP",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=13,
        leading=18,
        spaceBefore=8,
        spaceAfter=6,
        textColor=colors.HexColor("#1A1A1A"),
    )
    ranking_note_style = ParagraphStyle(
        "RankingNoteJP",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#666666"),
        spaceAfter=4,
    )

    from arato_tamana_records import group_records_by_gender

    total_records = sum(len(section.records) for section in sections)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    boys_ranking, girls_ranking = compute_affiliation_rankings(sections)

    story: list[Any] = [
        Paragraph(title, title_style),
        Paragraph(
            f"生成日時: {generated_at}　｜　所属数: {len(sections)}　｜　記録数: {total_records}",
            meta_style,
        ),
        Spacer(1, 4 * mm),
        Paragraph("所属別ランキング（3000m 予想タイム）", ranking_section_style),
        Paragraph(
            "各選手の 3000m SB → 1500m SB（+15秒/km換算）→ 800m SB（+10秒/km→1500m→3000m）"
            " の順で予想タイムを算出し、所属内の上位平均で順位付けしています。",
            ranking_note_style,
        ),
        Paragraph("男子", gender_style),
        _build_ranking_table(boys_ranking, font_name),
        Spacer(1, 3 * mm),
        Paragraph("女子", gender_style),
        _build_ranking_table(girls_ranking, font_name),
        Spacer(1, 6 * mm),
    ]

    for section in sections:
        story.append(
            Paragraph(f"{section.affiliation}（{len(section.records)}件）", section_style)
        )
        for gender, gender_rows in group_records_by_gender(section.records):
            story.append(Paragraph(f"{gender}（{len(gender_rows)}件）", gender_style))
            story.append(_build_table(gender_rows, font_name))
            story.append(Spacer(1, 2 * mm))
        story.append(Spacer(1, 2 * mm))

    doc.build(story)
    return output_path
