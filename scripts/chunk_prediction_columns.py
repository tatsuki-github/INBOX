"""Compare explicit saved prediction columns, without recomputing or endorsing a model."""
import csv,io,re
from decimal import Decimal
from chunk_time_comparisons import clock_seconds,decimal_text
SOURCE='input/external/drive/shared/記録データベース/2025年度/3000m予想タイムランキング.csv'
COLUMNS=('上位3000m予想平均タイム','上位3000m予想最速タイム','全員3000m予想平均タイム','全員3000m予想最速タイム')
PAIRS=((COLUMNS[0],COLUMNS[2]),(COLUMNS[1],COLUMNS[3]),(COLUMNS[0],COLUMNS[1]))

def saved_seconds(cell):
    m=re.fullmatch(r'(\d+:\d{2}(?:\.\d+)?)[（(]([1-9]\d*)人[）)]',cell)
    if not m:raise ValueError('prediction clock and population required')
    return clock_seconds(m[1]),m[1],int(m[2])

def render_columns(header,row,columns):
    if tuple(columns) not in PAIRS:raise ValueError('unsupported column comparison')
    if len(header)!=len(row['cells']):raise ValueError('column alignment')
    r=dict(zip(header,row['cells']));school=r['所属'];gender=r['性別']
    if not school or gender not in ('男子','女子') or r['種目']!='3000m予想':raise ValueError('prediction identity required')
    ca,cb=columns;a,at,an=saved_seconds(r[ca]);b,bt,bn=saved_seconds(r[cb]);delta=b-a
    q=f'2025年度3000m予想ランキングの{gender}・{school}で、「{ca}」欄と「{cb}」欄の保存値は何秒違う？'
    change=f'「{cb}」欄の方が{decimal_text(delta)}秒遅い予想値です。' if delta>0 else f'「{cb}」欄の方が{decimal_text(-delta)}秒速い予想値です。' if delta<0 else '掲載タイムは同じで差は0秒です。'
    answer=f'「{ca}」欄は{r[ca]}、「{cb}」欄は{r[cb]}です。{change}保存された予想欄の比較です。'
    calc={'operation':'saved_prediction_column_clock_gap','row':row['row'],'columns':list(columns),'delta_seconds':decimal_text(delta),'populations':[an,bn]}
    identity=(gender,school,tuple(columns))
    return q,answer,calc,identity

def validate_columns(entry,chunk,source_text):
    if entry['sources']!=[SOURCE]:raise ValueError('unsupported prediction source/year')
    ev=entry.get('evidence',[])
    if len(ev)!=1 or ev[0].get('kind')!='csv-rows' or len(ev[0]['rows'])!=1:raise ValueError('one source row required')
    h=ev[0]['header'];r=ev[0]['rows'][0];full=list(csv.reader(io.StringIO(source_text)));n=r['row']
    if h!=full[0] or h!=chunk['evidence']['header']:raise ValueError('header drift')
    if type(n)is not int or not 0<n<len(full) or full[n]!=r['cells']:raise ValueError('source row drift')
    if {u['row']:u['cells'] for u in chunk['evidence']['units']}.get(n)!=r['cells']:raise ValueError('outside assigned chunk')
    q,a,calc,_=render_columns(h,r,entry['calculation']['columns'])
    if entry['questions']!=[q] or entry['answer']!=a or entry['calculation']!=calc:raise ValueError('prediction column arithmetic drift')
    def independent(raw):
        clock=raw.split('（')[0].split('(')[0];minutes,seconds=clock.split(':');return Decimal(minutes)*60+Decimal(seconds)
    values=dict(zip(h,r['cells']));left,right=calc['columns']
    if independent(values[right])-independent(values[left])!=Decimal(calc['delta_seconds']):raise ValueError('independent gap drift')
