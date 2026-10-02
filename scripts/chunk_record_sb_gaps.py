"""Compare a record with the SB field in that same saved JSON row.

The SB field is a snapshot value, never asserted to be current or race-day PB.
"""
from datetime import date
from decimal import Decimal
import re
from chunk_time_comparisons import clock_seconds,decimal_text
from manual_json_evidence import validate_manual_json
SOURCES={'input/external/notion/databases/2026年度中学生記録/rows.json','out/analysis/notion_records_2026.json'}

def render_gap(unit):
    if not re.fullmatch(r'/\d+',unit['pointer']) or not isinstance(unit['value'],dict):raise ValueError('record row required')
    r=unit['value'];name=r.get('name','').strip();gender=r.get('gender');distance=r.get('distance')
    if not name or '\ufffd' in name or gender not in ('男子','女子') or not re.fullmatch(r'\d+(?:m|km)',distance or ''):raise ValueError('missing or damaged record identity')
    day=r['date'].replace('/','-');date.fromisoformat(day)
    observed,sb=r['time_text'],r['sb_text'];os,ss=clock_seconds(observed),clock_seconds(sb)
    recorded=Decimal(str(r['record_seconds']))
    if not recorded.is_finite() or recorded!=os:raise ValueError('stored seconds differs from displayed time')
    delta=os-ss;label=name+('（'+r['affiliation']+'）' if r.get('affiliation') else '')
    q=f'保存資料の{day}・{gender}{distance}の{label}の{observed}は、同じ掲載行のSB欄より何秒違う？'
    result=f'この記録の方が{decimal_text(delta)}秒遅い値です。' if delta>0 else f'この記録の方が{decimal_text(-delta)}秒速い値です。' if delta<0 else '同タイムで差は0秒です。'
    answer=f'同じ保存行では、記録は{observed}、SB欄は{sb}です。{result}'
    calc={'operation':'record_vs_saved_sb_clock_gap','pointer':unit['pointer'],'delta_seconds':decimal_text(delta)}
    return q,answer,calc

def validate_gap(entry,chunk,source_text):
    if entry['sources'][0] not in SOURCES:raise ValueError('unsupported SB snapshot source')
    ev=entry.get('evidence') or []
    if len(ev)!=1 or ev[0].get('kind')!='json-unit':raise ValueError('one JSON row required')
    validate_manual_json(entry,chunk,source_text)
    unit=ev[0]['unit'];q,a,calc=render_gap(unit)
    if entry['questions']!=[q] or entry['answer']!=a or entry['calculation']!=calc:raise ValueError('record/SB claim drift')
    row=unit['value']
    def independent(value):
        pieces=value.split(':');return Decimal(pieces[0])*60+Decimal(pieces[1])
    if independent(row['time_text'])-independent(row['sb_text'])!=Decimal(calc['delta_seconds']):raise ValueError('independent SB delta fails')
