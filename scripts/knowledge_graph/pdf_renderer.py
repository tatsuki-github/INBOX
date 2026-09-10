"""Render knowledge graph as a printable PDF snapshot (ReportLab)."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent.parent
KG_PDF_PATH = ROOT / "out" / "knowledge-graph.pdf"
DEFAULT_FONT = ROOT / "assets" / "fonts" / "NotoSansJP-Regular.ttf"
FONT_NAME = "NotoSansJP"
FALLBACK_FONT = "HeiseiKakuGo-W5"

TYPE_ORDER = [
    "Topic",
    "QueryHint",
    "Year",
    "Source",
    "Template",
    "Athlete",
    "Entity",
]


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


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text or "").replace("\n", "<br/>"), style)


def _refs_text(refs: list[str] | None, limit: int = 6) -> str:
    items = [str(r) for r in (refs or []) if r]
    if not items:
        return "—"
    shown = items[:limit]
    extra = len(items) - len(shown)
    text = "; ".join(shown)
    if extra > 0:
        text += f" …(+{extra})"
    return text


def write_knowledge_graph_pdf(graph: dict[str, Any], path: Path | None = None) -> Path:
    path = path or KG_PDF_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    font = register_font()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "KgTitle",
        parent=styles["Heading1"],
        fontName=font,
        fontSize=16,
        leading=20,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "KgH2",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=12,
        leading=16,
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "KgBody",
        parent=styles["Normal"],
        fontName=font,
        fontSize=9,
        leading=12,
    )
    cell_style = ParagraphStyle(
        "KgCell",
        parent=styles["Normal"],
        fontName=font,
        fontSize=7.5,
        leading=10,
    )
    muted_style = ParagraphStyle(
        "KgMuted",
        parent=styles["Normal"],
        fontName=font,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#555555"),
    )

    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        by_type[str(node.get("type") or "Entity")].append(node)

    story: list[Any] = []
    story.append(Paragraph("INBOX Knowledge Graph", title_style))
    story.append(
        _p(
            f"生成: {graph.get('generated_at') or '—'}  /  "
            f"nodes={len(nodes)}  edges={len(edges)}  version={graph.get('version')}",
            muted_style,
        )
    )
    story.append(
        _p(
            "ブラウザ可視化 HTML の印刷用スナップショットです。"
            "対話的なグラフではなく、ノード一覧と参照パスを PDF 化しています。",
            body_style,
        )
    )
    story.append(Spacer(1, 4 * mm))

    # Type summary
    summary_rows = [[_p("種別", cell_style), _p("件数", cell_style)]]
    ordered_types = [t for t in TYPE_ORDER if t in by_type] + sorted(
        t for t in by_type if t not in TYPE_ORDER
    )
    for t in ordered_types:
        summary_rows.append([_p(t, cell_style), _p(str(len(by_type[t])), cell_style)])
    summary = Table(summary_rows, colWidths=[40 * mm, 20 * mm])
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2128")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(summary)

    for type_name in ordered_types:
        group = sorted(by_type[type_name], key=lambda n: str(n.get("label") or n.get("id") or ""))
        story.append(Paragraph(f"{type_name}（{len(group)}）", h2_style))
        rows: list[list[Any]] = [
            [_p("ラベル", cell_style), _p("ヒント", cell_style), _p("参照", cell_style)]
        ]
        for node in group:
            rows.append(
                [
                    _p(str(node.get("label") or node.get("id") or ""), cell_style),
                    _p(str(node.get("hint") or "—"), cell_style),
                    _p(_refs_text(node.get("refs")), cell_style),
                ]
            )
        table = Table(rows, colWidths=[42 * mm, 62 * mm, 66 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2a343c")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f7f8")]),
                ]
            )
        )
        story.append(table)

    # Compact edge sample for Topics (routing relevance)
    topic_ids = {n["id"] for n in by_type.get("Topic", []) if n.get("id")}
    topic_edges = [e for e in edges if e.get("from") in topic_ids or e.get("to") in topic_ids]
    if topic_edges:
        story.append(Paragraph(f"Topic 関連エッジ（先頭 80 / 全 {len(topic_edges)}）", h2_style))
        edge_rows: list[list[Any]] = [
            [_p("from", cell_style), _p("rel", cell_style), _p("to", cell_style)]
        ]
        for edge in topic_edges[:80]:
            edge_rows.append(
                [
                    _p(str(edge.get("from") or ""), cell_style),
                    _p(str(edge.get("rel") or ""), cell_style),
                    _p(str(edge.get("to") or ""), cell_style),
                ]
            )
        edge_table = Table(edge_rows, colWidths=[70 * mm, 28 * mm, 72 * mm], repeatRows=1)
        edge_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2a343c")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]
            )
        )
        story.append(edge_table)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="INBOX Knowledge Graph",
        author="INBOX knowledge_graph",
    )
    doc.build(story)
    return path
