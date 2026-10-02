"""Count literal SB fields in saved women's ekiden/track joins, never missing careers."""
import re
from decimal import Decimal
from chunk_time_comparisons import clock_seconds
from manual_json_evidence import validate_manual_json
SOURCE='out/analysis/aragyoku_women_track_joined.json'
DISTANCES=('800m','1500m','3000m')

def render_coverage(unit,distance):
    if distance not in DISTANCES:raise ValueError('unsupported event')
    p=unit['pointer'];r=unit['value'];ctx=unit.get('context',{})
    if not isinstance(r,dict):raise ValueError('whole record required')
    year=ctx.get('year');school=r.get('school',ctx.get('school'))
    if type(year)is not int or not 2012<=year<=2025 or not school:raise ValueError('missing year/school')
    if re.fullmatch(r'/years/\d+/teams/\d+',p):
        athletes=r['athletes'];scope=f'{year}年の{school}の駅伝メンバー';team=True
    elif re.fullmatch(r'/years/\d+/teams/\d+/athletes/\d+',p):
        athletes=[r];scope=f'{year}年の{school}・{r["leg"]}区の{r["name"]}';team=False
    else:raise ValueError('whole team or athlete required')
    names=[a.get('name') for a in athletes]
    legs=[a.get('leg') for a in athletes]
    if any(not isinstance(n,str) or not n for n in names) or len(names)!=len(set(names)) or len(legs)!=len(set(legs)) or any(type(n)is not int or not 1<=n<=5 for n in legs):raise ValueError('ambiguous roster')
    listed=[]
    for a in athletes:
        sb=a.get('track_events',{}).get(distance,{}).get('sb')
        if sb is None:continue
        if not isinstance(sb,dict) or not sb.get('mark') or sb.get('season')!=str(year):raise ValueError('bad SB identity or year')
        if clock_seconds(sb['mark'])!=Decimal(str(sb['seconds'])):raise ValueError('stored SB seconds mismatch')
        if not a.get('name') or type(a.get('leg'))is not int:raise ValueError('damaged athlete identity')
        listed.append({'name':a['name'],'leg':a['leg'],'mark':sb['mark']})
    if team:
        q=f'女子駅伝トラック突合の保存資料で、{scope}に{distance}のトラックSBが載っているのは何人？'
        answer=f'{len(listed)}人です。'
    else:
        q=f'女子駅伝トラック突合の保存資料で、{scope}には{distance}のSB欄にどの記録がある？'
        answer='掲載SBは'+listed[0]['mark']+'です。' if listed else 'この保存資料のSB欄には掲載されていません。'
    if team and listed:answer+='掲載は'+ '、'.join(f'{a["name"]}（{a["leg"]}区）{a["mark"]}' for a in listed)+'です。'
    answer+='保存資料の掲載有無の確認で、未掲載でもその選手に競技記録がないとは言えません。駅伝当日時点や現在のSBを示すものでもありません。'
    calc={'operation':'saved_track_sb_coverage','pointer':p,'distance':distance,'listed_count':len(listed),'listed':listed}
    identity=(year,school,distance,'team' if team else (r['name'],r['leg']))
    return q,answer,calc,identity

def validate_coverage(entry,chunk,source_text):
    import json
    if entry['sources']!=[SOURCE] or '女子' not in json.loads(source_text)['meta']['title']:raise ValueError('unsupported source/gender')
    ev=entry.get('evidence',[])
    if len(ev)!=1 or ev[0].get('kind')!='json-unit':raise ValueError('one whole source unit required')
    validate_manual_json(entry,chunk,source_text)
    q,a,calc,_=render_coverage(ev[0]['unit'],entry['calculation']['distance'])
    if entry['questions']!=[q] or entry['answer']!=a or entry['calculation']!=calc:raise ValueError('coverage or prose drift')
    # Independent field-presence count, rather than trusting cached summary stats.
    r=ev[0]['unit']['value'];rows=r['athletes'] if 'athletes' in r else [r];d=calc['distance']
    independent=sum(isinstance(row.get('track_events',{}).get(d,{}).get('sb'),dict) for row in rows)
    if independent!=calc['listed_count']:raise ValueError('independent SB presence mismatch')
