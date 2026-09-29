#!/usr/bin/env python3
"""Render the current formula forecast Markdown, including recent results, to PDF."""
from pathlib import Path
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, LongTable, TableStyle, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝/区間オーダー_数式予想.md'
OUTPUT = ROOT / 'output/pdf/荒玉中体連駅伝2026_数式予想と大会結果.pdf'


def inline(text):
    text = escape(text.replace('`', ''))
    text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',
                  r'<link href="\2" color="#176b9c">\1</link>', text)
    return text


def build():
    pdfmetrics.registerFont(TTFont('NotoJP', str(ROOT / 'assets/fonts/NotoSansJP-Regular.ttf')))
    styles = {
        'body': ParagraphStyle('Body', fontName='NotoJP', fontSize=9, leading=13, spaceAfter=5, wordWrap='CJK'),
        'cell': ParagraphStyle('Cell', fontName='NotoJP', fontSize=8, leading=11, wordWrap='CJK'),
        'h1': ParagraphStyle('H1', fontName='NotoJP', fontSize=17, leading=24, spaceAfter=10, keepWithNext=True),
        'h2': ParagraphStyle('H2', fontName='NotoJP', fontSize=13, leading=18, spaceBefore=10, spaceAfter=7, keepWithNext=True),
        'h3': ParagraphStyle('H3', fontName='NotoJP', fontSize=11, leading=16, spaceBefore=10, spaceAfter=5, keepWithNext=True),
    }
    width, height = landscape(A4)
    usable = width - 64
    story = []
    lines = SOURCE.read_text(encoding='utf-8').splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line == '---':
            i += 1
            continue
        if line == '出典資料:':
            source_lines = [Paragraph(line, styles['h3'])]
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i].strip().startswith('- S')):
                if lines[i].strip():
                    source_lines.append(Paragraph(inline(lines[i].strip()), styles['body']))
                i += 1
            story.append(KeepTogether(source_lines))
            continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', x) for x in cells):
                    rows.append(cells)
                i += 1
            n = len(rows[0])
            if n == 9 and rows[0][0] == '予想区間':
                weights = [38, 72, 67, 182, 68, 48, 55, 210, 37]
            elif n == 12:
                weights = [66, 32, 55, 78, 31, 57, 57, 37, 37, 50, 77, 57]
            else:
                weights = [30, 70, 50] + [110] * (n - 3)
            widths = [usable * w / sum(weights) for w in weights]
            table = LongTable([[Paragraph(inline(c), styles['cell']) for c in row] for row in rows],
                              colWidths=widths, repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dceaf3')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f4f7fa')]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW', (0, 0), (-1, 0), .6, colors.HexColor('#7698b0')),
                ('LINEBELOW', (0, 1), (-1, -1), .25, colors.HexColor('#d8e1e8')),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story += [table, Spacer(1, 8)]
            continue
        heading = re.match(r'^(#{1,3})\s+(.+)', line)
        if heading:
            level, text = len(heading[1]), heading[2]
            if ('男子 区間オーダー' in text or text.startswith('各選手の8月29日以降')
                    or text == '区間別データ' or text.startswith('総合予想')):
                story.append(PageBreak())
            story.append(Paragraph(inline(text), styles[f'h{level}']))
        else:
            story.append(Paragraph(inline(line), styles['body']))
        i += 1

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#d8e1e8'))
        canvas.line(32, 27, width - 32, 27)
        canvas.setFont('NotoJP', 8)
        canvas.setFillColor(colors.HexColor('#536477'))
        canvas.drawString(32, 15, '荒玉中体連駅伝 2026 | 数式予想・8/29以降の大会結果')
        canvas.drawRightString(width - 32, 15, str(doc.page))
        canvas.restoreState()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=(width, height), leftMargin=32, rightMargin=32,
                            topMargin=30, bottomMargin=38, title='荒玉中体連駅伝2026 数式予想と大会結果',
                            author='いだてん岱明', invariant=1)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == '__main__':
    build()
