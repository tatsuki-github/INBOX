#!/usr/bin/env python3
"""Build the evidence-backed Aragyoku Ekiden 2026 comprehensive playbook."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from statistics import mean, median
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table,
    TableStyle, KeepTogether,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('/Users/t-tsuchiyama/Documents/Codex/2026-09-14/new-chat/outputs/荒玉駅伝2026徹底対策.pdf')
FONT = ROOT / 'assets/fonts/NotoSansJP-Regular.ttf'
MEN = ROOT / 'input/aragyoku/men_full_2012_2025.json'
WOMEN = ROOT / 'input/aragyoku/women_full_2012_2025.json'
WEATHER = ROOT / 'weather/aratama-ekiden-tamana-jma.csv'
MEN_RANK = ROOT / 'out/analysis/2026_men_1500m_pb_school_ranking.md'
WOMEN_RANK = ROOT / 'out/analysis/2026_women_800m_1500m_pb_school_ranking.md'
PACE = ROOT / 'out/analysis/aragyoku_top6_historical_average_pace.md'
TRANSCRIPTS = ROOT / 'input/aragyoku/transcripts'
SB_2026 = ROOT / 'input/external/sb/middle-school/by-year/2026-sb-adopted.json'

NAVY = colors.HexColor('#142B4A')
BLUE = colors.HexColor('#1C5A8A')
SKY = colors.HexColor('#EAF3FA')
GOLD = colors.HexColor('#C59528')
GREEN = colors.HexColor('#26734D')
RED = colors.HexColor('#A12E2E')
GREY = colors.HexColor('#616A73')
LIGHT = colors.HexColor('#F4F6F8')
FONT_NAME = 'NotoSansJP'


def secs(value):
    if not value or value in {'-', '—'}:
        return None
    parts = str(value).strip().split(':')
    try:
        return sum(int(x) * 60 ** (len(parts) - i - 1) for i, x in enumerate(parts))
    except ValueError:
        return None


def fmt(seconds, hours=False):
    if seconds is None:
        return '—'
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f'{h}:{m:02d}:{s:02d}' if h or hours else f'{m}:{s:02d}'


def pace(seconds, km):
    return f'{int(seconds/km)//60}:{int(seconds/km)%60:02d}/km' if seconds and km else '—'


def esc(text):
    return escape(str(text)).replace('\n', '<br/>')


class PlaybookDoc(BaseDocTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._heading_count = 0

    def beforeDocument(self):
        self._heading_count = 0
        super().beforeDocument()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style = flowable.style.name
            if style in {'H1', 'H2'}:
                self._heading_count += 1
                key = f'h{self._heading_count}'
                level = 0 if style == 'H1' else 1
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(flowable.getPlainText(), key, level, False)
                self.notify('TOCEntry', (level, flowable.getPlainText(), self.page, key))


def footer(canvas, doc):
    canvas.saveState()
    page = canvas.getPageNumber()
    if page > 1:
        canvas.setStrokeColor(colors.HexColor('#D5DDE5'))
        canvas.line(17*mm, 12*mm, A4[0]-17*mm, 12*mm)
        canvas.setFillColor(GREY)
        canvas.setFont(FONT_NAME, 7.2)
        canvas.drawString(17*mm, 7.5*mm, '荒玉駅伝2026 徹底対策  |  根拠に基づく作戦・練習・当日運用')
        canvas.drawRightString(A4[0]-17*mm, 7.5*mm, f'{page}')
    canvas.restoreState()


def styles():
    base = getSampleStyleSheet()
    return {
        'cover': ParagraphStyle('cover', parent=base['Title'], fontName=FONT_NAME, fontSize=28,
            leading=38, alignment=TA_CENTER, textColor=NAVY, spaceAfter=8*mm),
        'coverSub': ParagraphStyle('coverSub', parent=base['Normal'], fontName=FONT_NAME, fontSize=12,
            leading=20, alignment=TA_CENTER, textColor=GREY),
        'H1': ParagraphStyle('H1', parent=base['Heading1'], fontName=FONT_NAME, fontSize=17,
            leading=25, textColor=NAVY, spaceBefore=5*mm, spaceAfter=4*mm, keepWithNext=True),
        'H2': ParagraphStyle('H2', parent=base['Heading2'], fontName=FONT_NAME, fontSize=12,
            leading=18, textColor=BLUE, spaceBefore=4*mm, spaceAfter=2.5*mm, keepWithNext=True),
        'body': ParagraphStyle('body', parent=base['BodyText'], fontName=FONT_NAME, fontSize=8.5,
            leading=14, textColor=colors.HexColor('#1F2933'), spaceAfter=2.4*mm),
        'small': ParagraphStyle('small', parent=base['BodyText'], fontName=FONT_NAME, fontSize=7.2,
            leading=10.5, textColor=GREY, spaceAfter=1.5*mm),
        'callout': ParagraphStyle('callout', parent=base['BodyText'], fontName=FONT_NAME, fontSize=9,
            leading=14, textColor=NAVY, leftIndent=4*mm, rightIndent=4*mm, spaceBefore=2*mm, spaceAfter=3*mm),
        'table': ParagraphStyle('table', parent=base['BodyText'], fontName=FONT_NAME, fontSize=6.6,
            leading=8.4, textColor=colors.HexColor('#1F2933')),
        'tableHead': ParagraphStyle('tableHead', parent=base['BodyText'], fontName=FONT_NAME, fontSize=6.7,
            leading=8.5, textColor=colors.white, alignment=TA_CENTER),
        'appendix': ParagraphStyle('appendix', parent=base['BodyText'], fontName=FONT_NAME, fontSize=5.8,
            leading=7.1, textColor=colors.HexColor('#222222')),
        'appendixHead': ParagraphStyle('appendixHead', parent=base['BodyText'], fontName=FONT_NAME,
            fontSize=5.8, leading=7, textColor=colors.white, alignment=TA_CENTER),
    }


S = styles()


def P(text, style='body'):
    return Paragraph(esc(text), S[style])


def rich(text, style='body'):
    return Paragraph(text, S[style])


def heading(text, level=1):
    return Paragraph(esc(text), S['H1' if level == 1 else 'H2'])


def table(rows, widths, header=True, style='table', repeat=1, align=None):
    formatted = []
    for idx, row in enumerate(rows):
        st = 'tableHead' if header and idx == 0 else style
        formatted.append([cell if hasattr(cell, 'wrap') else P(cell, st) for cell in row])
    t = Table(formatted, colWidths=widths, repeatRows=repeat if header else 0, hAlign=align or 'LEFT')
    commands = [
        ('FONTNAME', (0,0), (-1,-1), FONT_NAME), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#CDD6DF')),
        ('LEFTPADDING', (0,0), (-1,-1), 2.2*mm), ('RIGHTPADDING', (0,0), (-1,-1), 2.2*mm),
        ('TOPPADDING', (0,0), (-1,-1), 1.2*mm), ('BOTTOMPADDING', (0,0), (-1,-1), 1.2*mm),
    ]
    if header:
        commands += [('BACKGROUND', (0,0), (-1,0), NAVY), ('TEXTCOLOR', (0,0), (-1,0), colors.white)]
    for i in range(1 if header else 0, len(rows)):
        if i % 2 == 0:
            commands.append(('BACKGROUND', (0,i), (-1,i), LIGHT))
    t.setStyle(TableStyle(commands))
    return t


def callout(title, text, color=SKY):
    content = rich(f'<b>{esc(title)}</b><br/>{esc(text)}', 'callout')
    t = Table([[content]], colWidths=[176*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), color), ('BOX', (0,0), (-1,-1), 0.35, colors.HexColor('#C6D4E0')),
        ('LEFTPADDING', (0,0), (-1,-1), 3*mm), ('RIGHTPADDING', (0,0), (-1,-1), 3*mm),
        ('TOPPADDING', (0,0), (-1,-1), 1*mm), ('BOTTOMPADDING', (0,0), (-1,-1), 1*mm),
    ]))
    return t


def source_note(paths):
    return P('根拠: ' + ' / '.join(paths), 'small')


CHART_COLORS = [colors.HexColor('#1C5A8A'), colors.HexColor('#C59528'), colors.HexColor('#26734D'), colors.HexColor('#A12E2E'), colors.HexColor('#7654A3'), colors.HexColor('#3F788F')]


def chart_note(text):
    return P('図の読み方: ' + text, 'small')


def vbar_chart(title, labels, series, legend_labels, unit='', height=70*mm, value_min=None, value_max=None):
    """Vector bar chart; all values are computed from cited source data."""
    width = 176 * mm
    d = Drawing(width, height)
    d.add(String(0, height - 10, title, fontName=FONT_NAME, fontSize=9.5, fillColor=NAVY))
    flat = [v for row in series for v in row]
    if not flat:
        d.add(String(0, height/2, '有効な数値データがないため、グラフは描画していません。', fontName=FONT_NAME, fontSize=9, fillColor=GREY))
        d.add(String(1, 5, unit, fontName=FONT_NAME, fontSize=6.3, fillColor=GREY))
        return d
    chart = VerticalBarChart()
    chart.x, chart.y = 30, 21
    chart.width, chart.height = width - 42, height - 40
    chart.data = series
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontName = FONT_NAME
    chart.categoryAxis.labels.fontSize = 6.2
    chart.categoryAxis.labels.dy = -7
    chart.categoryAxis.labels.angle = 0
    chart.valueAxis.labels.fontName = FONT_NAME
    chart.valueAxis.labels.fontSize = 6.2
    chart.valueAxis.labelTextFormat = '%.0f'
    chart.valueAxis.valueMin = value_min if value_min is not None else min(0, min(flat))
    chart.valueAxis.valueMax = value_max if value_max is not None else max(flat) * 1.10
    if chart.valueAxis.valueMax <= chart.valueAxis.valueMin:
        chart.valueAxis.valueMax = chart.valueAxis.valueMin + 1
    chart.valueAxis.forceZero = False
    chart.bars.strokeColor = None
    for idx in range(len(series)):
        chart.bars[idx].fillColor = CHART_COLORS[idx % len(CHART_COLORS)]
    d.add(chart)
    d.add(String(1, 5, unit, fontName=FONT_NAME, fontSize=6.3, fillColor=GREY))
    if legend_labels:
        legend = Legend()
        legend.x, legend.y = 35, height - 21
        legend.fontName, legend.fontSize = FONT_NAME, 6.5
        legend.dx, legend.dy = 7, 7
        legend.deltax = 55
        legend.colorNamePairs = [(CHART_COLORS[i % len(CHART_COLORS)], label) for i, label in enumerate(legend_labels)]
        d.add(legend)
    return d


def line_chart(title, points, legend_labels, unit='', height=70*mm, value_min=None, value_max=None):
    """Vector line chart using numeric x locations and explicit year labels."""
    width = 176 * mm
    d = Drawing(width, height)
    d.add(String(0, height - 10, title, fontName=FONT_NAME, fontSize=9.5, fillColor=NAVY))
    chart = LinePlot()
    chart.x, chart.y = 30, 21
    chart.width, chart.height = width - 42, height - 40
    chart.data = points
    yvals = [y for series in points for _, y in series]
    chart.yValueAxis.valueMin = value_min if value_min is not None else min(yvals) - max(1, (max(yvals)-min(yvals))*0.1)
    chart.yValueAxis.valueMax = value_max if value_max is not None else max(yvals) + max(1, (max(yvals)-min(yvals))*0.1)
    chart.yValueAxis.labels.fontName, chart.yValueAxis.labels.fontSize = FONT_NAME, 6.2
    chart.xValueAxis.labels.fontName, chart.xValueAxis.labels.fontSize = FONT_NAME, 6.2
    chart.xValueAxis.valueMin = min(x for series in points for x, _ in series)
    chart.xValueAxis.valueMax = max(x for series in points for x, _ in series)
    chart.xValueAxis.valueStep = 2
    for idx in range(len(points)):
        chart.lines[idx].strokeColor = CHART_COLORS[idx % len(CHART_COLORS)]
        chart.lines[idx].strokeWidth = 1.7
    d.add(chart)
    d.add(String(1, 5, unit, fontName=FONT_NAME, fontSize=6.3, fillColor=GREY))
    legend = Legend(); legend.x, legend.y = 35, height - 21
    legend.fontName, legend.fontSize, legend.dx, legend.dy, legend.deltax = FONT_NAME, 6.5, 7, 7, 55
    legend.colorNamePairs = [(CHART_COLORS[i % len(CHART_COLORS)], label) for i, label in enumerate(legend_labels)]
    d.add(legend)
    return d


def distance(year, gender):
    if gender == '女子':
        return [3, 1.855, 2, 2, 3]
    return [3, 2.855, 3, 3, 2.855, 3] if int(year) >= 2024 else [3.95, 3.05, 2.855, 2.855, 3, 4]


def load():
    return json.loads(MEN.read_text(encoding='utf-8')), json.loads(WOMEN.read_text(encoding='utf-8'))


def summary(dataset, gender):
    out = []
    podiums = Counter()
    for year, entry in sorted(dataset['years'].items()):
        kms = sum(distance(year, gender))
        teams = [t for t in entry['teams'] if secs(t.get('total'))]
        for t in teams:
            if t['rank'] <= 3: podiums[t['team']] += 1
        if teams:
            winner = teams[0]
            out.append({'year':year, 'teams':len(teams), 'winner':winner['team'], 'time':winner['total'],
                        'winner_sec':secs(winner['total']), 'winner_pace':pace(secs(winner['total']), kms), 'km':kms})
    return out, podiums


def historical_target_rows(dataset, gender):
    values = defaultdict(list)
    for year, entry in dataset['years'].items():
        km = sum(distance(year, gender))
        for t in entry['teams']:
            val = secs(t.get('total'))
            if val is not None and t['rank'] <= 6:
                values[t['rank']].append((val, km))
    rows = [['目標順位', '採用年度数', '加重平均ペース', '参考総合時間（現行距離換算）']]
    current_km = 17.71 if gender == '男子' else 11.855
    for rank in range(1, 7):
        pairs = values[rank]
        secpkm = sum(v for v, _ in pairs)/sum(k for _, k in pairs)
        rows.append([f'{rank}位', str(len(pairs)), pace(secpkm*current_km, current_km), fmt(secpkm*current_km)])
    return rows


def rank_markdown_rows(path, heading):
    text = path.read_text(encoding='utf-8')
    pos = text.find(heading)
    if pos < 0: return []
    segment = text[pos:].split('\n## ', 1)[0]
    result = []
    for line in segment.splitlines():
        if re.match(r'^\|\s*\d+', line):
            cells = [x.strip() for x in line.strip('|').split('|')]
            if len(cells) >= 4:
                result.append(cells[:4])
    return result


def weather_summary():
    with WEATHER.open(encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    byday = defaultdict(list)
    for row in rows:
        byday[row['開催日']].append(row)
    result=[]
    for day, rs in sorted(byday.items(), reverse=True):
        temps=[float(r['気温_C']) for r in rs if r['気温_C']]
        winds=[float(r['平均風速_m_s']) for r in rs if r['平均風速_m_s']]
        result.append([day, f'{min(temps):.1f}-{max(temps):.1f}℃' if temps else '—',
            f'{max(winds):.1f}m/s' if winds else '—', ' / '.join(sorted(set(r['風向'] for r in rs if r['風向'])),)])
    return result


def validate_dataset(dataset, gender):
    issues=[]
    for year, entry in dataset['years'].items():
        for team in entry['teams']:
            expected = 6 if gender == '男子' else 5
            if len(team['legs']) != expected: issues.append(f'{year} {gender} {team["team"]}: 区間数')
            if secs(team.get('total')) is not None:
                known=[secs(x.get('split')) for x in team['legs']]
                if all(v is not None for v in known) and sum(known) != secs(team['total']):
                    issues.append(f'{year} {gender} {team["team"]}: 区間和')
    return issues


def percentile(values, p):
    """Linear percentile, deliberately small and dependency-free."""
    values = sorted(values)
    if not values:
        return None
    pos = (len(values) - 1) * p
    lo, hi = int(pos), min(int(pos) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def dynamics(dataset, gender):
    """Compute only observations available in the canonical result-board JSON."""
    legs = 6 if gender == '男子' else 5
    per_leg = {leg: [] for leg in range(1, legs + 1)}
    spreads = {leg: [] for leg in range(1, legs + 1)}
    winner_leads = {leg: [0, 0] for leg in range(1, legs + 1)}
    winner_positions = {leg: [] for leg in range(1, legs + 1)}
    move_rows = {leg: [] for leg in range(2, legs + 1)}
    record_count = Counter()
    races = 0
    for year, entry in sorted(dataset['years'].items()):
        teams = [t for t in entry['teams'] if t.get('rank') and t.get('legs')]
        if not teams:
            continue
        races += 1
        winner = min(teams, key=lambda t: t['rank'])
        for leg_no in range(1, legs + 1):
            km = distance(year, gender)[leg_no - 1]
            vals = []
            for team in teams:
                leg = next((x for x in team['legs'] if x.get('leg') == leg_no), None)
                sec = secs(leg.get('split')) if leg else None
                if sec is not None:
                    per_leg[leg_no].append(sec / km)
                    vals.append(sec)
                    if leg.get('split_record'):
                        record_count[leg_no] += 1
            if len(vals) >= 2:
                spreads[leg_no].append(max(vals) - min(vals))
            wleg = next((x for x in winner['legs'] if x.get('leg') == leg_no), None)
            wrank = wleg.get('passing_rank') if wleg else None
            if isinstance(wrank, int):
                winner_positions[leg_no].append(wrank)
                winner_leads[leg_no][1] += 1
                if wrank == 1:
                    winner_leads[leg_no][0] += 1
            if leg_no > 1:
                for team in teams:
                    prev = next((x for x in team['legs'] if x.get('leg') == leg_no - 1), None)
                    now = next((x for x in team['legs'] if x.get('leg') == leg_no), None)
                    if prev and now and isinstance(prev.get('passing_rank'), int) and isinstance(now.get('passing_rank'), int):
                        move_rows[leg_no].append(prev['passing_rank'] - now['passing_rank'])
    demand = []
    for leg_no in range(1, legs + 1):
        vals = per_leg[leg_no]
        demand.append([f'{leg_no}区', str(len(vals)), pace(percentile(vals, .25), 1), pace(median(vals), 1), pace(percentile(vals, .75), 1),
                       pace(min(vals), 1), fmt(median(spreads[leg_no])) if spreads[leg_no] else '—', str(record_count[leg_no])])
    control = []
    for leg_no in range(1, legs + 1):
        lead, known = winner_leads[leg_no]
        positions = winner_positions[leg_no]
        control.append([f'{leg_no}区後', f'{lead}/{known}', f'{(100*lead/known):.0f}%' if known else '—',
                        f'{mean(positions):.2f}' if positions else '—',
                        f'{sum(1 for x in positions if x <= 3)}/{len(positions)}' if positions else '—'])
    movement = []
    for leg_no in range(2, legs + 1):
        vals = move_rows[leg_no]
        movement.append([f'{leg_no}区', str(len(vals)), f'{mean(vals):+.2f}' if vals else '—',
                         f'{mean(abs(x) for x in vals):.2f}' if vals else '—',
                         str(sum(1 for x in vals if x >= 2)), str(sum(1 for x in vals if x <= -2))])
    return {'races': races, 'demand': demand, 'control': control, 'movement': movement}


def team_depth_markdown_rows(path, heading):
    """Same parser as the existing PB tables; used for 3000m depth cross-checks."""
    return rank_markdown_rows(path, heading)


def teams_with_times(entry):
    return [team for team in sorted(entry['teams'], key=lambda x: x.get('rank', 999)) if secs(team.get('total')) is not None]


def year_total_pace_values(entry, gender):
    km = sum(distance(entry['year'], gender))
    teams = teams_with_times(entry)
    return [f"{t['rank']}位\n{t['team']}" for t in teams], [secs(t['total']) / km for t in teams]


def year_podium_leg_paces(entry, gender):
    distances = distance(entry['year'], gender)
    teams = teams_with_times(entry)[:3]
    labels = [f'{n}区' for n in range(1, len(distances) + 1)]
    values, names = [], []
    for team in teams:
        vals=[]
        for idx, leg in enumerate(team['legs']):
            sec=secs(leg.get('split'))
            vals.append(sec / distances[idx] if sec is not None else 0)
        values.append(vals); names.append(f"{team['rank']}位 {team['team']}")
    return labels, values, names


def annual_rank_pace_series(dataset, gender, ranks=(1, 2, 3, 6)):
    out = {rank: [] for rank in ranks}
    for year_s, entry in sorted(dataset['years'].items()):
        year = int(year_s)
        km = sum(distance(year, gender))
        for team in teams_with_times(entry):
            if team['rank'] in out:
                out[team['rank']].append((year, secs(team['total']) / km))
    return [out[r] for r in ranks], [f'{r}位' for r in ranks]


def podium_count_values(counter, limit=10):
    pairs = counter.most_common(limit)
    return [k for k, _ in pairs], [v for _, v in pairs]


def weather_chart_values():
    with WEATHER.open(encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    grouped=defaultdict(list)
    for row in rows:
        if row.get('気温_C'):
            grouped[row['開催日']].append(row)
    labels=[]; mins=[]; maxs=[]; winds=[]
    for day, rs in sorted(grouped.items()):
        labels.append(day[:4])
        temps=[float(x['気温_C']) for x in rs if x.get('気温_C')]
        speed=[float(x['平均風速_m_s']) for x in rs if x.get('平均風速_m_s')]
        mins.append(min(temps)); maxs.append(max(temps)); winds.append(max(speed) if speed else 0)
    return labels, mins, maxs, winds


def leg_distribution_values(dataset, gender, leg_no):
    vals=[]
    for year_s, entry in dataset['years'].items():
        km=distance(year_s, gender)[leg_no-1]
        for team in teams_with_times(entry):
            leg=next((x for x in team['legs'] if x.get('leg') == leg_no), None)
            sec=secs(leg.get('split')) if leg else None
            if sec is not None:
                vals.append(sec/km)
    return ['10%','25%','中央値','75%','90%'], [percentile(vals,p) for p in (.10,.25,.50,.75,.90)], len(vals)


def annual_gap_series(dataset, gender, rank_a, rank_b):
    vals=[]
    for year_s, entry in sorted(dataset['years'].items()):
        km=sum(distance(year_s, gender))
        byrank={x['rank']:x for x in teams_with_times(entry)}
        if rank_a in byrank and rank_b in byrank:
            vals.append((int(year_s), (secs(byrank[rank_b]['total'])-secs(byrank[rank_a]['total']))/km))
    return vals


def mark_seconds(cell):
    text=str(cell).strip()
    matched=re.fullmatch(r'(\d+):(\d{2})(?:\.(\d+))?', text)
    if matched:
        return int(matched.group(1))*60+int(matched.group(2))+float(f"0.{matched.group(3) or '0'}")
    v=secs(cell)
    return v if v is not None else 0


def ranking_chart_values(rows):
    return [r[1] for r in rows], [mark_seconds(r[3]) for r in rows]


def decimal_fmt(seconds):
    """Format a fractional track PB without silently dropping its hundredths."""
    if seconds is None:
        return '—'
    minutes, remainder = divmod(float(seconds), 60)
    return f'{int(minutes)}:{remainder:05.2f}'


def continuing_candidates():
    """Conservatively join recent result-board runners to 2026 adopted SB rows.

    A row qualifies only when its exact name, sex, and grade progressed to 2026
    all agree. This is an evidence list for pre-selection checks, not an entry
    list or a probabilistic forecast.
    """
    sb_rows = json.loads(SB_2026.read_text(encoding='utf-8'))
    by_key = defaultdict(list)
    snapshot_dates = []
    for row in sb_rows:
        name = str(row.get('名前') or '')
        if row.get('SB採用') != '__YES__' or not name or '�' in name:
            continue
        grade = str(row.get('学年') or '')
        gender = str(row.get('性別') or '')
        if grade not in {'1', '2', '3'} or gender not in {'男子', '女子'}:
            continue
        by_key[(name, gender, grade)].append(row)
        if row.get('日付'):
            snapshot_dates.append(row['日付'])

    result = {'男子': [], '女子': []}
    eligible_2025 = {'男子': 0, '女子': 0}
    for gender in ('男子', '女子'):
        grouped = {}
        for year in (2024, 2025):
            transcript = json.loads((TRANSCRIPTS / f'{year}-{gender}.json').read_text(encoding='utf-8'))
            for team in transcript['teams']:
                for leg in team['legs']:
                    name, grade = leg.get('name'), leg.get('grade')
                    if not name or name == 'unknown' or not isinstance(grade, int):
                        continue
                    target_grade = grade + (2026 - year)
                    if year == 2025 and target_grade in {2, 3}:
                        eligible_2025[gender] += 1
                    if target_grade not in {1, 2, 3}:
                        continue
                    rows = by_key.get((name, gender, str(target_grade)), [])
                    if not rows:
                        continue
                    key = (name, target_grade)
                    record = grouped.setdefault(key, {
                        'name': name, 'gender': gender, 'grade_2026': target_grade,
                        'history': [], 'pbs': {}, 'affiliations': set(),
                    })
                    record['history'].append({
                        'year': year, 'team': team['team'], 'leg': leg.get('leg'),
                        'split': leg.get('split'), 'grade': grade,
                    })
                    for row in rows:
                        dist = str(row.get('距離') or '')
                        try:
                            value = float(row.get('SB秒'))
                        except (TypeError, ValueError):
                            continue
                        if dist in {'800m', '1500m', '3000m'}:
                            record['pbs'][dist] = min(record['pbs'].get(dist, float('inf')), value)
                        if row.get('所属'):
                            record['affiliations'].add(row['所属'])
        for record in grouped.values():
            record['history'].sort(key=lambda item: item['year'], reverse=True)
            record['latest'] = record['history'][0]
            result[gender].append(record)
        result[gender].sort(key=lambda item: (item['latest']['team'], item['name']))
    return result, eligible_2025, max(snapshot_dates) if snapshot_dates else '—'


def candidate_team_counts(candidates):
    counts = Counter(item['latest']['team'] for item in candidates)
    pairs = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return [team for team, _ in pairs], [count for _, count in pairs]


def candidate_pb_rows(candidates, gender):
    primary = '1500m' if gender == '男子' else '800m'
    secondary = '3000m' if gender == '男子' else '1500m'
    rows = [['前回校', '氏名', '2026学年', '直近出走（学年）', primary + ' PB', secondary + ' PB', '照合']]
    for candidate in candidates:
        last = candidate['latest']
        older = candidate['history'][1:]
        history = f"{last['year']} {last['leg']}区 {last['split']}（{last['grade']}年）"
        if older:
            history += f" / {older[0]['year']}も出走"
        rows.append([
            last['team'], candidate['name'], f"{candidate['grade_2026']}年", history,
            decimal_fmt(candidate['pbs'].get(primary)), decimal_fmt(candidate['pbs'].get(secondary)),
            '氏名・性別・学年進行一致',
        ])
    return rows


def candidate_pb_chart_values(candidates, gender, limit=12):
    primary = '1500m' if gender == '男子' else '800m'
    eligible = [candidate for candidate in candidates if primary in candidate['pbs']]
    eligible.sort(key=lambda candidate: candidate['pbs'][primary])
    selected = eligible[:limit]
    labels = [f"{item['name']}\n{item['latest']['team']}" for item in selected]
    values = [item['pbs'][primary] for item in selected]
    return labels, values, primary


def one_character_variant(left, right):
    """Flag only a transparent, manual-review name similarity; never merge names."""
    return len(left) == len(right) and sum(a != b for a, b in zip(left, right)) == 1


def sb_unlisted_recent_runners():
    """Classify age-eligible 2024/25 runners by their SB snapshot presence.

    The full-width SB file has no year or grade, so it is used solely as an
    exact-name all-period presence check. It cannot prove club membership or
    that the athlete never raced elsewhere.
    """
    current_rows = json.loads(SB_2026.read_text(encoding='utf-8'))
    current = set()
    current_names = defaultdict(set)
    for row in current_rows:
        name, gender, grade = str(row.get('名前') or ''), str(row.get('性別') or ''), str(row.get('学年') or '')
        if row.get('SB採用') == '__YES__' and name and '�' not in name and gender in {'男子', '女子'} and grade in {'1', '2', '3'}:
            current.add((name, gender, grade))
            current_names[(gender, grade)].add(name)
    with (ROOT / 'input/external/sb/middle-school/wide/中学生SB.csv').open(encoding='utf-8-sig') as stream:
        wide_rows = list(csv.DictReader(stream))
    all_period = {(str(row.get('名前') or ''), str(row.get('性別') or '')) for row in wide_rows if row.get('名前') and '�' not in str(row.get('名前'))}

    classified = {'男子': [], '女子': []}
    for gender in ('男子', '女子'):
        grouped = {}
        for year in (2024, 2025):
            transcript = json.loads((TRANSCRIPTS / f'{year}-{gender}.json').read_text(encoding='utf-8'))
            for team in transcript['teams']:
                for leg in team['legs']:
                    name, grade = leg.get('name'), leg.get('grade')
                    target_grade = grade + (2026 - year) if isinstance(grade, int) else 99
                    if not name or name == 'unknown' or target_grade not in {1, 2, 3}:
                        continue
                    entry = grouped.setdefault((name, target_grade), {
                        'name': name, 'gender': gender, 'grade_2026': target_grade, 'history': [],
                    })
                    entry['history'].append({'year': year, 'team': team['team'], 'leg': leg.get('leg'), 'split': leg.get('split'), 'grade': grade})
        for entry in grouped.values():
            entry['history'].sort(key=lambda item: item['year'], reverse=True)
            entry['latest'] = entry['history'][0]
            key = (entry['name'], gender, str(entry['grade_2026']))
            if key in current:
                entry['status'] = '2026 SB一致'
            elif (entry['name'], gender) in all_period:
                entry['status'] = '2026 SBなし・全期間SBあり'
            else:
                entry['status'] = '全期間SBに完全一致なし'
            variants = sorted(
                candidate for candidate in current_names[(gender, str(entry['grade_2026']))]
                if one_character_variant(entry['name'], candidate)
            )
            entry['similar_name'] = variants[0] if variants else None
            classified[gender].append(entry)
        classified[gender].sort(key=lambda item: (item['latest']['team'], item['name']))
    return classified


def sb_status_chart_values(classified):
    statuses = ['2026 SB一致', '2026 SBなし\n全期間SBあり', '全期間SBに\n完全一致なし']
    keys = ['2026 SB一致', '2026 SBなし・全期間SBあり', '全期間SBに完全一致なし']
    return statuses, [[sum(item['status'] == key for item in classified[gender]) for key in keys] for gender in ('男子', '女子')]


def sb_unlisted_table_rows(entries):
    rows = [['直近年', '前回校', '氏名', '2026学年', '直近出走（学年）', 'SB照合', '表記類似（要原票）']]
    for entry in entries:
        last = entry['latest']
        history = f"{last['leg']}区 {last['split']}（{last['grade']}年）"
        if len(entry['history']) > 1:
            history += f" / {entry['history'][1]['year']}も出走"
        rows.append([
            str(last['year']), last['team'], entry['name'], f"{entry['grade_2026']}年", history,
            entry['status'], entry['similar_name'] or '—',
        ])
    return rows


def rank_stability(dataset, gender):
    """How much an observed relay checkpoint resembles the final placing."""
    leg_count = 6 if gender == '男子' else 5
    labels, exact, within_one, mean_abs, sample = [], [], [], [], []
    for leg_no in range(1, leg_count + 1):
        pairs = []
        for entry in dataset['years'].values():
            for team in entry['teams']:
                leg = next((item for item in team['legs'] if item.get('leg') == leg_no), None)
                if leg and isinstance(leg.get('passing_rank'), int) and isinstance(team.get('rank'), int):
                    pairs.append((leg['passing_rank'], team['rank']))
        labels.append(f'{leg_no}区後')
        sample.append(len(pairs))
        exact.append(100 * sum(checkpoint == final for checkpoint, final in pairs) / len(pairs) if pairs else 0)
        within_one.append(100 * sum(abs(checkpoint - final) <= 1 for checkpoint, final in pairs) / len(pairs) if pairs else 0)
        mean_abs.append(mean(abs(checkpoint - final) for checkpoint, final in pairs) if pairs else 0)
    return labels, exact, within_one, mean_abs, sample


def podium_turnover(dataset, gender):
    """Count podium entries/exits relative to each exchange checkpoint."""
    leg_count = 6 if gender == '男子' else 5
    labels, late_entries, late_exits, sample = [], [], [], []
    for leg_no in range(1, leg_count):
        pairs = []
        for entry in dataset['years'].values():
            for team in entry['teams']:
                leg = next((item for item in team['legs'] if item.get('leg') == leg_no), None)
                if leg and isinstance(leg.get('passing_rank'), int) and isinstance(team.get('rank'), int):
                    pairs.append((leg['passing_rank'], team['rank']))
        labels.append(f'{leg_no}区後')
        late_entries.append(sum(checkpoint > 3 and final <= 3 for checkpoint, final in pairs))
        late_exits.append(sum(checkpoint <= 3 and final > 3 for checkpoint, final in pairs))
        sample.append(len(pairs))
    return labels, late_entries, late_exits, sample


def extreme_rank_changes(dataset, gender, limit=5):
    """Largest finish-versus-first-exchange shifts, retaining actual evidence."""
    rows = []
    for year_s, entry in dataset['years'].items():
        for team in entry['teams']:
            first = next((item for item in team['legs'] if item.get('leg') == 1), None)
            if not first or not isinstance(first.get('passing_rank'), int) or not isinstance(team.get('rank'), int):
                continue
            trajectory = []
            for leg_no in range(1, (6 if gender == '男子' else 5) + 1):
                leg = next((item for item in team['legs'] if item.get('leg') == leg_no), None)
                if leg and isinstance(leg.get('passing_rank'), int):
                    trajectory.append(str(leg['passing_rank']))
            change = first['passing_rank'] - team['rank']
            rows.append({
                'year': int(year_s), 'team': team['team'], 'first': first['passing_rank'],
                'final': team['rank'], 'change': change, 'total': team.get('total') or '—',
                'trajectory': '→'.join(trajectory),
            })
    gains = sorted((row for row in rows if row['change'] > 0), key=lambda row: (-row['change'], row['year'], row['team']))[:limit]
    losses = sorted((row for row in rows if row['change'] < 0), key=lambda row: (row['change'], row['year'], row['team']))[:limit]
    return gains, losses


def gap_profile(dataset, gender):
    """Adjacent finishing-place gaps, distance-normalised to seconds/km."""
    values = {rank: [] for rank in range(1, 6)}
    for year_s, entry in dataset['years'].items():
        by_rank = {team['rank']: team for team in teams_with_times(entry)}
        km = sum(distance(year_s, gender))
        for rank in values:
            if rank in by_rank and rank + 1 in by_rank:
                values[rank].append((secs(by_rank[rank + 1]['total']) - secs(by_rank[rank]['total'])) / km)
    rows = []
    for rank, gaps in values.items():
        rows.append([f'{rank}-{rank + 1}位', str(len(gaps)), f'{percentile(gaps, .25):.1f}', f'{median(gaps):.1f}', f'{percentile(gaps, .75):.1f}', f'{sum(gap <= 5 for gap in gaps)}/{len(gaps)}'])
    return rows, [median(values[rank]) for rank in values]


def rank_change_table_rows(records, direction):
    rows = [['年', '学校', '1区後', '最終', '変動', '通過順位の軌跡', '総合']]
    for record in records:
        signed = f"+{record['change']}" if record['change'] > 0 else str(record['change'])
        label = f'{signed}位（改善）' if direction == 'gain' else f'{signed}位（後退）'
        rows.append([str(record['year']), record['team'], f"{record['first']}位", f"{record['final']}位", label, record['trajectory'], record['total']])
    return rows


def second_place_pace_profile(dataset, gender):
    """Historical pace distribution for the second-placed team, not a target guarantee."""
    points, paces = [], []
    for year_s, entry in sorted(dataset['years'].items()):
        second = next((team for team in teams_with_times(entry) if team['rank'] == 2), None)
        if second:
            sec_per_km = secs(second['total']) / sum(distance(year_s, gender))
            points.append((int(year_s), sec_per_km))
            paces.append(sec_per_km)
    current_km = 17.710 if gender == '男子' else 11.855
    bands = []
    for label, quantile in [('速い側25%', .25), ('中央値', .50), ('遅い側75%', .75)]:
        value = percentile(paces, quantile)
        bands.append([label, f'{value:.1f}秒/km', fmt(value * current_km)])
    return points, paces, bands


def second_checkpoint_profile(dataset, gender):
    """Where eventual second-place teams stood at every valid exchange."""
    leg_count = 6 if gender == '男子' else 5
    labels, top_two, top_three, average_rank, sample = [], [], [], [], []
    for leg_no in range(1, leg_count + 1):
        values = []
        for entry in dataset['years'].values():
            second = next((team for team in entry['teams'] if team.get('rank') == 2), None)
            leg = next((item for item in second['legs'] if item.get('leg') == leg_no), None) if second else None
            if leg and isinstance(leg.get('passing_rank'), int):
                values.append(leg['passing_rank'])
        labels.append(f'{leg_no}区後')
        sample.append(len(values))
        top_two.append(100 * sum(rank <= 2 for rank in values) / len(values) if values else 0)
        top_three.append(100 * sum(rank <= 3 for rank in values) / len(values) if values else 0)
        average_rank.append(mean(values) if values else 0)
    return labels, top_two, top_three, average_rank, sample


def second_leg_profile(dataset, gender):
    """Split-rank distribution of historical second-place teams by leg."""
    leg_count = 6 if gender == '男子' else 5
    labels, top_three, top_five, med_rank, sample = [], [], [], [], []
    for leg_no in range(1, leg_count + 1):
        values = []
        for entry in dataset['years'].values():
            second = next((team for team in entry['teams'] if team.get('rank') == 2), None)
            leg = next((item for item in second['legs'] if item.get('leg') == leg_no), None) if second else None
            if leg and isinstance(leg.get('split_rank'), int):
                values.append(leg['split_rank'])
        labels.append(f'{leg_no}区')
        sample.append(len(values))
        top_three.append(100 * sum(rank <= 3 for rank in values) / len(values) if values else 0)
        top_five.append(100 * sum(rank <= 5 for rank in values) / len(values) if values else 0)
        med_rank.append(median(values) if values else 0)
    return labels, top_three, top_five, med_rank, sample


def second_boundary_margins(dataset, gender):
    """Distance-normalised margins around second place by year."""
    first_gap, third_gap = [], []
    for year_s, entry in sorted(dataset['years'].items()):
        by_rank = {team['rank']: team for team in teams_with_times(entry)}
        if all(rank in by_rank for rank in (1, 2, 3)):
            km = sum(distance(year_s, gender))
            first_gap.append((int(year_s), (secs(by_rank[2]['total']) - secs(by_rank[1]['total'])) / km))
            third_gap.append((int(year_s), (secs(by_rank[3]['total']) - secs(by_rank[2]['total'])) / km))
    return first_gap, third_gap


def margin_summary_rows(first_gap, third_gap):
    rows = [['差の方向', '標本', '25%点', '中央値', '75%点', '≤5秒/km']]
    for label, points in [('優勝との差', first_gap), ('3位との差', third_gap)]:
        values = [value for _, value in points]
        rows.append([label, str(len(values)), f'{percentile(values, .25):.1f}', f'{median(values):.1f}', f'{percentile(values, .75):.1f}', f'{sum(value <= 5 for value in values)}/{len(values)}'])
    return rows


def provenance_diagram():
    """A compact vector map of what flows into decisions, without implying causality."""
    width, height = 176*mm, 105*mm
    d=Drawing(width,height)
    d.add(String(0,height-10,'根拠から当日判断までのデータ流れ',fontName=FONT_NAME,fontSize=10,fillColor=NAVY))
    boxes=[
        (5*mm,72*mm,48*mm,19*mm,'正本結果\n全年度・全区間'),
        (5*mm,40*mm,48*mm,19*mm,'2026走力\nPB・3000m層'),
        (5*mm,8*mm,48*mm,19*mm,'気象・日程\n当日運用条件'),
        (64*mm,72*mm,48*mm,19*mm,'検証・距離補正\n欠損を明示'),
        (64*mm,40*mm,48*mm,19*mm,'図表・シナリオ\n事実と予測を分離'),
        (123*mm,54*mm,48*mm,19*mm,'選考・配置\nA/B/Cの判断'),
        (123*mm,18*mm,48*mm,19*mm,'レース後記録\n次年度に再利用'),
    ]
    for x,y,w,h,text in boxes:
        d.add(Rect(x,y,w,h,fillColor=SKY if x<60*mm else colors.HexColor('#F4EEDC') if x<120*mm else colors.HexColor('#E8F3EC'),strokeColor=BLUE,strokeWidth=.6,rx=3,ry=3))
        for idx,line in enumerate(text.split('\n')):
            d.add(String(x+w/2,y+h-6*mm-3.6*mm*idx,line,fontName=FONT_NAME,fontSize=7.2,fillColor=NAVY,textAnchor='middle'))
    for x1,y1,x2,y2 in [(53*mm,81.5*mm,64*mm,81.5*mm),(53*mm,49.5*mm,64*mm,49.5*mm),(53*mm,17.5*mm,64*mm,49.5*mm),(112*mm,81.5*mm,123*mm,63.5*mm),(112*mm,49.5*mm,123*mm,63.5*mm),(147*mm,54*mm,147*mm,37*mm)]:
        d.add(Line(x1,y1,x2,y2,strokeColor=GREY,strokeWidth=1))
    d.add(String(0,0,'注: この図は根拠の流れを示し、PBや過去結果から順位を自動決定するものではありません。',fontName=FONT_NAME,fontSize=6.5,fillColor=GREY))
    return d


def story():
    men, women = load()
    man_sum, man_podium = summary(men, '男子')
    wom_sum, wom_podium = summary(women, '女子')
    men_issues=validate_dataset(men,'男子'); women_issues=validate_dataset(women,'女子')
    men_dyn, women_dyn = dynamics(men, '男子'), dynamics(women, '女子')
    candidates, eligible_2025, sb_snapshot = continuing_candidates()
    sb_status = sb_unlisted_recent_runners()
    men_stability = rank_stability(men, '男子')
    women_stability = rank_stability(women, '女子')
    men_turnover = podium_turnover(men, '男子')
    women_turnover = podium_turnover(women, '女子')
    men_gains, men_losses = extreme_rank_changes(men, '男子')
    women_gains, women_losses = extreme_rank_changes(women, '女子')
    men_gap_rows, men_gap_values = gap_profile(men, '男子')
    women_gap_rows, women_gap_values = gap_profile(women, '女子')
    men_second_pace, _, men_second_bands = second_place_pace_profile(men, '男子')
    women_second_pace, _, women_second_bands = second_place_pace_profile(women, '女子')
    men_second_checkpoint = second_checkpoint_profile(men, '男子')
    women_second_checkpoint = second_checkpoint_profile(women, '女子')
    men_second_leg = second_leg_profile(men, '男子')
    women_second_leg = second_leg_profile(women, '女子')
    men_second_margins = second_boundary_margins(men, '男子')
    women_second_margins = second_boundary_margins(women, '女子')
    st=[]
    # Cover
    st += [Spacer(1, 28*mm), rich('ARAGYOKU EKIDEN 2026', 'cover'), rich('荒玉駅伝2026 徹底対策', 'cover'),
        Spacer(1, 8*mm), rich('歴代結果 × 2026走力 × 区間設計 × 練習 × 当日運用', 'coverSub'), Spacer(1, 18*mm),
        rich('対象: 中学校駅伝チーム / 指導者 / 選手<br/>作成日: 2026年9月14日<br/>データ基準日: 2026年8月29日（2026走力データ）', 'coverSub'),
        Spacer(1, 15*mm), callout('この資料の使い方', '予測順位を断定する資料ではありません。最新のチーム編成、当日気象、体調、コース状況で結果は変わります。歴代の到達ラインと現在の走力を分け、意思決定に使えるチェックリストへ落とし込んでいます。', colors.HexColor('#F4EEDC')), PageBreak()]
    # TOC
    st += [heading('目次'), P('見出しをクリックすると、PDFビューアのしおりから該当章へ移動できます。ページ番号は生成時に自動確定します。', 'body')]
    toc=TableOfContents()
    toc.levelStyles=[ParagraphStyle('TOC0', fontName=FONT_NAME,fontSize=9,leading=15,leftIndent=0,firstLineIndent=0,textColor=NAVY),
                     ParagraphStyle('TOC1', fontName=FONT_NAME,fontSize=8,leading=12,leftIndent=8*mm,firstLineIndent=0,textColor=GREY)]
    st += [toc, PageBreak()]

    # Summary
    st += [heading('0. まず読むべき結論')]
    st += [callout('男子: 「上位4人」より「6人の底」を優先する', '2026年の1500m上位4人平均では玉陵中・菊水中が先行しています。一方、現行男子コースは6区間です。歴代上位の再現には、速い4人だけでなく、5・6番手が失速しない編成と補員の準備が不可欠です。'),
           callout('女子: 5人目が順位を左右する', '2026年の女子800m上位3人平均は長洲中、上位5人平均は岱明中が首位です。女子は5区間であり、上位3人の速さと5人目までの均質性を別々に確認する必要があります。', colors.HexColor('#E8F3EC')),
           callout('順位目標は「総合タイム」ではなく「平均ペース」で管理する', '男子は2024年に総距離が19.710kmから17.710kmへ変わりました。年度横断の比較は総合タイムの大小ではなく、距離補正したペースで行います。女子は全年度11.855kmです。', colors.HexColor('#F5F2E9')),
           P('本書の重要な制約: 2019年・2022年・2025年など一部の男子氏名欄には、原画像の解像度・取得権限に由来する未確定セルがあります。結果、順位、総合タイム、区間タイムに基づく分析は別途検算済みですが、個人名を用いる判断は「要原票確認」として扱います。', 'small'), PageBreak()]

    # integrity
    st += [heading('1. データ品質・検証範囲'), heading('1.1 何を正本としたか',2),
           P('歴代の正本は input/aragyoku/transcripts/ の年度別文字起こしJSONです。女子は2012-2025年（2014年は原画像未確認）、男子は2012-2025年（2019年は判読不能セルをunknownとして保持）を収録しています。'),
           table([['対象','検証内容','扱い'],['総合・区間タイム','区間和 = 総合、順位順、通過順位・区間順位の整合','分析に採用'],['氏名・学年','原結果表との照合、女子上位校はCSV突合も実施','未確定セルを注記'],['年度間比較','男子は2024年の距離変更を補正','ペースで比較'],['2026走力','2024-2026 PBと2026年記録を学校単位に集計','大会結果の予測ではなく現状把握']], [30*mm,80*mm,66*mm]),
           heading('1.2 生成前検査の結果',2),
           table([['データ','区間和・区間数の自動検査','結果'],['男子全年度', f'{len(men["years"])}年度 / {sum(len(v["teams"]) for v in men["years"].values())}チーム', '合格' if not men_issues else '要確認 '+str(len(men_issues))],['女子全年度',f'{len(women["years"])}年度 / {sum(len(v["teams"]) for v in women["years"].values())}チーム','合格' if not women_issues else '要確認 '+str(len(women_issues))]], [38*mm,88*mm,50*mm]),
           heading('1.3 使ってはいけない比較と時間方向の注意',2),
           table([['資料','使えること','使えないこと / 注意'],['女子上位6校の同年度トラック突合','390人中230人の同年度トラック記録付き実績を、個人の過去事例として参照','同年度内でも駅伝後の記録を含み得る。レース前予測・因果の証拠には使わない'],['1500m SB帯別実績','男子4:30/4:45/5:00、女子4:45/5:00/5:15/5:30の各±3秒、計198件の実走例を参照','SBから駅伝タイムを一意に換算しない。距離、路面、気象、タスキ、配置が異なる'],['2026学校別PB','候補層の厚みと不足データを確認','出場確定、故障、当日状態、直前伸長を含まないため順位予想にしない']], [36*mm,66*mm,74*mm]),
           source_note(['input/aragyoku/validate_transcript.py','input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json','docs/adr/013-aragyoku-csv-name-reconciliation.md']), PageBreak()]

    # Event profile
    st += [heading('2. 大会プロファイルとコース設計'), heading('2.1 区間距離',2),
           table([['部門・年度','1区','2区','3区','4区','5区','6区','合計'],['男子 2023年以前','3.95','3.05','2.855','2.855','3.00','4.00','19.710km'],['男子 2024年以降','3.00','2.855','3.00','3.00','2.855','3.00','17.710km'],['女子 全年度','3.00','1.855','2.00','2.00','3.00','-','11.855km']], [34*mm,21*mm,21*mm,21*mm,21*mm,21*mm,21*mm,27*mm]),
           P('男子は2024年から距離構成が変わっています。2012-2023の「長い1区・6区」での序盤耐性を、2024-2025の「3km中心の反復高速区間」にそのまま当てはめないことが必要です。'),
           heading('2.2 区間の役割と配置基準',2),
           table([['区間','男子 2024-','女子','第一配置基準','避ける配置'],['1区','3.0km','3.0km','混戦・位置取りに強く、最初の1kmを抑えられる選手','PBだけで選ぶ／序盤オーバーペース'],['2区','2.855km','1.855km','テンポ変化に強い・単独走の集中力','ロング型を無検証で短区間へ'],['3区','3.0km','2.0km','流れを作る安定選手','失速耐性未確認の選手'],['4区','3.0km','2.0km','勝負所で追走・攻めを判断できる選手','前半型のみの選手'],['5区','2.855km','3.0km','疲労下でフォーム維持、女子は特に総合力','5人目を軽視'],['6区','3.0km','-','順位を守る／詰める実戦判断','アンカー適性をスピードだけで判断']], [18*mm,18*mm,18*mm,67*mm,55*mm]),
           source_note(['docs/aragyoku-ekiden-distance-definitions.md']), PageBreak()]

    # Historical
    st += [heading('3. 歴代到達ライン'), heading('3.1 順位別の目安（距離補正済み）',2),
           P('下表は各順位の歴代上位6校を、総時間 ÷ 総距離で加重平均したものです。「必要条件」ではなく、競争水準を把握するための基準です。参考総合時間は2024年以降男子17.710km、女子11.855kmに換算しています。')]
    st += [P('男子', 'H2'), table(historical_target_rows(men,'男子'),[29*mm,32*mm,50*mm,65*mm]),Spacer(1,4*mm),P('女子','H2'),table(historical_target_rows(women,'女子'),[29*mm,32*mm,50*mm,65*mm]),
           heading('3.2 歴代優勝校と優勝ペース',2),
           table([['年','男子優勝','記録','ペース','女子優勝','記録','ペース']]+[[m['year'],m['winner'],m['time'],m['winner_pace'], next((w['winner'] for w in wom_sum if w['year']==m['year']),'—'), next((w['time'] for w in wom_sum if w['year']==m['year']),'—'), next((w['winner_pace'] for w in wom_sum if w['year']==m['year']),'—')] for m in man_sum], [14*mm,32*mm,22*mm,26*mm,32*mm,22*mm,26*mm]),
           P('2014年女子は原画像未確認のため、女子の歴代表から除外しています。2019年男子は氏名の一部をunknownとして保持していますが、総合タイムが確定しているチームはペース集計に含めています。','small'), source_note(['out/analysis/aragyoku_top6_historical_average_pace.md','input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json']), PageBreak()]

    # Observed, result-board-based race dynamics. These are descriptive, not forecasts.
    st += [heading('3.3 区間別の実測ペース分布（全参加校）',2),
           P('各年度の全参加校・全有効区間を距離補正して、区間の負荷とばらつきを示します。25%点は速い側、75%点は遅い側です。路面・風・気温・チーム数は年ごとに異なるため、個人の目標タイムや医学的負荷の処方には使いません。'),
           P(f'男子（{men_dyn["races"]}年度、2024年のコース変更を距離補正）','H2'),
           table([['区間','標本数','速い側25%','中央値','遅い側75%','最速','同年内の最速-最遅の中央値','区間新数'], *men_dyn['demand']], [15*mm,17*mm,25*mm,25*mm,25*mm,25*mm,31*mm,18*mm]),
           P(f'女子（{women_dyn["races"]}年度、距離構成一定）','H2'),
           table([['区間','標本数','速い側25%','中央値','遅い側75%','最速','同年内の最速-最遅の中央値','区間新数'], *women_dyn['demand']], [15*mm,17*mm,25*mm,25*mm,25*mm,25*mm,31*mm,18*mm]),
           callout('読み方', '短区間は速いペースになりやすい一方、中央値と速い側25%点の差が小さいからといって、誰でも置ける区間ではありません。速さ・スタート対応・単独走・受け渡し後の判断は別評価です。', colors.HexColor('#F5F2E9')),
           source_note(['input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json','docs/aragyoku-ekiden-distance-definitions.md']), PageBreak()]

    st += [heading('3.4 中継時点の位置取りと順位変動',2),
           P('各年の優勝校が中継時点でどの位置にいたかを集計しました。因果ではなく、優勝校の実際の位置の記述統計です。通過順位欠損は分母から除外しています。'),
           P('男子: 優勝校の中継時点','H2'),
           table([['時点','優勝校が首位','首位率','優勝校の平均通過順位','3位以内'], *men_dyn['control']], [28*mm,35*mm,28*mm,48*mm,32*mm]),
           P('女子: 優勝校の中継時点','H2'),
           table([['時点','優勝校が首位','首位率','優勝校の平均通過順位','3位以内'], *women_dyn['control']], [28*mm,35*mm,28*mm,48*mm,32*mm]),
           P('序盤首位の率が100%でなければ、序盤に首位でないこと自体は敗因ではありません。現場では順位だけでなく先頭との差、単独か集団か、選手のフォームを同時に確認します。','body'),
           heading('3.5 1区間で順位はどれだけ動くか',2),
           table([['男子の区間','比較数','平均順位改善','平均絶対変動','2位以上改善','2位以上後退'], *men_dyn['movement']], [27*mm,25*mm,31*mm,31*mm,31*mm,31*mm]), Spacer(1,3*mm),
           table([['女子の区間','比較数','平均順位改善','平均絶対変動','2位以上改善','2位以上後退'], *women_dyn['movement']], [27*mm,25*mm,31*mm,31*mm,31*mm,31*mm]),
           P('平均との差が0に近くても、個々のチームには大きな上下があります。「追える区間」を事前に決め打ちせず、走者の単独走耐性と前走者から受け取る順位・差を使って作戦を切り替えます。','small'),
           source_note(['input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json']), PageBreak()]

    # Current rankings
    men4=rank_markdown_rows(MEN_RANK,'## 上位4人平均')
    men6=rank_markdown_rows(MEN_RANK,'## 上位6人平均')
    men3000_4=team_depth_markdown_rows(MEN_RANK,'## 3000m・上位4人平均')
    men3000_6=team_depth_markdown_rows(MEN_RANK,'## 3000m・上位6人平均')
    women3=rank_markdown_rows(WOMEN_RANK,'## 800m・上位3人平均')
    women5=rank_markdown_rows(WOMEN_RANK,'## 800m・上位5人平均')
    st += [heading('4. 2026年の勢力図（PBベース）'),
           P('以下は2026年8月29日までに取得済みの記録を用いた走力スナップショットです。駅伝出場確定者、当日のコンディション、練習進捗、故障・欠場は反映していないため、予想順位ではありません。'),
           heading('4.1 男子: 上位4人と上位6人を分けて見る',2),
           table([['順位','学校','対象人数','1500m 上位4人平均']]+[r[:4] for r in men4], [16*mm,40*mm,24*mm,45*mm]), Spacer(1,3*mm),
           table([['順位','学校','対象人数','1500m 上位6人平均']]+[r[:4] for r in men6], [16*mm,40*mm,24*mm,45*mm]),
           callout('男子の判断', '上位4人平均だけを見ると玉陵中・菊水中・玉名附中が先行します。6人平均では玉陵中・菊水中・南関中が上位です。駅伝では「誰が走るか」より先に、6人目までの安全な戦力を確定し、補員を含む9-10人の練習設計を組みます。', colors.HexColor('#EAF3FA')),
           heading('4.2 女子: 上位3人の速さと上位5人の均質性',2),
           table([['順位','学校','対象人数','800m 上位3人平均']]+[r[:4] for r in women3], [16*mm,40*mm,24*mm,45*mm]), Spacer(1,3*mm),
           table([['順位','学校','対象人数','800m 上位5人平均']]+[r[:4] for r in women5], [16*mm,40*mm,24*mm,45*mm]),
           callout('女子の判断', '上位3人平均は長洲中、上位5人平均は岱明中が首位です。主力3人の出力と5人目までの揃い方は別の能力です。選考では「5人の合計期待値」と「1人欠けた時の代替可能性」を同時に確認します。', colors.HexColor('#E8F3EC')),
           source_note(['out/analysis/2026_men_1500m_pb_school_ranking.md','out/analysis/2026_women_800m_1500m_pb_school_ranking.md','input/external/drive/shared/分析/2026年度荒玉男子.pdf','input/external/drive/shared/分析/2026年荒玉女子.pdf']), PageBreak()]

    st += [heading('4.3 男子は3000mでも層を再確認する',2),
           P('男子の現行コースは2.855-3.0kmが中心であり、1500mだけでは持続走力を十分に表せません。3000m記録が4人または6人そろう学校だけを別軸で確認します。記録時期・レース条件・出場可否は統一されていないため、1500m順位を置き換えるものではありません。'),
           table([['順位','学校','対象人数','3000m 上位4人平均']]+[r[:4] for r in men3000_4], [16*mm,40*mm,24*mm,45*mm]), Spacer(1,3*mm),
           table([['順位','学校','対象人数','3000m 上位6人平均']]+[r[:4] for r in men3000_6], [16*mm,40*mm,24*mm,45*mm]),
           callout('二軸での選考', '1500mが速くても、3km巡航・後半維持・連戦回復は別に確認します。3000mデータが不足する選手は、区間相当TT、過去駅伝、練習内の後半低下、痛み・回復記録を用い、空欄を恣意的な推定で埋めません。', colors.HexColor('#F5F2E9')),
           heading('4.4 「近いSB帯の過去実績」を使うときの作法',2),
           P('既存のSB帯別突合には、男子1500m 4:30/4:45/5:00、女子1500m 4:45/5:00/5:15/5:30の各±3秒に当たる歴代198件が収録されています。これは数式での予想値ではなく、「同程度の1500m記録を持った選手が、実際にどの距離・区間・チーム順位で走ったか」を照会する索引です。'),
           table([['照会手順','行うこと','結論にしてはいけないこと'],['1','同じ性別・SB帯・距離構成に近い年度を抽出','SBが近いから同じ区間タイムになる'],['2','区間距離を明記し、1区/短区間/アンカーを混ぜない','平均値だけで個人の上限・下限を決める'],['3','区間順位とチーム順位、単独走・気象の注記を併読','速い選手を長区間へ、遅い選手を短区間へ自動配置する'],['4','現在のTT・回復・出場可否で最終判断','過去の他校実績を本人の予測として断定する']], [18*mm,79*mm,79*mm]),
           P('女子上位6校の同年度トラック突合（390人中230人にトラック記録）は、過去の駅伝結果を読み解く補助資料です。季節内の記録には駅伝後のものも含み得るため、前日までに使える予測データとは分けて扱います。','small'),
           source_note(['out/analysis/1500m_sb_band_ekiden.html','out/analysis/aragyoku_women_track_joined.json','out/analysis/2026_men_1500m_pb_school_ranking.md']), PageBreak()]

    # Recent runner-to-current-SB joins: candidate discovery, deliberately not an entry prediction.
    male_team_labels, male_team_values = candidate_team_counts(candidates['男子'])
    female_team_labels, female_team_values = candidate_team_counts(candidates['女子'])
    male_top_labels, male_top_values, male_primary = candidate_pb_chart_values(candidates['男子'], '男子')
    female_top_labels, female_top_values, female_primary = candidate_pb_chart_values(candidates['女子'], '女子')
    male_latest_2025 = sum(item['latest']['year'] == 2025 for item in candidates['男子'])
    female_latest_2025 = sum(item['latest']['year'] == 2025 for item in candidates['女子'])
    sb_status_labels, sb_status_series = sb_status_chart_values(sb_status)
    male_global_absent = [item for item in sb_status['男子'] if item['status'] == '全期間SBに完全一致なし']
    female_global_absent = [item for item in sb_status['女子'] if item['status'] == '全期間SBに完全一致なし']
    male_variant_count = sum(item['similar_name'] is not None for item in male_global_absent)
    female_variant_count = sum(item['similar_name'] is not None for item in female_global_absent)
    st += [heading('4.5 2024・2025出走者から見る2026継続候補'),
           P(f'2024・2025年の正本結果表を、2026年度SB採用データ（最新収録日 {sb_snapshot}）と照合しました。ここでの「継続候補」は、過去出走者の氏名・性別・学年を2026年へ進行させ、その3条件が2026 SB行と完全一致した選手だけです。これは候補確認の索引であり、エントリー・在籍・故障・当日出走を予測または確定するものではありません。'),
           table([['照合条件','採用','採用しない / 不明扱い'],['過去結果','2024年の1年生、2025年の1-2年生（2026年に1-3年生）','2026年に卒業済みとなる学年、unknown氏名'],['同一性','氏名・性別・学年進行が2026 SB採用行と完全一致','類似字・所属名だけでの推定照合'],['走力','2026 SBにある800m・1500m・3000mの公表記録','出走可否、直前状態、所属変更、登録を推測']], [33*mm,70*mm,73*mm]),
           callout('読み方', f"男子 {len(candidates['男子'])}人、女子 {len(candidates['女子'])}人が完全一致しました。うち直近の2025年出走に基づく者は男子 {male_latest_2025}人、女子 {female_latest_2025}人です。2025年に2026年の2-3年生となる出走者は男子 {eligible_2025['男子']}人、女子 {eligible_2025['女子']}人であり、SB未掲載は『走らない』を意味しません。", colors.HexColor('#F5F2E9')),
           vbar_chart('男子: 2026 SBまで追跡できる継続候補数（直近の出走校別）', male_team_labels, [male_team_values], ['候補数'], '縦軸: 人', height=67*mm),
           vbar_chart('女子: 2026 SBまで追跡できる継続候補数（直近の出走校別）', female_team_labels, [female_team_values], ['候補数'], '縦軸: 人', height=67*mm),
           source_note(['input/aragyoku/transcripts/2024-男子.json','input/aragyoku/transcripts/2025-男子.json','input/aragyoku/transcripts/2024-女子.json','input/aragyoku/transcripts/2025-女子.json','input/external/sb/middle-school/by-year/2026-sb-adopted.json','docs/adr/013-aragyoku-csv-name-reconciliation.md']), PageBreak()]

    st += [heading('4.6 男子: 継続候補の個別確認表',2),
           P('直近の出走校で並べています。PBは2026 SB採用値であり、駅伝換算値ではありません。2025年以外の出走歴がある場合は補足に残します。PB欄がない種目は能力不足ではなく、当該種目の採用SBが存在しないことを示します。'),
           table(candidate_pb_rows(candidates['男子'], '男子'), [24*mm,20*mm,15*mm,40*mm,22*mm,22*mm,33*mm], style='appendix'),
           callout('男子の分析上の使い方', '候補ごとに「2025年の区間実走」と「2026年の1500m/3000m」を別根拠として見ます。どちらか一方だけで区間を決めず、3km相当TT、後半低下、直近の健康状態、補員との差で最終確認します。', colors.HexColor('#EAF3FA')),
           source_note(['input/aragyoku/transcripts/2024-男子.json','input/aragyoku/transcripts/2025-男子.json','input/external/sb/middle-school/by-year/2026-sb-adopted.json']), PageBreak()]

    st += [heading('4.7 女子: 継続候補の個別確認表',2),
           P('女子も同じ完全一致規則で抽出しています。短い800mのPBは立ち上がりの確認材料になりますが、1区・5区などの3km区間へそのまま換算しません。前年の区間実走、1500m、TTと疲労耐性を併読します。'),
           table(candidate_pb_rows(candidates['女子'], '女子'), [24*mm,20*mm,15*mm,40*mm,22*mm,22*mm,33*mm], style='appendix'),
           callout('女子の分析上の使い方', '2025年に走った選手でも、2026年に同じ校・同じ区間で走るとは限りません。女子は5人編成なので、上位候補の速さだけでなく、5人目までの出場可否・健康・3km耐性を同時に確認します。', colors.HexColor('#E8F3EC')),
           source_note(['input/aragyoku/transcripts/2024-女子.json','input/aragyoku/transcripts/2025-女子.json','input/external/sb/middle-school/by-year/2026-sb-adopted.json']), PageBreak()]

    st += [heading('4.8 継続候補の2026 PB比較（確認用）',2),
           P('完全一致した継続候補のうち、比較種目のSBがある速い順12人を表示します。男子は1500m、女子は800mです。表示外の候補を除外・不適格と解釈しないでください。棒が低いほど記録が速いことを示します。'),
           vbar_chart('男子: 継続候補の2026 1500m PB 上位12人', male_top_labels, [male_top_values], ['1500m PB'], '縦軸: 秒（低いほど速い）', height=68*mm),
           vbar_chart('女子: 継続候補の2026 800m PB 上位12人', female_top_labels, [female_top_values], ['800m PB'], '縦軸: 秒（低いほど速い）', height=68*mm),
           chart_note('この図は選考順位・出走予測ではありません。2025実走、2026 SB、学年進行の三つを同じ選手で確認できる候補を、現場で再確認するための図です。'),
           source_note(['input/aragyoku/transcripts/2024-男子.json','input/aragyoku/transcripts/2025-男子.json','input/aragyoku/transcripts/2024-女子.json','input/aragyoku/transcripts/2025-女子.json','input/external/sb/middle-school/by-year/2026-sb-adopted.json']), PageBreak()]

    st += [heading('4.9 「2026 SB未掲載」と「荒玉以外の記録なし」を分ける'),
           P('2024年の1年生と2025年の1-2年生を、2026年の学年へ進行させて追跡しました。まず2026年度SB採用データとの完全一致を確認し、未一致者は中学生SBワイド表（全期間の現行スナップショット）にも同じ氏名・性別で載るかを別に確認しています。ワイド表には年度・学年がないため、全期間照合は同一人物の断定ではなく、同名記録の有無だけを示します。'),
           vbar_chart('年齢上2026年に在籍し得る2024・2025出走者のSB照合', sb_status_labels, sb_status_series, ['男子','女子'], '縦軸: 人', height=82*mm),
           table([['区分','男子','女子','意味'],['2026 SB一致',str(sum(item['status']=='2026 SB一致' for item in sb_status['男子'])),str(sum(item['status']=='2026 SB一致' for item in sb_status['女子'])),'2026年度SB採用行に氏名・性別・学年進行が一致'],['2026 SBなし・全期間SBあり',str(sum(item['status']=='2026 SBなし・全期間SBあり' for item in sb_status['男子'])),str(sum(item['status']=='2026 SBなし・全期間SBあり' for item in sb_status['女子'])),'今年のSB採用行はないが、ワイドSBには同名・同性別の記録あり'],['全期間SBに完全一致なし',str(len(male_global_absent)),str(len(female_global_absent)),'ワイドSBにも同名・同性別の完全一致がない。次ページ以降に一覧']], [42*mm,18*mm,18*mm,88*mm]),
           callout('重要な非断定', f'下の一覧は「荒玉駅伝しか出場していない」「陸上部ではない」を証明するものではありません。公開SBスナップショットに完全一致がない、という観測結果です。氏名の一字違いで2026 SBに似た表記がある者は男子 {male_variant_count}人、女子 {female_variant_count}人おり、別人・OCR差・改姓等を原票なしに決めません。', colors.HexColor('#F5F2E9')),
           source_note(['input/aragyoku/transcripts/2024-男子.json','input/aragyoku/transcripts/2025-男子.json','input/aragyoku/transcripts/2024-女子.json','input/aragyoku/transcripts/2025-女子.json','input/external/sb/middle-school/by-year/2026-sb-adopted.json','input/external/sb/middle-school/wide/中学生SB.csv','docs/adr/012-middle-school-sb-all-years.md']), PageBreak()]

    st += [heading('4.10 男子: 全期間SBに完全一致がない出走者（要確認リスト）',2),
           P('2024・2025の荒玉出走歴があり、学年進行上2026年に中学生であり得る男子のうち、2026 SB採用表・全期間SBワイド表のどちらにも同名・同性別の完全一致がなかった者です。表記類似欄は自動統合せず、原画像・所属・学年を確認するための注意喚起です。'),
           table(sb_unlisted_table_rows(male_global_absent), [15*mm,24*mm,25*mm,15*mm,38*mm,30*mm,29*mm], style='appendix'),
           callout('現場での使い方', 'この表は補員候補や駅伝適性を見落とさないための確認リストです。SBがないことを低い走力・非所属・出走なしと扱わず、練習参加、校内TT、健康状態、エントリー意思を個別に確認します。', colors.HexColor('#EAF3FA')),
           source_note(['input/aragyoku/transcripts/2024-男子.json','input/aragyoku/transcripts/2025-男子.json','input/external/sb/middle-school/by-year/2026-sb-adopted.json','input/external/sb/middle-school/wide/中学生SB.csv']), PageBreak()]

    st += [heading('4.11 女子: 全期間SBに完全一致がない出走者（要確認リスト）',2),
           P('女子も同じ規則です。過年度を含むワイドSBに同名・同性別の完全一致がないことだけを示します。所属の異動、表記揺れ、非公表大会、SB更新遅れはこの照合だけでは除外できません。'),
           table(sb_unlisted_table_rows(female_global_absent), [15*mm,24*mm,25*mm,15*mm,38*mm,30*mm,29*mm], style='appendix'),
           callout('選考での扱い', '駅伝での区間実走は、トラックSBがない選手にも残る実戦情報です。短区間と3km区間を区別し、当年のTT・後半低下・疲労・健康・補員の準備を併せて確認します。', colors.HexColor('#E8F3EC')),
           source_note(['input/aragyoku/transcripts/2024-女子.json','input/aragyoku/transcripts/2025-女子.json','input/external/sb/middle-school/by-year/2026-sb-adopted.json','input/external/sb/middle-school/wide/中学生SB.csv']), PageBreak()]

    st += [heading('4.12 中継順位は最終順位をどれだけ示すか'),
           P('各中継時点の通過順位と最終順位を、全収録年度・全参加校で突合しました。「最終順位と一致」はその時点の順位が最終結果と同じ割合、「±1位以内」は最終順位との差が1以内の割合です。最終区間後が100%になるのは定義上当然なので、それ以前の上がり方を見る図です。'),
           vbar_chart('男子: 中継順位と最終順位の一致度', men_stability[0], [men_stability[1], men_stability[2]], ['最終順位と一致','最終順位±1位'], '縦軸: 割合（%）', height=67*mm, value_min=0, value_max=100),
           vbar_chart('女子: 中継順位と最終順位の一致度', women_stability[0], [women_stability[1], women_stability[2]], ['最終順位と一致','最終順位±1位'], '縦軸: 割合（%）', height=67*mm, value_min=0, value_max=100),
           table([['部門','1区後の標本','最終前中継の平均絶対差','読み方'],['男子',str(men_stability[4][0]),f'{men_stability[3][-2]:.2f}位','最終前の順位でも変動が残る'],['女子',str(women_stability[4][0]),f'{women_stability[3][-2]:.2f}位','終盤まで順位を固定しない']], [25*mm,32*mm,46*mm,63*mm]),
           chart_note('順位の一致度は因果ではなく結果の記述です。首位を守る、または後方から追う作戦を固定する根拠にはせず、先頭差・単独走・選手のフォームを併読します。'),
           source_note(['input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json']), PageBreak()]

    st += [heading('4.13 表彰台はどこまで入れ替わるか'),
           P('各中継時点で3位以内にいなかったのに最終表彰台へ入ったチームを「後発の表彰台入り」、逆に中継時点で3位以内だったのに最終表彰台外となったチームを「表彰台外へ」として件数化しました。年数・参加数の違いを含む全期間の件数であり、区間単独の因果を示しません。'),
           vbar_chart('男子: 中継後に起きた表彰台の入れ替わり', men_turnover[0], [men_turnover[1], men_turnover[2]], ['後発の表彰台入り','表彰台外へ'], '縦軸: 件数', height=70*mm),
           vbar_chart('女子: 中継後に起きた表彰台の入れ替わり', women_turnover[0], [women_turnover[1], women_turnover[2]], ['後発の表彰台入り','表彰台外へ'], '縦軸: 件数', height=70*mm),
           callout('実戦への含意', '中継3位以内は有利な位置情報ですが、確定結果ではありません。タスキを受けた時点では順位だけでペースを上げず、先頭差・前後の集団・担当選手の後半耐性で「守る/追う」を判断します。', colors.HexColor('#F5F2E9')),
           source_note(['input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json']), PageBreak()]

    st += [heading('4.14 最大逆転・最大後退の実例'),
           P('1区後の通過順位と最終順位の差が大きいチームを、改善・後退それぞれ5例ずつ抽出しました。順位の軌跡は各区間後の通過順位です。未記録の通過順位は補完せず、保存値だけを並べています。'),
           P('男子: 1区後からの最大改善','H2'), table(rank_change_table_rows(men_gains, 'gain'), [14*mm,29*mm,18*mm,18*mm,26*mm,43*mm,28*mm]),
           P('男子: 1区後からの最大後退','H2'), table(rank_change_table_rows(men_losses, 'loss'), [14*mm,29*mm,18*mm,18*mm,26*mm,43*mm,28*mm]),
           P('女子: 1区後からの最大改善','H2'), table(rank_change_table_rows(women_gains, 'gain'), [14*mm,29*mm,18*mm,18*mm,26*mm,43*mm,28*mm]),
           P('女子: 1区後からの最大後退','H2'), table(rank_change_table_rows(women_losses, 'loss'), [14*mm,29*mm,18*mm,18*mm,26*mm,43*mm,28*mm]),
           chart_note('これはケーススタディ用の事実一覧です。逆転を再現するために序盤を遅らせたり、後退を特定区間の失敗と断定したりはできません。'),
           source_note(['input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json']), PageBreak()]

    st += [heading('4.15 どの順位帯が接戦になりやすいか'),
           P('隣り合う最終順位の総合タイム差を、各年度の総距離で割って秒/kmへ補正しました。箱ひげ図ではなく、25%点・中央値・75%点と「5秒/km以下」の年度数を表に示します。男子の2024年コース変更は距離補正済みです。'),
           vbar_chart('男子: 隣接順位の総合ペース差（中央値）', ['1-2位','2-3位','3-4位','4-5位','5-6位'], [men_gap_values], ['中央値'], '縦軸: 秒/km（小さいほど接戦）', height=61*mm),
           table([['順位帯','標本','25%点','中央値','75%点','≤5秒/km'], *men_gap_rows], [26*mm,22*mm,27*mm,27*mm,27*mm,34*mm]),
           vbar_chart('女子: 隣接順位の総合ペース差（中央値）', ['1-2位','2-3位','3-4位','4-5位','5-6位'], [women_gap_values], ['中央値'], '縦軸: 秒/km（小さいほど接戦）', height=61*mm),
           table([['順位帯','標本','25%点','中央値','75%点','≤5秒/km'], *women_gap_rows], [26*mm,22*mm,27*mm,27*mm,27*mm,34*mm]),
           chart_note('秒/kmの差は年度間比較のための補正です。実際のタスキ差は総秒差で確認し、同じペース差でもコース距離と中継状況で意味が変わります。'),
           source_note(['input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json','docs/aragyoku-ekiden-distance-definitions.md']), PageBreak()]

    st += [heading('4.16 県駅伝出場圏: 2位到達ラインの見方'),
           P('この章では、依頼時に示された「2位まで県駅伝に出場できる」という前提で、歴代2位チームの実測を分析します。出場枠は年度の大会要項で必ず再確認してください。2位のタイムは競技力・天候・人数・コース条件で変わるため、ここでは必達値ではなく距離補正済みの到達ラインとして扱います。'),
           vbar_chart('男子: 歴代2位の総合ペース（年度別）', [str(year) for year, _ in men_second_pace], [[value for _, value in men_second_pace]], ['2位ペース'], '縦軸: 秒/km（低いほど速い）', height=65*mm),
           vbar_chart('女子: 歴代2位の総合ペース（年度別）', [str(year) for year, _ in women_second_pace], [[value for _, value in women_second_pace]], ['2位ペース'], '縦軸: 秒/km（低いほど速い）', height=65*mm),
           table([['部門','帯','2位のペース','現行コース換算の参考総合'], *[['男子', *row] for row in men_second_bands], *[['女子', *row] for row in women_second_bands]], [20*mm,30*mm,45*mm,55*mm]),
           callout('2位を狙う条件', '最初に置くべきは「2位の歴史的なペース帯」と「3位との境界」です。PB合計だけで到達を決めず、次ページ以降の中継位置、区間順位、終盤の差を同じオーダー案で照合します。', colors.HexColor('#E8F3EC')),
           source_note(['input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json','docs/aragyoku-ekiden-distance-definitions.md']), PageBreak()]

    st += [heading('4.17 2位チームは中継でどの位置にいたか'),
           P('各年度の最終2位チームだけを取り出し、中継順位を集計しました。「中継2位以内」は県駅伝出場圏内にいる割合、「中継3位以内」は圏外からの逆転余地も含めた近接位置の割合です。最終区間後の100%は定義上の確認値です。'),
           vbar_chart('男子: 最終2位チームの中継位置', men_second_checkpoint[0], [men_second_checkpoint[1], men_second_checkpoint[2]], ['中継2位以内','中継3位以内'], '縦軸: 割合（%）', height=68*mm, value_min=0, value_max=100),
           vbar_chart('女子: 最終2位チームの中継位置', women_second_checkpoint[0], [women_second_checkpoint[1], women_second_checkpoint[2]], ['中継2位以内','中継3位以内'], '縦軸: 割合（%）', height=68*mm, value_min=0, value_max=100),
           table([['部門','区間後','標本','2位チームの平均通過順位'], *[['男子', label, str(sample), f'{rank:.2f}位'] for label, sample, rank in zip(men_second_checkpoint[0], men_second_checkpoint[4], men_second_checkpoint[3])], *[['女子', label, str(sample), f'{rank:.2f}位'] for label, sample, rank in zip(women_second_checkpoint[0], women_second_checkpoint[4], women_second_checkpoint[3])]], [22*mm,30*mm,28*mm,58*mm]),
           chart_note('歴代2位チームにも中継3位以下からの到達例があります。序盤の順位だけを失敗と読まず、差・集団・区間適性・終盤の残りを確認します。'),
           source_note(['input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json']), PageBreak()]

    st += [heading('4.18 2位チームの区間順位: 速さより「揃え方」を見る'),
           P('歴代の最終2位チームについて、各区間が区間順位3位以内・5位以内に入った割合を示します。これは「全区間で上位3位が必要」という条件ではありません。むしろ、1区間の大きな後退を残りの区間でどう補ったかを実測から確認する補助指標です。'),
           vbar_chart('男子: 2位チームの区間順位の分布', men_second_leg[0], [men_second_leg[1], men_second_leg[2]], ['区間3位以内','区間5位以内'], '縦軸: 割合（%）', height=68*mm, value_min=0, value_max=100),
           vbar_chart('女子: 2位チームの区間順位の分布', women_second_leg[0], [women_second_leg[1], women_second_leg[2]], ['区間3位以内','区間5位以内'], '縦軸: 割合（%）', height=68*mm, value_min=0, value_max=100),
           table([['部門','区間','標本','区間順位の中央値'], *[['男子', label, str(sample), f'{rank:.1f}位'] for label, sample, rank in zip(men_second_leg[0], men_second_leg[4], men_second_leg[3])], *[['女子', label, str(sample), f'{rank:.1f}位'] for label, sample, rank in zip(women_second_leg[0], women_second_leg[4], women_second_leg[3])]], [22*mm,30*mm,28*mm,58*mm]),
           callout('編成への使い方', '2位の再現条件は、最速選手を一人置くことではなく、区間順位の極端な落ち込みを管理することです。候補ごとにPB、3km相当TT、過去の単独走、後半低下、補員との差を分けて採点します。', colors.HexColor('#EAF3FA')),
           source_note(['input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json']), PageBreak()]

    st += [heading('4.19 2位の境界: 優勝との差と3位との差'),
           P('最終2位を基準に、優勝との差と3位との差を年度別に秒/kmで表示します。3位との差が小さい年ほど、2位の出場圏を守るには終盤の順位・受け渡し・失速管理の相対的重要性が高まります。ただし差が大きい/小さい原因はこの図だけでは決まりません。'),
           line_chart('男子: 2位の前後差（年度別）', [men_second_margins[0], men_second_margins[1]], ['優勝との差','3位との差'], '縦軸: 秒/km（小さいほど接戦）', height=68*mm),
           table(margin_summary_rows(*men_second_margins), [38*mm,22*mm,27*mm,27*mm,27*mm,35*mm]),
           line_chart('女子: 2位の前後差（年度別）', [women_second_margins[0], women_second_margins[1]], ['優勝との差','3位との差'], '縦軸: 秒/km（小さいほど接戦）', height=68*mm),
           table(margin_summary_rows(*women_second_margins), [38*mm,22*mm,27*mm,27*mm,27*mm,35*mm]),
           chart_note('目標を「優勝との差」だけで作らず、必ず「3位との差」も同時に確認します。2位を守るための想定は、総合見込み、最終区間前の位置、補員投入時の差の3条件で作成します。'),
           source_note(['input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json','docs/aragyoku-ekiden-distance-definitions.md']), PageBreak()]

    # selection / race plan
    st += [heading('5. 選考・区間配置の実戦プロトコル'), heading('5.1 選考順序',2),
           table([['順','確認項目','記録方法','合格の考え方'],['1','健康・出場可否','睡眠、痛み、既往、RPE、練習出席','痛み・発熱・歩容異常はタイムより優先して止める'],['2','駅伝適性','3km前後TT、後半1km、単独走、抜き返し','PBより「後半低下」「単独走」「連続練習の回復」を評価'],['3','区間適性','短区間の立ち上がり、3kmの巡航、混戦','各区間の要求と選手の強みを一致させる'],['4','チーム期待値','6人/5人の合計、補員差、欠場シナリオ','最速個人の並びではなくチーム合計を比較'],['5','当日決定','直近48hの状態、気象、アップ反応','事前順位を盲信せず、代替案へ切り替える']], [12*mm,29*mm,48*mm,87*mm]),
           heading('5.2 配置を数値で確認するワークシート',2),
           P('各候補の「想定区間タイム」を作るときは、トラックPBに一定係数を掛けるだけで確定してはいけません。過去の同距離駅伝区間、TT、坂・風の条件、前走者からの位置、直近疲労を別欄に残してください。'),
           table([['候補','想定区間','想定値','根拠A（TT/駅伝）','根拠B（PB）','当日代替','注意信号'],['','','','','','',''],['','','','','','',''],['','','','','','',''],['','','','','','',''],['','','','','','',''],['','','','','','','']], [25*mm,24*mm,24*mm,34*mm,27*mm,24*mm,29*mm], style='table'),
           heading('5.3 秒差シナリオでオーダーを比較する',2),
           P('オーダー比較は「予想順位」ではなく、各区間の根拠付き想定値を合計して行います。基本・暑熱/強風・欠場代替の3シナリオを同じ表に置き、最速の1人を並べる案と、5人/6人の失速リスクを抑える案を比べます。下表は記入用であり、空欄を一般式で自動推定しません。'),
           table([['区間','基本想定','悪条件調整','代替時調整','根拠メモ','差分累計'],['1区','','','','',''],['2区','','','','',''],['3区','','','','',''],['4区','','','','',''],['5区','','','','',''],['6区（女子は—）','','','','',''],['合計','','','','','']], [21*mm,27*mm,31*mm,31*mm,46*mm,20*mm]),
           heading('5.4 タスキと中継の実戦設計',2),
           table([['局面','走者','中継担当','指導者/記録担当'],['20-30分前','アップ完了・衣類とゼッケン確認・最初のコールを1つ決める','受け渡し位置と進入方向、予備タスキ・防寒を確認','前走者/次走者/代替の所在、時計同期、連絡手段を確認'],['5分前','流し後に保温・トイレ・靴紐を終える','タスキを持つ手・受ける手・走り出す方向を再確認','順位だけでなく先頭差・風・雨・単独/集団を短く伝える'],['受け渡し','最後の合図を増やさない。受け取ったら前方へ加速','進入者を見て、渡したら安全に離脱','通過時刻、順位、差、選手の様子を記録'],['直後','止まらず安全に移動・保温・水分','次区間へ必要情報を1文で伝える','異常所見ならタイムより保護者・大会運営・学校手順を優先']], [25*mm,46*mm,52*mm,53*mm]),
           callout('禁止事項', '「1区は最速」「アンカーは最速」の固定観念、前年の区間配置のコピペ、短区間でのウォームアップ不足、補員の練習からの除外。この4つは再現性を下げます。', colors.HexColor('#FAE9E9')), PageBreak()]

    # Training
    st += [heading('6. 大会までの逆算スケジュール（2026日程を反映）'),
           P('保存カレンダーには「荒玉中体連駅伝」が2026年10月14日（水）、予備日が10月15日（木）としてscheduled登録されています。ただし開始時刻・会場・競技要項の値はこのスナップショットにありません。日付はD0として使えますが、時刻・集合・コース運用は大会要項で最終確認してください。'),
           heading('6.0 2026年の日付入り逆算（カレンダー記載ベース）',2),
           table([['日付','D表記','カレンダー上の事項','運用上の意味'],['9/29（火）','D-15','校内行事: 駅伝試走（午前）','試走は走力テストにしない。導線、受け渡し、アップ地点、危険箇所、計時方法を確認'],['10/4（日）','D-10','奥球磨駅伝大会の登録あり','参加対象・負荷・移動を確認。参加する選手は以後の質を追加しない'],['10/10（土）','D-4','熊本県長距離記録会の登録あり','参加対象を確認。大会扱いなら翌日以降の回復を優先'],['10/12（月）','D-2','スポーツの日','900m/600mの刺激を実施する場合も1本のみ。翌日追い込まない'],['10/14（水）','D0','荒玉中体連駅伝','気象・体調・公式導線でA/B/Cを最終決定'],['10/15（木）','D+1 / 予備日','荒玉中体連駅伝予備日','雨天順延の可能性を前提に、10/14直後の回復・移動計画を固定しすぎない']], [24*mm,23*mm,54*mm,75*mm]),
           table([['期間','狙い','主な内容','負荷管理・中止基準'],['D-35〜D-22','土台と選考材料','3km前後の閾値走、短い坂、レースペース確認、補員も同じ枠で','急な距離増なし。痛みが増すなら質を中止し評価へ'],['D-21〜D-15','区間特異性','区間距離に近い分割走、タスキ受け渡し、風・単独走の練習','高強度は週2回以内、同一日に2つの主練習を置かない'],['D-14〜D-8','チーム最適化','候補区間での実戦シミュレーション、補員含むオーダー演習','TTは1回で十分。記録の良し悪しより回復を評価'],['D-7〜D-3','鋭さを残す','総量を落とし、短いレースペース刺激、動き作り','疲労を抜く。新しい靴・補給・練習は導入しない'],['D-2','刺激のみ','800m: 600m×1、1500m: 900m×1（最大1000m、1本のみ）','翌日は追い込まない。違和感が出たら即中止'],['D-1','回復と確認','短いジョグ、流し、受付・導線・持ち物確認','睡眠優先。判断を増やさない'],['D0','実行','アップ、区間別コール、給水、補員待機','気象・体調に応じて事前プランをA/B/Cで切替']], [23*mm,31*mm,65*mm,57*mm]),
           heading('6.1 1週間のテンプレート（例）',2),
           table([['曜日','主目的','例','確認'],['月','回復','ジョグ + 可動域 + 補強','日曜の疲労が抜けたか'],['火','有酸素の質','閾値走または分割テンポ','後半のフォーム'],['水','回復・技術','短いジョグ、ドリル、流し','痛みの有無'],['木','駅伝特異性','区間相当の分割走/坂/レースペース','想定区間の感覚'],['金','回復','短いジョグまたは休養','睡眠と食欲'],['土','シミュレーション','タスキ、集団・単独走、補員も参加','運用の詰まり'],['日','低強度/休養','個別の回復走または完全休養','翌週に持ち越さない']], [17*mm,30*mm,73*mm,56*mm]),
           heading('6.2 練習の実行条件と切り替え表',2),
           table([['確認時点','緑: 実施候補','黄: 内容を軽くする','赤: 中止して共有'],['起床時','睡眠・食欲・歩行が普段通り','疲労感が高い、張りが残る','発熱、胸痛、息苦しさ、めまい、強い痛み、歩容異常'],['アップ','動きが整い、痛みが増えない','片側の張り、フォームの乱れ','痛みが増える、走れない、普段と明らかに異なる'],['主練習中','後半も動作が保てる','設定を下げる/本数を減らす/ジョグへ','中断して保温・水分・学校と保護者の手順へ'],['翌日','睡眠・食欲・痛みが基準内','回復走または休養','大会翌日は原則休み。自主練もEまで']], [24*mm,48*mm,52*mm,52*mm]),
           P('この表は診断や復帰許可の基準ではありません。症状・既往・医療上の指示がある場合は、学校・保護者・医療者の判断を優先します。','small'),
           heading('6.3 大会週の負荷を可視化する記録欄',2),
           table([['日','睡眠','主観疲労 1-10','痛み 0-10','主練習の実施/変更','翌朝への持越し'],['D-7','','','','',''],['D-6','','','','',''],['D-5','','','','',''],['D-4','','','','',''],['D-3','','','','',''],['D-2','','','','',''],['D-1','','','','','']], [17*mm,25*mm,35*mm,27*mm,42*mm,30*mm]),
           source_note(['docs/adr/005-pre-race-rp-stimulus.md','docs/adr/006-practice-meets-not-load.md','docs/adr/007-post-race-rest.md','docs/adr/008-daniels-vdot-gz-guidance.md']), PageBreak()]

    # day of race
    st += [heading('7. レース週・当日運用'), heading('7.1 気象に対する準備',2),
           P('保存済みの10-12時気象では、2020-2025年に気温17.4-30.3℃、最大風速0.7-3.7m/sが観測されています。平均値で準備せず、気温・風・日射・雨の組合せでA/B/Cプランを作ります。'),
           table([['開催日','気温帯（10-12時）','最大風速','主な風向'],*weather_summary()], [40*mm,51*mm,34*mm,51*mm]),
           heading('7.2 A/B/Cプラン',2),
           table([['状況','A: 標準','B: 暑熱・強日射','C: 強風・雨'],['アップ','通常のジョグ→ドリル→流し','開始を早め、日陰・水分・冷却を確保','防風・防寒、衣類を濡らさない'],['ペース','最初の400-800mは事前上限','前半をさらに保守的に、給水計画を明確化','単独区間の無理な前追いを避け、集団活用'],['連絡','中間通過と順位','体調・熱症状を最優先','風向・滑りやすい地点を共有'],['切替条件','RPE/フォーム異常','熱症状、頭痛、悪寒、異常な心拍感','体温低下、転倒リスク、視界不良']], [27*mm,49*mm,49*mm,49*mm]),
           heading('7.3 当日チェックリスト',2),
           table([['時点','必須確認'],['前日','オーダーA/B/C、補員順、連絡網、ゼッケン、タスキ、靴下・予備靴、天気再確認'],['会場到着','導線、トイレ、アップ場所、受け渡しゾーン、荷物・防寒、緊急連絡'],['各区間前','シューズ、ゼッケン、ウォームアップ完了、直前の水分、コールの言葉を1つに絞る'],['レース中','タイムだけでなく姿勢・腕振り・表情・単独/集団を観察。指示は短く具体的に'],['直後','保温、水分、軽食、歩容・痛み確認、クールダウン、次走者への情報共有'],['終了後','記録確認、個別の回復、24-48hの痛み追跡、振り返りは事実と解釈を分ける']], [33*mm,143*mm]),
           heading('7.4 役割カードと連絡の最小単位',2),
           table([['役割','開始前に確認','レース中に行うこと','してはいけないこと'],['統括','A/B/C、欠場時の決定者、緊急連絡','安全判断、役割間の情報統合','複数の人が別の作戦を指示する'],['区間担当','走者の状態、アップ、移動導線','短い事実: 差・順位・単独/集団・次の行動','長い技術指導や曖昧な励まし'],['記録担当','時計同期、通過地点、記録様式','時刻・順位・差・観察を記録','記憶だけに頼る'],['補員担当','補員のアップ・防寒・食事・連絡','交代判断に備え、同じ情報を共有','補員を待機だけにして孤立させる'],['保護者連絡','学校の連絡ルール、医療・移動情報','必要時のみ統括と一元連絡','選手への追加指示や未確認情報の拡散']], [23*mm,42*mm,55*mm,56*mm]),
           source_note(['weather/aratama-ekiden-tamana-jma.csv','docs/tamana-weather.md']), PageBreak()]

    # safety
    st += [heading('8. 安全・回復・栄養の最低基準'),
           callout('医学的な判断について', '本章は一般的なチーム運用です。発熱、胸痛、息苦しさ、めまい、強い痛み、歩容異常、食事・水分が取れない状態は、競技継続ではなく保護者・医療者・学校の手順を優先してください。', colors.HexColor('#FAE9E9')),
           heading('8.1 故障リスクを上げない原則',2),
           table([['領域','実行','避けること'],['負荷','走行量と高強度日を記録し、急増を避ける','遅れを取り戻すための連続追い込み'],['痛み','部位・左右差・走ると増えるかを毎日確認','痛みを「根性」で評価しない'],['睡眠','大会週は平日も起床時刻を大きくずらさない','前日に睡眠を借金から取り戻そうとする'],['補給','普段から使う炭水化物・水分を事前に試す','当日に初めてのサプリ・濃い飲料'],['シューズ','摩耗・サイズ・靴紐を練習で確認','大会当日の新品導入']], [24*mm,76*mm,76*mm]),
           heading('8.2 回復の記録欄',2), table([['日付','睡眠','主観疲労 1-10','痛み 0-10・部位','食欲/水分','練習変更'],['','','','','',''],['','','','','',''],['','','','','',''],['','','','','',''],['','','','','','']], [25*mm,25*mm,35*mm,45*mm,25*mm,25*mm]), PageBreak()]

    st += [heading('9. レース後の検証と次年度への資産化'),
           P('振り返りは「良かった/悪かった」で終わらせず、翌年に再利用できる事実を残します。タイムと順位だけでは、風・気温・単独走・受け渡し・体調の差を説明できません。事実、解釈、次の実験を分けて記録します。'),
           heading('9.1 24時間以内に確定する事実',2),
           table([['領域','残すデータ','保存先/責任'],['公式結果','総合・区間・通過順位・差・DNS/DNF','結果表を正本として保存'],['当日条件','気温、風、雨、路面、スタート/区間の時刻','観測値と担当者メモを区別'],['実行','オーダーA/B/Cのどれを使ったか、交代の有無','統括が確定'],['選手状態','睡眠、主観疲労、痛み、補給、アップ反応','個人情報の扱いを学校ルールに従う'],['運用','タスキ・移動・連絡・荷物の詰まり','役割別に1件ずつ']], [27*mm,74*mm,49*mm]),
           heading('9.2 検証会の質問（解釈を事実から分ける）',2),
           table([['事実を問う','解釈を問う','次回試すこと'],['どの中継で、誰が、何秒差・何位だったか','差が動いた要因は風、単独走、ペース、体調、配置のどれか','次の試走で何を計測すれば判別できるか'],['想定値と実績の差は各区間何秒か','推定根拠A/Bのどちらが外れたか','TT、後半1km、受け渡し、気象記録のどれを改善するか'],['赤/黄の安全信号はあったか','見逃しは判断基準か連絡経路か','中止/代替の決定者を一人に固定できるか']], [56*mm,60*mm,55*mm]),
           heading('9.3 次版PDFの更新規則',2),
           P('公式結果が入ったら、まず年度別transcript JSONを更新し、validate_transcript.pyを通過させます。距離・氏名・区間タイム・順位を正本以外で埋めず、未確定はunknownのまま残します。その後に派生JSON、統計表、PDFを再生成します。これにより、次年度の分析で古い推測や手計算を持ち越しません。'),
           source_note(['docs/adr/014-aragyoku-full-transcript-schema.md','input/aragyoku/validate_transcript.py','docs/adr/007-post-race-rest.md']), PageBreak()]

    # appendices overview
    st += [heading('付録A. 歴代サマリー'), heading('A.1 表彰台回数（2012-2025の収録年度）',2),
           table([['男子 学校','表彰台回数'], *[[k,str(v)] for k,v in man_podium.most_common()],], [76*mm,35*mm]), Spacer(1,4*mm),
           table([['女子 学校','表彰台回数'], *[[k,str(v)] for k,v in wom_podium.most_common()],], [76*mm,35*mm]),
           P('表彰台回数は、複数年度にわたる校力の記録であり、2026年の順位を直接予測するものではありません。','small'), PageBreak()]

    # all historical records, detailed
    for gender, dataset in [('男子', men), ('女子', women)]:
        st += [heading(f'付録B. {gender} 全年度結果・区間一覧')]
        st += [P('各年度の総合順位・総合タイム・区間の氏名（保存値）・学年・区間タイムを再掲します。unknownは、原画像が未判読または高解像度原票にアクセスできず、推測で補わなかったセルです。', 'small')]
        for year, entry in sorted(dataset['years'].items()):
            st += [heading(f'{year}年 {gender}（{entry.get("date") or "日付未確認"}）',2)]
            rows=[['順位','学校','総合','区間（氏名［学年］: 区間タイム）']]
            for team in entry['teams']:
                legs=' / '.join(f"{x['leg']}区 {x.get('name') or 'unknown'}[{x.get('grade') if x.get('grade') is not None else '—'}]: {x.get('split') or '—'}" for x in team['legs'])
                rows.append([str(team['rank']),team['team'],team.get('total') or '—',legs])
            st += [table(rows,[13*mm,28*mm,23*mm,112*mm],style='appendix')]
            st += [P(f'コース距離: {" / ".join(str(x) for x in distance(year, gender))} km', 'small'),Spacer(1,2*mm)]
        st += [PageBreak()]

    # sources
    st += [heading('付録C. 根拠・再現手順'),
           P('本PDFは、以下のローカルデータスナップショットから再生成可能です。Webの検索結果や推測値は、表・順位・タイムの計算に用いていません。'),
           table([['領域','主要根拠','用途'],['歴代結果','input/aragyoku/men_full_2012_2025.json / women_full_2012_2025.json','総合・区間・順位・個人欄'],['検証規則','input/aragyoku/validate_transcript.py','区間和、順位、区間数、アンカー照合'],['距離定義','docs/aragyoku-ekiden-distance-definitions.md','年度補正・平均ペース'],['2026走力','out/analysis/2026_men_1500m_pb_school_ranking.md / 2026_women_800m_1500m_pb_school_ranking.md','学校別の層の把握'],['歴代トラック突合','out/analysis/1500m_sb_band_ekiden.html / aragyoku_women_track_joined.json','近似SB帯の実走例（予測には使わない）'],['歴代ペース','out/analysis/aragyoku_top6_historical_average_pace.md','順位別到達ライン'],['気象','weather/aratama-ekiden-tamana-jma.csv','過去当日気象の幅'],['2026日程','out/2026/calendar.md','10/14開催・10/15予備日のスケジュール確認'],['練習運用','docs/adr/005-pre-race-rp-stimulus.md ほか','大会前・安全の設計']], [31*mm,90*mm,55*mm]),
           heading('C.1 最終確認チェック',2),
           table([['確認','結果'],['PDF内の総合・区間タイム','正本JSONから直接読み込み'],['順位別ペース','年度別距離で再計算'],['男子コース変更','2024年以降17.710kmを適用'],['女子コース','11.855kmを全年度へ適用'],['2026走力の基準日','2026-08-29と明記'],['2026開催日','保存カレンダーの10/14 scheduled・10/15予備日を明記。開始時刻等は要項確認'],['氏名の不確実性','unknown・要原票確認を隠さず表示'],['時間方向の混入','同年度トラック突合は駅伝後の記録を含み得るため予測に使わない'],['医療・安全判断','一般的運用として限定し、診断をしない']], [68*mm,108*mm]),
           P('更新手順: 新しい結果表または2026年公式日程が入手できたら、まず正本データと検証器を更新し、本PDFを再生成してください。個人名の未確定セルを修正する際は、原画像または公式原票を根拠にし、推測で埋めないでください。','body'), PageBreak()]

    st += [heading('付録D. 収録範囲と未取得情報の監査'),
           P('「載っていない情報」を曖昧に残さないため、この版で確認した情報領域と、現スナップショットに存在しないため収録できない領域を明示します。空白を推測で埋めないことは、分析の完全性の一部です。'),
           table([['領域','この版の扱い','根拠 / 制約'],['歴代公式結果','2012-2025の全収録年度・全参加校・全区間を付録Bへ収録','女子2014は原画像未確認。氏名の未確定セルはunknown'],['距離・順位・ペース','年度別距離補正、順位別到達ライン、区間分布、通過順位、順位変動を収録','男子は2024年に距離構成が変更'],['2026競合走力','学校別1500m/800m層、男子3000m層を収録','基準日は2026-08-29。出場可否・直前状態は含まない'],['トラックと駅伝の関係','SB帯別198実走例と女子同年度突合の利用規則を収録','一意換算・レース前予測には使わない'],['日程・気象・運営','10/14と予備日、過去気象、A/B/C、役割、タスキ、記録を収録','開始時刻、会場、コース導線は要項で確認'],['練習・安全','D0逆算、2日前刺激、翌日休養、負荷・回復記録を収録','個人への医療診断・処方は行わない']], [32*mm,75*mm,69*mm]),
           heading('D.1 現時点で原典がないため載せない項目',2),
           table([['未取得 / 未確定項目','PDFでの扱い','入手後の更新先'],['2026年の公式競技要項（開始時刻、会場、導線、招集、区間変更の有無）','推測しない。D0日付のみ保存カレンダーから反映','大会要項を正本として6章・7章を更新'],['コースの地図・標高・危険箇所の公式資料','地形・高低差・曲がり角を断定しない','公式図または試走の計測記録を2章へ追加'],['2026年のエントリー、確定オーダー、欠場情報','学校別PBは候補層としてのみ利用','出場名簿と直前の状態で4章・5章を更新'],['女子2014の結果ボード原票','欠損年度として明示','transcript JSONと付録Bを更新'],['判読できない氏名セルの高解像度原票','unknownを維持','原票を根拠にtranscriptを修正し検証器を通す']], [53*mm,58*mm,65*mm]),
           callout('更新の優先順位', '競技要項・会場導線・エントリーが入手できた時点で、まず当日運用とオーダーの根拠を更新します。結果ボード原票が入手できた時点で、氏名・欠損年度の正本を更新します。いずれも、先に正本と検証を更新してから統計とPDFを再生成します。', colors.HexColor('#F4EEDC')),
           source_note(['out/knowledge-graph.json','input/external/notion/media/ekiden-history/INDEX.md','docs/adr/014-aragyoku-full-transcript-schema.md','out/2026/calendar.md'])]

    # Visual atlas. Each chart is generated here from the same canonical data used above.
    st += [PageBreak(), heading('付録E. 可視化アトラス - 歴代・2026・当日判断'),
           P('この付録は、表の値を視覚的に比較するための図版集です。グラフはすべて本書の正本JSON・既存分析ファイルから生成しています。棒の高さや線の位置を予測値と読まないよう、各ページに標本・単位・制約を付けます。'),
           callout('図版の共通ルール', '青系は男子、緑系は女子を中心に使用します。ペースは秒/km、学校別PBは秒、気象は摂氏・m/sです。距離の異なる年度は総合時間でなくペースに補正しています。', colors.HexColor('#EAF3FA')),
           table([['図版群','目的','注意'],['E.1-E.2','歴代優勝・上位の年度推移','年度差は気象・チーム構成を含む'],['E.3-E.4','表彰台の継続性','2026順位の予測ではない'],['E.5-E.6','過去気象の幅','2026当日の予報ではない'],['E.7-E.33','各年度の結果カード','各年の全参加校と表彰台区間を表示'],['E.34-E.44','区間別分位点','個人目標タイムではない'],['E.45-E.52','2026学校別PBの可視化','出場確定・体調を含まない'],['E.53-E.56','競争差と作戦判断の図','因果推論や順位予測ではない']], [27*mm,65*mm,84*mm]),
           source_note(['input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json','out/analysis/2026_men_1500m_pb_school_ranking.md','out/analysis/2026_women_800m_1500m_pb_school_ranking.md']), PageBreak()]

    # E.1-2: winner/top-rank longitudinal pace lines.
    for gender, dataset in [('男子', men), ('女子', women)]:
        series, names = annual_rank_pace_series(dataset, gender)
        st += [heading(f'E. 年度推移: {gender}の順位別ペース',2),
               P('1位・2位・3位・6位の総合ペースを年度別距離で補正した時系列です。線の高低は1km当たりの秒数であり、低いほど速いことを示します。欠損年度を直線補間していません。'),
               line_chart(f'{gender} 総合順位別ペースの年度推移', series, names, '縦軸: 秒/km（低いほど速い） / 横軸: 年'),
               chart_note('同順位でも年度により競争水準が異なります。1位線だけでなく、2位・3位・6位との間隔を見て競技集団の厚みを確認します。'),
               source_note(['input/aragyoku/men_full_2012_2025.json' if gender == '男子' else 'input/aragyoku/women_full_2012_2025.json','docs/aragyoku-ekiden-distance-definitions.md']), PageBreak()]

    # E.3-4: historical podium counts.
    for gender, podium in [('男子', man_podium), ('女子', wom_podium)]:
        labels, values = podium_count_values(podium)
        st += [heading(f'E. 表彰台の継続性: {gender}',2),
               P('収録年度における表彰台（1-3位）回数です。学校名の表記は年度別正本の保存値です。これは長期的な実績を示すだけで、2026年の人数・学年・出場状態を反映しません。'),
               vbar_chart(f'{gender} 表彰台回数（収録年度）', labels, [values], ['表彰台回数'], '縦軸: 回数'),
               chart_note('回数が同じでも、その内訳（優勝・準優勝・3位）や直近性は異なります。比較は付録Bの年度別結果へ戻って確認します。'),
               source_note(['input/aragyoku/men_full_2012_2025.json' if gender == '男子' else 'input/aragyoku/women_full_2012_2025.json']), PageBreak()]

    # E.5-6: weather variability.
    weather_labels, temp_min, temp_max, max_wind = weather_chart_values()
    st += [heading('E. 過去当日気象: 気温レンジ',2),
           P('保存済みの開催日10-12時データの最低・最高気温です。各年の2本の棒は同じ時間帯の観測範囲を示します。年表示は開催年です。'),
           vbar_chart('荒玉開催日の気温レンジ（10-12時）', weather_labels, [temp_min, temp_max], ['最低気温','最高気温'], '縦軸: ℃'),
           chart_note('これは当日の予報ではありません。大会週に最新予報を確認し、暑熱・強風・雨のA/B/C切替へ使います。'),
           source_note(['weather/aratama-ekiden-tamana-jma.csv']), PageBreak()]
    st += [heading('E. 過去当日気象: 最大風速',2),
           P('保存済みの開催日10-12時データから、各日の最大平均風速を表示します。風向、降水、日射、路面は別に確認が必要です。'),
           vbar_chart('荒玉開催日の最大平均風速（10-12時）', weather_labels, [max_wind], ['最大平均風速'], '縦軸: m/s'),
           chart_note('同じ風速でも向き・露出・集団状況で影響は変わります。単独走で無理に前を追う根拠にはしません。'),
           source_note(['weather/aratama-ekiden-tamana-jma.csv']), PageBreak()]

    # E.7-33: one visual result card per observed race.
    for gender, dataset in [('男子', men), ('女子', women)]:
        for year_s, entry in sorted(dataset['years'].items()):
            labels, pace_values = year_total_pace_values(entry, gender)
            leg_labels, podium_values, podium_names = year_podium_leg_paces(entry, gender)
            st += [heading(f'E. {year_s}年 {gender} 結果カード',2),
                   P(f"開催日: {entry.get('date') or '未確認'}。上図は全参加校の総合ペース（秒/km、低いほど速い）、下図は表彰台3校の区間ペースです。男子は年度ごとのコース距離で補正しています。"),
                   vbar_chart(f'{year_s}年 {gender}: 全参加校の総合ペース', labels, [pace_values], ['総合ペース'], '縦軸: 秒/km（低いほど速い）', height=67*mm),
                   vbar_chart(f'{year_s}年 {gender}: 表彰台3校の区間ペース', leg_labels, podium_values, podium_names, '縦軸: 秒/km（低いほど速い）', height=67*mm),
                   chart_note('学校ごとの棒・線はその年の結果であり、異なる年度間の総合時間比較は避けます。区間が欠損のチームは値を作らず、正本のまま扱います。'),
                   source_note([f'input/aragyoku/{"men" if gender == "男子" else "women"}_full_2012_2025.json','docs/aragyoku-ekiden-distance-definitions.md']), PageBreak()]

    # E.34-44: one distribution page per leg.
    for gender, dataset in [('男子', men), ('女子', women)]:
        leg_count = 6 if gender == '男子' else 5
        for leg_no in range(1, leg_count + 1):
            qlabels, qvalues, n = leg_distribution_values(dataset, gender, leg_no)
            st += [heading(f'E. {gender} {leg_no}区: ペース分布',2),
                   P(f'収録年度の全有効区間 {n}本を、当該年度の区間距離で秒/kmへ換算した分位点です。10%は速い側、90%は遅い側です。'),
                   vbar_chart(f'{gender} {leg_no}区のペース分位点', qlabels, [qvalues], ['秒/km'], '縦軸: 秒/km（低いほど速い）', height=82*mm),
                   chart_note('分布は「その区間の歴史的な結果の幅」です。選手個人の設定や必達ラインに直接変換せず、区間相当TT・後半低下・体調と併読します。'),
                   source_note(['input/aragyoku/men_full_2012_2025.json' if gender == '男子' else 'input/aragyoku/women_full_2012_2025.json','docs/aragyoku-ekiden-distance-definitions.md']), PageBreak()]

    # E.45-52: 2026 PB views, one chart per available depth definition.
    pb_views = [
        ('男子 1500m 上位4人平均', men4), ('男子 1500m 上位6人平均', men6),
        ('男子 3000m 上位4人平均', men3000_4), ('男子 3000m 上位6人平均', men3000_6),
        ('女子 800m 上位3人平均', women3), ('女子 800m 上位5人平均', women5),
        ('女子 1500m 上位3人平均', rank_markdown_rows(WOMEN_RANK,'## 1500m・上位3人平均')),
        ('女子 1500m 上位5人平均', rank_markdown_rows(WOMEN_RANK,'## 1500m・上位5人平均')),
    ]
    for title, rows in pb_views:
        labels, values = ranking_chart_values(rows)
        st += [heading(f'E. 2026 PB層: {title}',2),
               P('学校別の上位人数平均を秒で可視化しています。棒が低いほど平均記録が速いことを示します。基準日は2026年8月29日で、在籍・出場・故障・直前の変化は別途確認が必要です。'),
               vbar_chart(title, labels, [values], ['上位人数平均'], '縦軸: 秒（低いほど速い）', height=85*mm),
               chart_note('人数条件を満たす学校だけが表示されます。順位の予測ではなく、選考前に候補層を確認するための図です。'),
               source_note([MEN_RANK.name if title.startswith('男子') else WOMEN_RANK.name]), PageBreak()]

    # E.53-56: competition-gap and decision figures.
    for gender, dataset in [('男子', men), ('女子', women)]:
        a=annual_gap_series(dataset, gender, 1, 2)
        b=annual_gap_series(dataset, gender, 3, 6)
        st += [heading(f'E. {gender}: 上位差の年度推移',2),
               P('優勝-2位差と3位-6位差を、それぞれ秒/kmに距離補正して表示します。低い値ほど同順位間の差が小さいことを示します。'),
               line_chart(f'{gender}: 上位の競争差', [a,b], ['1位-2位差','3位-6位差'], '縦軸: 秒/km（低いほど差が小さい）'),
               chart_note('差が小さい年は、1区間の作戦・受け渡し・体調の影響が相対的に大きくなり得ます。ただし因果はこの図だけで確定しません。'),
               source_note(['input/aragyoku/men_full_2012_2025.json' if gender == '男子' else 'input/aragyoku/women_full_2012_2025.json','docs/aragyoku-ekiden-distance-definitions.md']), PageBreak()]
    for gender, dyn in [('男子', men_dyn), ('女子', women_dyn)]:
        labels=[x[0] for x in dyn['movement']]
        gains=[int(x[4]) for x in dyn['movement']]
        drops=[int(x[5]) for x in dyn['movement']]
        st += [heading(f'E. {gender}: 2位以上の順位変動が起きた区間',2),
               P('各区間で、前区間から2位以上改善したチーム数と2位以上後退したチーム数です。比較母数は同一チームで連続した通過順位が確認できる例に限ります。'),
               vbar_chart(f'{gender}: 大きな順位変動の件数', labels, [gains,drops], ['2位以上改善','2位以上後退'], '縦軸: 件数', height=82*mm),
               chart_note('平均順位改善がゼロに近くても大きな変動は起こります。区間の固定的な役割付けではなく、走者と当日の状況に合わせて判断します。'),
               source_note(['input/aragyoku/men_full_2012_2025.json' if gender == '男子' else 'input/aragyoku/women_full_2012_2025.json']), PageBreak()]
    st += [heading('E. 最終図: 根拠から当日判断まで',2),
           P('100ページ版の最終図です。すべての判断は、正本データ、2026走力、日程・気象、検証規則を分けて確認した後に行います。どれか一つの図表だけで選考・出走・安全を決定しません。'),
           provenance_diagram(),
           chart_note('レース後記録を正本・検証・図表へ戻すことで、翌年の分析精度を高めます。'),
           source_note(['docs/adr/014-aragyoku-full-transcript-schema.md','input/aragyoku/validate_transcript.py','out/2026/calendar.md'])]
    return st


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT)))
    doc=PlaybookDoc(str(OUT),pagesize=A4,leftMargin=17*mm,rightMargin=17*mm,topMargin=17*mm,bottomMargin=17*mm)
    frame=Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='main')
    doc.addPageTemplates([PageTemplate(id='main',frames=[frame],onPage=footer)])
    doc.multiBuild(story())
    print(OUT)


if __name__ == '__main__':
    main()
