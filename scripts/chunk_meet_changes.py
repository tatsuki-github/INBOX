"""One-athlete comparison between the two literal meet columns in the 2025 table."""
import csv,io
from decimal import Decimal,InvalidOperation
from chunk_time_comparisons import clock_seconds,decimal_text
SOURCE='input/external/drive/shared/記録データベース/2025年度/選手権と通信のタイム差.csv'

def render_change(header,row):
    if len(header)!=len(row['cells']):raise ValueError('column alignment differs')
    d=dict(zip(header,row['cells']));name=d['姓'].strip()+d['名'].strip()
    if not name or '\ufffd' in name:raise ValueError('missing or damaged identity')
    a,b=d['選手権800m記録'],d['通信800m記録'];before,after=clock_seconds(a),clock_seconds(b);delta=after-before
    try:stored=Decimal(d['選手権からのタイム差'])
    except InvalidOperation:raise ValueError('invalid stored difference')
    if not stored.is_finite() or stored!=delta:raise ValueError('stored difference disagrees with clock cells')
    label=name+('（'+d['所属']+'）' if d.get('所属') else '')
    result=f'{decimal_text(-delta)}秒速くなった掲載値です。' if delta<0 else f'{decimal_text(delta)}秒遅くなった掲載値です。' if delta>0 else '同タイムで差は0秒です。'
    q=f'2025年度の選手権・通信比較表で、{label}の800m保存記録は選手権から通信へ何秒変わった？'
    a=f'選手権は{a}、通信は{b}です。{result}'
    calc={'operation':'within_athlete_meet_clock_change','row':row['row'],'delta_seconds':decimal_text(delta)}
    return q,a,calc

def validate_change(entry,chunk,source_text):
    if entry['sources']!=[SOURCE]:raise ValueError('unsupported season/source')
    ev=entry['evidence']
    if len(ev)!=1 or ev[0].get('kind')!='csv-rows' or len(ev[0]['rows'])!=1:raise ValueError('one typed source row required')
    h=ev[0]['header'];r=ev[0]['rows'][0];full=list(csv.reader(io.StringIO(source_text)))
    if full[0]!=h or chunk['evidence']['header']!=h:raise ValueError('header drift')
    n=r['row']
    if type(n)is not int or not 0<n<len(full) or full[n]!=r['cells']:raise ValueError('source row drift')
    if {u['row']:u['cells'] for u in chunk['evidence']['units']}.get(n)!=r['cells']:raise ValueError('outside assigned chunk')
    q,a,calc=render_change(h,r)
    if entry['questions']!=[q] or entry['answer']!=a or entry['calculation']!=calc:raise ValueError('within-athlete change drift')
    def independent(value):
        minutes,seconds=value.split(':');return Decimal(minutes)*60+Decimal(seconds)
    raw=dict(zip(h,r['cells']))
    if independent(raw['通信800m記録'])-independent(raw['選手権800m記録'])!=Decimal(calc['delta_seconds']):raise ValueError('independent delta disagrees')
