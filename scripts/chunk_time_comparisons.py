"""Schema-reviewed comparisons of literal clock cells in source CSV snapshots.

The snapshot values are compared as recorded. No age category or season is
inferred from filenames, and missing affiliations are not invented.
"""
import csv
from decimal import Decimal
import io
import re

CLOCK = re.compile(r'^(\d+):(\d{2}(?:\.\d+)?)$')
FIELD = re.compile(r'^(?:\d+m|\d+km)SB$')


def clock_seconds(value):
    m = CLOCK.fullmatch(value)
    if not m or not 0 <= Decimal(m[2]) < 60:
        raise ValueError('invalid clock cell')
    seconds = Decimal(m[1]) * 60 + Decimal(m[2])
    if seconds <= 0:
        raise ValueError('nonpositive clock cell')
    return seconds


def decimal_text(value):
    return format(value.normalize(), 'f')


def label(row, header):
    name = row[header.index('名前')].strip()
    if not name:
        raise ValueError('missing athlete identity')
    team = row[header.index('所属')].strip()
    return name + ('（' + team + '）' if team else '')


def render_comparison(header, rows, field):
    if not FIELD.fullmatch(field) or len(rows) != 2:
        raise ValueError('unsupported comparison schema')
    a, b = [r['cells'] for r in rows]
    if len(a) != len(header) or len(b) != len(header):
        raise ValueError('CSV column alignment differs')
    gender = a[header.index('性別')]
    if gender not in ('男子', '女子') or gender != b[header.index('性別')]:
        raise ValueError('different or unknown gender groups')
    if a[header.index('名前')] == b[header.index('名前')]:
        raise ValueError('same identity; cannot establish distinct athletes')
    n = header.index(field); va, vb = a[n], b[n]
    sa, sb = clock_seconds(va), clock_seconds(vb)
    la, lb = label(a, header), label(b, header)
    event = field.removesuffix('SB'); gap = decimal_text(abs(sa - sb))
    question = f'保存済みSBデータベースで、{gender}{event}の{la}と{lb}の掲載タイムは何秒差？'
    if sa == sb:
        result = '同タイムで、差は0秒です。'
    else:
        result = f'{la if sa < sb else lb}が{gap}秒速い掲載値です。'
    answer = f'保存データの{event}SB欄では、{la}は{va}、{lb}は{vb}です。{result}'
    return question, answer, {'operation': 'clock_cell_difference', 'field': field,
                             'rows': [r['row'] for r in rows], 'gap_seconds': gap,
                             'faster_row': rows[0]['row'] if sa < sb else rows[1]['row'] if sb < sa else None}


def validate_csv_comparison(entry, chunk, source_text):
    evidence = entry.get('evidence') or []
    if len(evidence) != 1 or evidence[0].get('kind') != 'csv-rows':
        raise ValueError('expected CSV record evidence')
    ev = evidence[0]; header = ev['header']; rows = ev['rows']
    full = list(csv.reader(io.StringIO(source_text)))
    if not full or full[0] != header or chunk['evidence']['header'] != header:
        raise ValueError('source header drift')
    assigned = {r['row']: r['cells'] for r in chunk['evidence']['units']}
    if len(rows) != 2 or len({r['row'] for r in rows}) != 2:
        raise ValueError('comparison requires two distinct records')
    for row in rows:
        index = row['row']
        if not isinstance(index, int) or index < 1 or index >= len(full) or full[index] != row['cells']:
            raise ValueError('source row drift')
        if assigned.get(index) != row['cells']:
            raise ValueError('record outside assigned chunk')
    question, answer, calculation = render_comparison(header, rows, entry['calculation']['field'])
    if entry['questions'] != [question] or entry['answer'] != answer or entry['calculation'] != calculation:
        raise ValueError('comparison question, answer or arithmetic drift')
    # Independent assertion of the winner and gap using colon-part expansion,
    # rather than relying solely on the answer renderer's result.
    times = []
    for row in rows:
        raw = row['cells'][header.index(calculation['field'])]
        pieces = [Decimal(p) for p in raw.split(':')]
        times.append(sum(p * (Decimal(60) ** i) for i, p in enumerate(reversed(pieces))))
    if Decimal(calculation['gap_seconds']) != abs(times[0] - times[1]):
        raise ValueError('independent arithmetic check failed')
