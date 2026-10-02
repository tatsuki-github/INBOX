#!/usr/bin/env python3
import argparse,json,unicodedata
from collections import Counter
from pathlib import Path
from chunk_prediction_columns import SOURCE,PAIRS,render_columns
ROOT=Path(__file__).resolve().parents[1]
def norm(s):return ''.join(unicodedata.normalize('NFKC',s).split())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(ROOT/'input/faq/full-knowledge-qa/reviewed-0024.json'));args=ap.parse_args();out=Path(args.output)
 old=json.loads(out.read_text())['entries'] if out.is_file() else [];old_ids={e['id'] for e in old};entries=list(old);counts=Counter(e['chunk_id'] for e in old);claimed={render_columns(e['evidence'][0]['header'],e['evidence'][0]['rows'][0],e['calculation']['columns'])[3] for e in old}
 for p in (ROOT/'input/faq/full-knowledge-qa').glob('*.json'):
  for e in json.loads(p.read_text()).get('entries',[]):
   if e['id'] not in old_ids:counts[e['chunk_id']]+=1
 prior=[norm(q) for e in json.loads((ROOT/'backend/data/prepared-qa.json').read_text())['entries'] if e['id'] not in old_ids for q in e['questions'] if '予想' in q and '差' in q or '予想' in q and '違' in q];pending=[]
 cs=[json.loads(l) for p in sorted((ROOT/'out/qa-chunks').glob('chunks-*.jsonl')) for l in p.read_text().split('\n') if l]
 for c in cs:
  if c['source']!=SOURCE or counts[c['id']]>=3:continue
  selected=[];local=set();h=c['evidence']['header']
  for r in c['evidence']['units']:
   for cols in PAIRS:
    try:q,a,calc,key=render_columns(h,r,cols)
    except (ValueError,KeyError):continue
    gender,school,_=key
    if key in claimed or key in local or any('2025' in p and norm(school) in p and gender in p and all(norm(col) in p for col in cols) for p in prior):continue
    local.add(key);selected.append((q,a,calc,key,r))
  needed=3-counts[c['id']]
  if len(selected)<needed:pending.append({'chunk_id':c['id'],'available':len(selected)});continue
  for q,a,calc,key,r in selected[:needed]:
   i=counts[c['id']]+1;counts[c['id']]+=1;claimed.add(key)
   entries.append({'id':'fullchunkqa-'+c['id'].removeprefix('knowledge-')+'-'+str(i),'chunk_id':c['id'],'questions':[q],'answer':a,'sources':[SOURCE],'source_sha256':c['source_sha256'],'evidence':[{'kind':'csv-rows','header':h,'rows':[r]}],'calculation':calc,'review':{'method':'schema-reviewed-prediction-columns','status':'schema-reviewed','scope':'Literal same-row 2025 prediction columns with saved population labels; exact decimal clock difference, no model recomputation or actual race outcome inference.'}})
 out.write_text(json.dumps({'version':1,'entries':entries,'unresolved_chunks':pending},ensure_ascii=False,indent=2)+'\n');print('authored',len(entries),'unresolved',len(pending))
if __name__=='__main__':main()
