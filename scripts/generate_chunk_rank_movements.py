#!/usr/bin/env python3
"""Prepare novel team passing-rank changes for full historical result chunks."""
import itertools,json,re,unicodedata
from pathlib import Path
from chunk_rank_movements import render_movement,TEAM_POINTER,expand_team_units
ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'input/faq/full-knowledge-qa/reviewed-0006.json'
old_entries=json.loads(OUTPUT.read_text())['entries'] if OUTPUT.is_file() else []
old_ids={e['id'] for e in old_entries}
old_by_chunk={}
for entry in old_entries:old_by_chunk.setdefault(entry['chunk_id'],[]).append(entry)
existing=[e for e in json.loads((ROOT/'backend/data/prepared-qa.json').read_text())['entries'] if e['id'] not in old_ids]
def norm(q):return ''.join(unicodedata.normalize('NFKC',q).split())
questions=[t for e in existing for q in e['questions'] if '順位' in (t:=norm(q)) and re.search('上が|上げ|下が|下げ|変わ|変化|推移',t)]
chunks=[json.loads(l) for p in sorted((ROOT/'out/qa-chunks').glob('chunks-*.jsonl')) for l in p.read_text().split('\n') if l]
sources={'input/aragyoku/men_full_2012_2025.json','input/aragyoku/women_full_2012_2025.json','input/aragyoku/women_top4_2012_2025.json','input/aragyoku/women_top6_2012_2025.json'}
claimed=set();entries=[];pending=[]
for entry in old_entries:
 parent=entry['evidence'][0]['unit'];unit=next(u for u in expand_team_units(parent) if u['pointer']==entry['calculation']['pointer']);calc=entry['calculation']
 claimed.add((unit['context']['year'],unit['context']['gender'],norm(unit['value']['team']),calc['from_leg'],calc['to_leg']))
for c in chunks:
 if c['source'] not in sources:continue
 if c['id'] in old_by_chunk:
  assert len(old_by_chunk[c['id']])==3
  entries.extend(old_by_chunk[c['id']]);continue
 candidates=[]
 for parent in c['evidence']['units']:
  for unit in expand_team_units(parent):
   for a,b in itertools.combinations([r['leg'] for r in unit['value'].get('legs',[])],2):
    try:q,answer,calc=render_movement(unit,a,b)
    except (ValueError,KeyError,TypeError):continue
    identity=(unit['context']['year'],unit['context']['gender'],norm(unit['value']['team']),a,b)
    if identity in claimed:continue
    # Exclude earlier requests for this same team's rank movement between legs.
    y,g,t,lo,hi=identity
    if any(str(y) in s and g in s and t in s and f'{lo}区' in s and f'{hi}区' in s and '順位' in s and re.search('上が|上げ|下が|下げ|変わ|変化|推移',s) for s in questions):continue
    candidates.append((q,answer,calc,parent,identity))
 if len(candidates)<3:pending.append(c['id']);continue
 for i,(q,answer,calc,unit,identity) in enumerate(candidates[:3],1):
  claimed.add(identity);entries.append({'id':'fullchunkqa-'+c['id'].removeprefix('knowledge-')+'-'+str(i),'chunk_id':c['id'],'questions':[q],'answer':answer,'sources':[c['source']],'source_sha256':c['source_sha256'],'evidence':[{'kind':'json-unit','unit':unit}],'calculation':calc,'review':{'method':'schema-reviewed-passing-rank-change','status':'schema-reviewed','scope':'Net change in printed passing ranks for one team, same year and gender; never split ranks or actual overtakes.'}})
OUTPUT.write_text(json.dumps({'version':1,'entries':entries,'unresolved_chunks':pending},ensure_ascii=False,indent=2)+'\n');print('authored',len(entries),'unresolved',len(pending))
