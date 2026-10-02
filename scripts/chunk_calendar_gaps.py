"""Elapsed days between literal public calendar dates, with typed provenance."""
import csv,io,json,re
from datetime import date,datetime
import yaml
from prepare_knowledge_qa_chunks import resolve_pointer
PUBLIC=re.compile(r'駅伝|陸上|記録会|マラソン|大会|選手権|練習|中体連|通信|修学旅行|入試|テスト|終業式|始業式|卒業式|運動会|体育大会|夏休み|冬休み|春休み|元日|成人の日|建国記念|天皇誕生日|春分|秋分|昭和の日|憲法記念|みどりの日|こどもの日|海の日|山の日|敬老の日|スポーツの日|文化の日|勤労感謝')
PATH=re.compile(r'^(?:calendar\.md|input/events\.20\d{2}\.yaml|out/20\d{2}/(?:calendar\.md|events\.json|source\.csv|notion\.csv|google\.csv))$')

def markdown_events(text):
    """Only complete detail blocks; no date/title joins across chunk boundaries."""
    units=[]
    for m in re.finditer(r'<details>\n.*?</details>',text,re.S):
        block=m[0];fields={}
        for key in ('件名','開始日','非公開'):
            values=re.findall(r'^- \*\*'+key+r'\*\*: (.+)$',block,re.M)
            if len(values)!=1:break
            fields[key]=values[0]
        else:
            if fields['非公開'] not in ('はい','いいえ'):continue
            unit={'quote':block,'value':{'title':fields['件名'],'date':fields['開始日'],'private':fields['非公開']=='はい'}}
            try:event(unit)
            except (ValueError,TypeError):continue
            units.append(unit)
    return units

def load_source(text):
    return json.loads(json.dumps(yaml.load(text,Loader=yaml.CSafeLoader),ensure_ascii=False,default=str))

def event(unit,header=None):
    if header is None:
        d=unit['value'];title=d['title'];raw=d['date'];private=d.get('private',False)
    else:
        if len(header)!=len(unit['cells']):raise ValueError('column alignment')
        d=dict(zip(header,unit['cells']))
        if 'title' in d:title,raw,private=d['title'],d['date'],d.get('private','false')
        elif 'Name' in d:title,raw,private=d['Name'],d['Date'],False
        elif 'Subject' in d:title,raw,private=d['Subject'],d['Start Date'],d.get('Private','false');raw=datetime.strptime(raw,'%m/%d/%Y').date().isoformat()
        else:raise ValueError('unknown calendar schema')
    if not isinstance(title,str) or not PUBLIC.search(title) or re.search(r'自分|診断|誕生日|個人|謝礼|口座|給与|資産',title) or str(private).lower()=='true':raise ValueError('not a public schedule selection')
    when=date.fromisoformat(raw)
    return title,when

def render_gap(units,header=None):
    if len(units)!=2:raise ValueError('two events required')
    a,b=[event(u,header) for u in units]
    if a[1]>=b[1]:raise ValueError('strictly ordered dates required')
    days=(b[1]-a[1]).days
    q=f'保存カレンダーで、{a[1].isoformat()}の「{a[0]}」から{b[1].isoformat()}の「{b[0]}」まで、予定日の日付差は何日？'
    answer=f'予定日の差は{days}日です。{a[1].isoformat()}から{b[1].isoformat()}までの日付差で、両端の日を含めた日数ではありません。保存された予定日を比較しており、実施済みかどうかを示すものではありません。'
    calc={'operation':'calendar_elapsed_days','from_date':a[1].isoformat(),'to_date':b[1].isoformat(),'days':days}
    return q,answer,calc

def validate_gap(entry,chunk,source_text):
    if len(entry['sources'])!=1 or not PATH.fullmatch(entry['sources'][0]):raise ValueError('unsupported calendar source')
    ev=entry['evidence']
    if len(ev)!=1:raise ValueError('one typed evidence block required')
    ev=ev[0];header=None
    if ev.get('kind')=='calendar-json-units':
        units=ev['units'];source=load_source(source_text);assigned={u['pointer']:u for u in chunk['evidence']['units']}
        for u in units:
            if assigned.get(u['pointer'])!=u:raise ValueError('outside assigned chunk')
            if u.get('string_span') or resolve_pointer(source,u['pointer'])!=u['value']:raise ValueError('source record changed')
    elif ev.get('kind')=='calendar-markdown-events':
        if chunk['evidence']['kind']!='text':raise ValueError('Markdown text chunk required')
        units=ev['units'];assigned=markdown_events(chunk['evidence']['text']);full=markdown_events(source_text)
        for u in units:
            if u not in assigned:raise ValueError('outside assigned chunk')
            if u not in full:raise ValueError('source detail block changed')
    elif ev.get('kind')=='csv-rows':
        header=ev['header'];units=ev['rows'];full=list(csv.reader(io.StringIO(source_text)))
        if not full or full[0]!=header or chunk['evidence']['header']!=header:raise ValueError('header changed')
        assigned={u['row']:u['cells'] for u in chunk['evidence']['units']}
        for u in units:
            n=u['row']
            if type(n)is not int or not 0<n<len(full) or full[n]!=u['cells']:raise ValueError('source row changed')
            if assigned.get(n)!=u['cells']:raise ValueError('outside assigned chunk')
    else:raise ValueError('typed calendar evidence required')
    q,a,calc=render_gap(units,header)
    if entry['questions']!=[q] or entry['answer']!=a or entry['calculation']!=calc:raise ValueError('calendar arithmetic or prose changed')
    # Independent ordinal arithmetic verifies leap years and year boundaries.
    start=datetime.strptime(calc['from_date'],'%Y-%m-%d');end=datetime.strptime(calc['to_date'],'%Y-%m-%d')
    if end.toordinal()-start.toordinal()!=calc['days']:raise ValueError('independent day difference changed')
