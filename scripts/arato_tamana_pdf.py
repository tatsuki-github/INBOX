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
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from arato_tamana_ranking import (
    CategoryRankings,
    GenderRankingTable,
    compute_all_affiliation_rankings,
    format_seconds,
)
from arato_tamana_records import AffiliationSection, RecordRow, shorten_url


class _BookmarkDocTemplate(SimpleDocTemplate):
    """見出し Paragraph に PDF しおり（ブックマーク）を付与する。"""

    def __init__(self, *args: Any, bookmark_targets: dict[str, tuple[str, int]] | None = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._bookmark_targets = bookmark_targets or {}
        self._bookmarked: set[str] = set()

    def afterFlowable(self, flowable: Any) -> None:
        if not isinstance(flowable, Paragraph):
            return
        text = flowable.getPlainText()
        target = self._bookmark_targets.get(text)
        if target is None:
            return
        anchor, level = target
        if anchor in self._bookmarked:
            return
        self.canv.bookmarkPage(anchor)
        self.canv.addOutlineEntry(text, anchor, level, 0)
        self._bookmarked.add(anchor)

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


def _ranking_cell(
    text: str,
    style: ParagraphStyle,
    *,
    header: bool = False,
    align: str = "left",
) -> Paragraph:
    content = escape(str(text))
    if header:
        content = f"<b>{content}</b>"
    if align != "left":
        return Paragraph(f'<para align="{align}">{content}</para>', style)
    return Paragraph(content, style)


def _ranking_paragraph_styles(font_name: str) -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    return {
        "section": ParagraphStyle(
            "RankingSectionJP",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=13,
            leading=18,
            spaceBefore=8,
            spaceAfter=6,
            textColor=colors.HexColor("#1A1A1A"),
        ),
        "note": ParagraphStyle(
            "RankingNoteJP",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#666666"),
            spaceAfter=4,
        ),
        "gender": ParagraphStyle(
            "RankingGenderJP",
            parent=styles["Heading3"],
            fontName=font_name,
            fontSize=11,
            leading=15,
            spaceBefore=4,
            spaceAfter=4,
            textColor=colors.HexColor("#333333"),
        ),
        "header": ParagraphStyle(
            "RankingTableHeaderJP",
            fontName=font_name,
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#1A1A1A"),
        ),
        "cell": ParagraphStyle(
            "RankingTableCellJP",
            fontName=font_name,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1A1A1A"),
        ),
    }


def _gender_ranking_block(
    boys_ranking: GenderRankingTable,
    girls_ranking: GenderRankingTable,
    styles: dict[str, ParagraphStyle],
    *,
    page_break_before_girls: bool = True,
) -> list[Any]:
    story: list[Any] = [
        Paragraph("男子", styles["gender"]),
        _build_ranking_table(boys_ranking, styles["header"], styles["cell"]),
    ]
    if page_break_before_girls:
        story.append(PageBreak())
    else:
        story.append(Spacer(1, 4 * mm))
    story.extend(
        [
            Paragraph("女子", styles["gender"]),
            _build_ranking_table(girls_ranking, styles["header"], styles["cell"]),
        ]
    )
    return story


def _category_ranking_story(
    category: CategoryRankings,
    styles: dict[str, ParagraphStyle],
    *,
    page_break_before: bool = False,
) -> list[Any]:
    story: list[Any] = []
    if page_break_before:
        story.append(PageBreak())
    story.extend(
        [
            Paragraph(category.spec.title, styles["section"]),
            Paragraph(category.spec.note, styles["note"]),
            *_gender_ranking_block(category.boys, category.girls, styles),
        ]
    )
    return story


def _all_rankings_story(
    categories: list[CategoryRankings],
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    story: list[Any] = [
        Paragraph("所属別ランキング", styles["section"]),
        Paragraph(
            "800m / 1500m / 3000m の実記録と 3000m 予想タイムを、"
            "所属ごとに上位平均で順位付けしています。",
            styles["note"],
        ),
        Spacer(1, 2 * mm),
    ]
    for idx, category in enumerate(categories):
        story.extend(_category_ranking_story(category, styles, page_break_before=idx > 0))
    return story


def _ranking_bookmarks(categories: list[CategoryRankings]) -> dict[str, tuple[str, int]]:
    bookmarks: dict[str, tuple[str, int]] = {"所属別ランキング": ("ranking-index", 0)}
    for category in categories:
        bookmarks[category.spec.title] = (f"ranking-{category.spec.key}", 1)
    bookmarks["所属別 全記録一覧"] = ("records", 0)
    return bookmarks


def _build_ranking_table(
    table: GenderRankingTable,
    header_style: ParagraphStyle,
    cell_style: ParagraphStyle,
) -> Table:
    headers = ["順位", "所属", "人数"] + [f"上位{n}人平均" for n in table.top_ns]
    col_widths = [12 * mm, 46 * mm, 12 * mm] + [26 * mm] * len(table.top_ns)
    data: list[list[Any]] = [
        [
            _ranking_cell(h, header_style, header=True, align="center" if i != 1 else "left")
            for i, h in enumerate(headers)
        ]
    ]
    for entry in table.entries:
        data.append(
            [
                _ranking_cell(entry.rank, cell_style, align="center"),
                _ranking_cell(entry.affiliation, cell_style),
                _ranking_cell(entry.athlete_count, cell_style, align="center"),
                *[
                    _ranking_cell(_format_average(entry.averages.get(n)), cell_style, align="center")
                    for n in table.top_ns
                ],
            ]
        )

    ranking_table = Table(data, colWidths=col_widths, repeatRows=1)
    ranking_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
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


def _doc_template(output_path: Path, title: str, *, bookmarks: dict[str, tuple[str, int]] | None = None) -> SimpleDocTemplate:
    return _BookmarkDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=title,
        bookmark_targets=bookmarks,
    )


def build_ranking_pdf(
    sections: list[AffiliationSection],
    output_path: Path,
    title: str,
    font_path: Path | None = None,
) -> Path:
    """所属別ランキングのみの PDF を生成する。"""
    font_name = register_font(font_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    categories = compute_all_affiliation_rankings(sections)
    ranking_styles = _ranking_paragraph_styles(font_name)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "RankingTitleJP",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=24,
        spaceAfter=8,
    )
    meta_style = ParagraphStyle(
        "RankingMetaJP",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#444444"),
        spaceAfter=6,
    )

    doc = _doc_template(
        output_path,
        title,
        bookmarks=_ranking_bookmarks(categories),
    )
    story: list[Any] = [
        Paragraph(title, title_style),
        Paragraph(
            f"生成日時: {generated_at}　｜　所属数: {len(sections)}",
            meta_style,
        ),
        Spacer(1, 4 * mm),
        *_all_rankings_story(categories, ranking_styles),
    ]
    doc.build(story)
    return output_path


def build_pdf(
    sections: list[AffiliationSection],
    output_path: Path,
    title: str,
    font_path: Path | None = None,
) -> Path:
    font_name = register_font(font_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    categories = compute_all_affiliation_rankings(sections)
    doc = _doc_template(
        output_path,
        title,
        bookmarks=_ranking_bookmarks(categories),
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
    records_section_style = ParagraphStyle(
        "RecordsSectionJP",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=13,
        leading=18,
        spaceBefore=8,
        spaceAfter=6,
        textColor=colors.HexColor("#1A1A1A"),
    )
    ranking_styles = _ranking_paragraph_styles(font_name)

    from arato_tamana_records import group_records_by_gender

    total_records = sum(len(section.records) for section in sections)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    ranking_page_count = len(categories) * 2

    story: list[Any] = [
        Paragraph(title, title_style),
        Paragraph(
            f"生成日時: {generated_at}　｜　所属数: {len(sections)}　｜　記録数: {total_records}",
            meta_style,
        ),
        Paragraph(
            f"1〜{ranking_page_count}ページ: 所属別ランキング（800m/1500m/3000m 実記録 + 3000m 予想）"
            "　｜　以降: 全記録一覧",
            meta_style,
        ),
        Spacer(1, 4 * mm),
        *_all_rankings_story(categories, ranking_styles),
        PageBreak(),
        Paragraph("所属別 全記録一覧", records_section_style),
        Spacer(1, 4 * mm),
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
