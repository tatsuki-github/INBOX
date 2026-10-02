"""Date- and event-bound comparisons of literal recorded meet times.

These compare saved values, without claiming heat, final rank, SB or PB.
"""
import csv,io,re
from datetime import date as calendar_date
from decimal import Decimal
from chunk_time_comparisons import clock_seconds,decimal_text


def read_identity(header,row,field):
    if len(header)!=len(row):raise ValueError('column alignment differs')
    value=dict(zip(header,row))
    name=value.get('名前') or (value.get('姓','').strip()+value.get('名','').strip())
    if not name or '\ufffd' in name:raise ValueError('missing or damaged identity')
    if field=='記録':
        distance=value.get('距離');date=value.get('日付');meet=value.get('大会名')
    else:
        match=re.fullmatch(r'(800m|1500m|3000m)記録',field)
        if not match:raise ValueError('unknown clock column')
        distance=match[1];date=value.get(distance+'日付');meet=value.get(distance+'大会')
    if not re.fullmatch(r'\d+(?:m|km)',distance or ''):raise ValueError('unknown event')
    if not re.fullmatch(r'20\d{2}[-/]\d{2}[-/]\d{2}',date or '') or not meet:raise ValueError('missing meet or date')
    gender=value.get('性別')
    if gender not in ('男子','女子'):raise ValueError('unknown gender')
    calendar_date.fromisoformat(date.replace('/','-'))
    time=value[field];seconds=clock_seconds(time)
    label=name+('（'+value['所属']+'）' if value.get('所属') else '')
    return {'name':name,'label':label,'date':date.replace('/','-'),'meet':meet,'gender':gender,'distance':distance,'time':time,'seconds':seconds}


def render_meet_comparison(header,rows,field):
    if len(rows)!=2:raise ValueError('two records required')
    a,b=[read_identity(header,r['cells'],field) for r in rows]
    if any(a[k]!=b[k] for k in ('date','meet','gender','distance')):raise ValueError('different meet/date/event/gender')
    if ''.join(a['name'].split())==''.join(b['name'].split()):raise ValueError('same athlete')
    gap=abs(a['seconds']-b['seconds']);win=rows[0]['row'] if a['seconds']<b['seconds'] else rows[1]['row'] if b['seconds']<a['seconds'] else None
    q=f'{a["date"]}の{a["meet"]}の保存記録で、{a["gender"]}{a["distance"]}の{a["label"]}と{b["label"]}は何秒差？'
    result='同タイムで差は0秒です。' if win is None else f'{a["label"] if win==rows[0]["row"] else b["label"]}が{decimal_text(gap)}秒速い掲載値です。'
    answer=f'{a["label"]}は{a["time"]}、{b["label"]}は{b["time"]}です。{result}'
    calc={'operation':'dated_meet_clock_difference','field':field,'rows':[r['row'] for r in rows],'gap_seconds':decimal_text(gap),'faster_row':win,'date':a['date'],'meet':a['meet'],'gender':a['gender'],'distance':a['distance']}
    return q,answer,calc


def validate_meet_comparison(entry,chunk,source_text):
    ev=entry['evidence']
    if len(ev)!=1 or ev[0].get('kind')!='csv-rows':raise ValueError('typed CSV evidence required')
    header=ev[0]['header'];rows=ev[0]['rows'];full=list(csv.reader(io.StringIO(source_text)));assigned={r['row']:r['cells'] for r in chunk['evidence']['units']}
    if full[0]!=header or header!=chunk['evidence']['header']:raise ValueError('header drift')
    if len(rows)!=2 or rows[0]['row']==rows[1]['row']:raise ValueError('distinct rows required')
    for r in rows:
        n=r['row']
        if type(n) is not int or not 0<n<len(full) or full[n]!=r['cells']:raise ValueError('source row drift')
        if assigned.get(n)!=r['cells']:raise ValueError('record outside assigned chunk')
    q,a,calc=render_meet_comparison(header,rows,entry['calculation']['field'])
    if entry['questions']!=[q] or entry['answer']!=a or entry['calculation']!=calc:raise ValueError('meet comparison drift')
    n=header.index(calc['field']);values=[]
    for r in rows:
        minutes,seconds=r['cells'][n].split(':');values.append(Decimal(minutes)*60+Decimal(seconds))
    if abs(values[0]-values[1])!=Decimal(calc['gap_seconds']):raise ValueError('independent clock difference fails')
