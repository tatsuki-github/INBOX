#!/usr/bin/env python3
"""Generate schema-reviewed SB snapshot comparison candidates.

Publication is separate and requires source, arithmetic, novelty and runtime
checks. Category and season values are not inferred from these snapshots.
"""
import sys,json,itertools,re,unicodedata
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'scripts'))
from chunk_time_comparisons import FIELD,render_comparison
chunks=[json.loads(l) for p in sorted((root/'out/qa-chunks').glob('chunks-*.jsonl')) for l in p.read_text().split('\n') if l]
selected=[c for c in chunks if c['evidence']['kind']=='csv' and c['source'].endswith('/SBデータベース.csv')]
def normalized(s):return ''.join(unicodedata.normalize('NFKC',s).split())
names={normalized(r['cells'][c['evidence']['header'].index('名前')]) for c in selected for r in c['evidence']['units'] if r['cells'][0]}
name_pattern=re.compile('|'.join(re.escape(n) for n in sorted(names,key=lambda x:(-len(x),x))))
existing=[e for e in json.loads((root/'backend/data/prepared-qa.json').read_text())['entries'] if not e['id'].startswith('fullchunkqa-')];blocked=set()
for e in existing:
 for q in e['questions']:
  text=normalized(q)
  if not re.search('差|比較|速|遅|何秒',text):continue
  found=set(name_pattern.findall(text))
  if len(found)<2:continue
  events=re.findall(r'\d+(?:km|m)',text) or ['*']
  for a,b in itertools.combinations(sorted(found),2):
   for event in events:blocked.add((a,b,event))
entries=[];unresolved=[];claimed=set()
for c in selected:
 header=c['evidence']['header'];candidates=[];local_keys=set()
 for field in header:
  if not FIELD.fullmatch(field):continue
  eligible=[r for r in c['evidence']['units'] if len(r['cells'])==len(header) and r['cells'][header.index(field)] and r['cells'][header.index('名前')]]
  for pair in itertools.combinations(eligible,2):
   a,b=sorted(normalized(r['cells'][header.index('名前')]) for r in pair);event=field.removesuffix('SB')
   if (a,b,event) in blocked or (a,b,'*') in blocked or (a,b,event) in claimed or (a,b,event) in local_keys:continue
   try:q,answer,calc=render_comparison(header,list(pair),field)
   except ValueError:continue
   local_keys.add((a,b,event));candidates.append((q,answer,calc,field,list(pair),(a,b,event)))
 if len(candidates)<3:unresolved.append(c['id']);continue
 for ordinal,(q,answer,calc,field,pair,key) in enumerate(candidates[:3],1):
  claimed.add(key)
  entries.append({'id':'fullchunkqa-'+c['id'].removeprefix('knowledge-')+'-'+str(ordinal),'chunk_id':c['id'],'questions':[q],'answer':answer,'sources':[c['source']],'source_sha256':c['source_sha256'],'evidence':[{'kind':'csv-rows','header':header,'rows':pair}],'calculation':calc,'review':{'method':'schema-reviewed-time-comparison','status':'schema-reviewed','scope':'Literal snapshot SB cells; category and current season not asserted; previously asked athlete/event comparisons excluded.'}})
p=root/'input/faq/full-knowledge-qa/reviewed-0003.json';p.write_text(json.dumps({'version':1,'entries':entries,'schema_review':{'identity_columns':['名前','所属','性別'],'clock_columns':'distance+SB','categorization_warning':'Age category values are not relied on; snapshot values are not current-year guarantees.'},'unresolved_chunks':unresolved},ensure_ascii=False,indent=2)+'\n');print('authored',len(entries),'completed SB chunks',len(entries)//3,'unresolved',len(unresolved),'blocked previous comparison intents',len(blocked))
