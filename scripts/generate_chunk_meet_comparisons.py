#!/usr/bin/env python3
"""Prepare comparisons with literal date, meet, distance and athlete identities."""
import itertools,json,re,unicodedata
from pathlib import Path
from chunk_meet_comparisons import read_identity,render_meet_comparison
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'input/faq/full-knowledge-qa/reviewed-0007.json'
old_ids={e['id'] for e in json.loads(OUT.read_text())['entries']} if OUT.is_file() else set()
chunks=[json.loads(l) for p in sorted((ROOT/'out/qa-chunks').glob('chunks-*.jsonl')) for l in p.read_text().split('\n') if l]
selected=[c for c in chunks if c['evidence']['kind']=='csv' and c['source'].startswith('input/external/drive/shared/記録データベース/') and any(f in c['evidence']['header'] for f in ('800m記録','記録')) and '選手権と通信' not in c['source']]
def norm(s):return ''.join(unicodedata.normalize('NFKC',s).split())
names={norm(dict(zip(c['evidence']['header'],r['cells'])).get('名前') or (dict(zip(c['evidence']['header'],r['cells'])).get('姓','')+dict(zip(c['evidence']['header'],r['cells'])).get('名',''))) for c in selected for r in c['evidence']['units']};names.discard('')
pattern=re.compile('|'.join(re.escape(n) for n in sorted(names,key=lambda n:(-len(n),n))))
blocked=set()
for e in json.loads((ROOT/'backend/data/prepared-qa.json').read_text())['entries']:
 if e['id'] in old_ids:continue
 for q in e['questions']:
  q=norm(q)
  if not re.search('差|比較|速|遅|何秒',q):continue
  years=re.findall(r'20\d{2}',q);events=re.findall(r'\d+(?:km|m)',q);found=sorted(set(pattern.findall(q)))
  for a,b in itertools.combinations(found,2):
   for y in years:
    for distance in events:blocked.add((y,distance,a,b))
claimed=set();entries=[];pending=[]
for c in selected:
 h=c['evidence']['header'];candidates=[];local=set()
 for field in h:
  if field!='記録' and not re.fullmatch('(800m|1500m|3000m)記録',field):continue
  eligible=[]
  for r in c['evidence']['units']:
   try:identity=read_identity(h,r['cells'],field)
   except (ValueError,KeyError):continue
   eligible.append((r,identity))
  for (a,ia),(b,ib) in itertools.combinations(eligible,2):
   pair=sorted((norm(ia['name']),norm(ib['name'])));key=(ia['date'],ia['meet'],ia['gender'],ia['distance'],*pair)
   if key in claimed or key in local or (ia['date'][:4],ia['distance'],*pair) in blocked:continue
   try:q,answer,calc=render_meet_comparison(h,[a,b],field)
   except ValueError:continue
   local.add(key);candidates.append((q,answer,calc,[a,b],key))
 if len(candidates)<3:pending.append(c['id']);continue
 for i,(q,answer,calc,pair,key) in enumerate(candidates[:3],1):
  claimed.add(key);entries.append({'id':'fullchunkqa-'+c['id'].removeprefix('knowledge-')+'-'+str(i),'chunk_id':c['id'],'questions':[q],'answer':answer,'sources':[c['source']],'source_sha256':c['source_sha256'],'evidence':[{'kind':'csv-rows','header':h,'rows':pair}],'calculation':calc,'review':{'method':'schema-reviewed-dated-meet-comparison','status':'schema-reviewed','scope':'Same literal meet, date, distance and gender; recorded times only, no heat or place inference.'}})
OUT.write_text(json.dumps({'version':1,'entries':entries,'unresolved_chunks':pending},ensure_ascii=False,indent=2)+'\n');print('authored',len(entries),'completed',len(entries)//3,'unresolved',len(pending))
