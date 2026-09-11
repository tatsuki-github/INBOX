#!/usr/bin/env python3
"""荒玉男子駅伝の年度別上位6校PDFを生成する。"""

from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "input/aragyoku/men_full_2012_2025.json"
OUTPUT = ROOT / "out/analysis/荒玉男子駅伝_上位6校.pdf"
FONT = ROOT / "assets/fonts/NotoSansJP-Regular.ttf"


class InvariantCanvas(Canvas):
    def __init__(self, *args, **kwargs):
        kwargs["invariant"] = 1
        super().__init__(*args, **kwargs)


def styles(font: str):
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName=font, fontSize=16, leading=22, spaceAfter=8),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=font, fontSize=12, leading=16, spaceBefore=3, spaceAfter=5),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName=font, fontSize=8.5, leading=12, textColor=colors.HexColor("#374151")),
        "note": ParagraphStyle("note", parent=base["Normal"], fontName=font, fontSize=8, leading=11, textColor=colors.HexColor("#92400E")),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontName=font, fontSize=6.5, leading=8),
    }


def p(value, style):
    return Paragraph(escape("" if value is None else str(value)), style)


def year_page(year: int, block: dict, st: dict) -> list:
    story = [Paragraph(f"{year}年 玉名荒尾中体連駅伝・男子 上位6校", st["h1"])]
    if block.get("date"):
        story.append(Paragraph(f"開催日: {escape(block['date'])}", st["body"]))
    if year == 2019:
        story.append(Paragraph(
            "注意: 2019年度男子は、Google Drive原画像の解像度が低く、選手名・学年・区間記録・総合記録を確定できません。推測値は掲載せず、unknown／—で表示します。",
            st["note"],
        ))
    story.append(Spacer(1, 2 * mm))
    for team in [t for t in block.get("teams", []) if t.get("rank", 99) <= 6]:
        story.append(Paragraph(
            escape(f"{team['rank']}位　{team['team']}　総合 {team.get('total') or '—'}"), st["body"]
        ))
        header = [p("区", st["cell"]), p("選手", st["cell"]), p("学年", st["cell"]), p("区間", st["cell"]), p("累積", st["cell"])]
        rows = [header]
        for leg in team.get("legs", []):
            rows.append([
                p(leg.get("leg"), st["cell"]),
                p(leg.get("name") or "unknown", st["cell"]),
                p(leg.get("grade") if leg.get("grade") is not None else "—", st["cell"]),
                p(leg.get("split") or "—", st["cell"]),
                p(leg.get("cumulative") or "—", st["cell"]),
            ])
        table = Table(rows, colWidths=[12 * mm, 48 * mm, 18 * mm, 28 * mm, 28 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.extend([table, Spacer(1, 2 * mm)])
    story.append(PageBreak())
    return story


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    if FONT.exists():
        pdfmetrics.registerFont(TTFont("NotoSansJP", str(FONT)))
        font = "NotoSansJP"
    else:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
        font = "HeiseiKakuGo-W5"
    st = styles(font)
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=10 * mm, title="荒玉男子駅伝 上位6校")
    story = [Paragraph("荒玉（玉名荒尾）中体連駅伝・男子 上位6校", st["title"]), Paragraph("対象年: 2012〜2025年 ／ 2019年度は原画像低解像度のため未確定値を明示", st["body"]), PageBreak()]
    for year in sorted((int(y) for y in data["years"]), reverse=True):
        story.extend(year_page(year, data["years"][str(year)], st))
    if isinstance(story[-1], PageBreak):
        story.pop()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, canvasmaker=InvariantCanvas)
    print(f"PDF 生成: {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
