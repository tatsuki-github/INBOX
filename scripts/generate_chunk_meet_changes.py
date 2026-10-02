#!/usr/bin/env python3
import json,re,unicodedata
from pathlib import Path
from chunk_meet_changes import SOURCE,render_change
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'input/faq/full-knowledge-qa/reviewed-0011.json'
old_ids={e['id'] for e in json.loads(OUT.read_text())['entries']} if OUT.is_file() else set()
def norm(s):return ''.join(unicodedata.normalize('NFKC',s).split())
prior=[norm(q) for e in json.loads((ROOT/'backend/data/prepared-qa.json').read_text())['entries'] if e['id'] not in old_ids for q in e['questions'] if '通信' in q and '選手権' in q and re.search('差|変|速|遅',q)]
cs=[json.loads(l) for p in sorted((ROOT/'out/qa-chunks').glob('chunks-*.jsonl')) for l in p.read_text().split('\n') if l];entries=[];claimed=set();pending=[]
for c in cs:
 if c['source']!=SOURCE:continue
 h=c['evidence']['header'];candidates=[]
 for r in c['evidence']['units']:
  d=dict(zip(h,r['cells']));name=norm(d.get('姓','')+d.get('名',''))
  if name in claimed or any(name in q and '2025' in q and '800' in q for q in prior):continue
  try:q,a,calc=render_change(h,r)
  except (ValueError,KeyError):continue
  candidates.append((q,a,calc,r,name))
 if len(candidates)<3:pending.append(c['id']);continue
 for i,(q,a,calc,r,name) in enumerate(candidates[:3],1):
  claimed.add(name);entries.append({'id':'fullchunkqa-'+c['id'].removeprefix('knowledge-')+'-'+str(i),'chunk_id':c['id'],'questions':[q],'answer':a,'sources':[SOURCE],'source_sha256':c['source_sha256'],'evidence':[{'kind':'csv-rows','header':h,'rows':[r]}],'calculation':calc,'review':{'method':'schema-reviewed-within-athlete-meet-change','status':'schema-reviewed','scope':'Literal 2025 comparison-table cells; signed clock change checked against the stored difference, without gender or rank inference.'}})
OUT.write_text(json.dumps({'version':1,'entries':entries,'unresolved_chunks':pending},ensure_ascii=False,indent=2)+'\n');print('authored',len(entries),'unresolved',len(pending))
