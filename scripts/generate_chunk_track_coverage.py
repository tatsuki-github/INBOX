#!/usr/bin/env python3
"""New source-specific coverage questions; preserve reviewed assignments."""
import argparse,json,re,unicodedata
from collections import Counter
from pathlib import Path
from chunk_track_coverage import SOURCE,DISTANCES,render_coverage
ROOT=Path(__file__).resolve().parents[1]
def norm(s):return ''.join(unicodedata.normalize('NFKC',s).split())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(ROOT/'input/faq/full-knowledge-qa/reviewed-0022.json'));args=ap.parse_args();out=Path(args.output)
 old=json.loads(out.read_text())['entries'] if out.is_file() else [];old_ids={e['id'] for e in old};entries=list(old);counts=Counter(e['chunk_id'] for e in old);claimed=set()
 for e in old:
  _,_,_,key=render_coverage(e['evidence'][0]['unit'],e['calculation']['distance']);claimed.add(key)
 for p in (ROOT/'input/faq/full-knowledge-qa').glob('*.json'):
  for e in json.loads(p.read_text()).get('entries',[]):
   if e['id'] not in old_ids:counts[e['chunk_id']]+=1
 prior=[norm(q) for e in json.loads((ROOT/'backend/data/prepared-qa.json').read_text())['entries'] if e['id'] not in old_ids for q in e['questions']]
 cs=[json.loads(l) for p in sorted((ROOT/'out/qa-chunks').glob('chunks-*.jsonl')) for l in p.read_text().split('\n') if l];pending=[]
 for c in cs:
  if c['source']!=SOURCE or counts[c['id']]>=3:continue
  selected=[];local=set()
  for u in c['evidence']['units']:
   for distance in DISTANCES:
    try:q,a,calc,key=render_coverage(u,distance)
    except (ValueError,KeyError,TypeError):continue
    if key in claimed or key in local:continue
    year,school,_,who=key
    if who=='team':
     duplicate=any(str(year) in p and norm(school) in p and distance in p and '女子' in p and re.search('何人|人数|掲載.*SB|SB.*掲載',p) for p in prior)
    else:
     duplicate=any(str(year) in p and norm(who[0]) in p and distance in p and 'SB' in p for p in prior)
    if duplicate:continue
    local.add(key);selected.append((q,a,calc,key,u))
  needed=3-counts[c['id']]
  if len(selected)<needed:pending.append({'chunk_id':c['id'],'available':len(selected)});continue
  for q,a,calc,key,u in selected[:needed]:
   i=counts[c['id']]+1;counts[c['id']]+=1;claimed.add(key)
   entries.append({'id':'fullchunkqa-'+c['id'].removeprefix('knowledge-')+'-'+str(i),'chunk_id':c['id'],'questions':[q],'answer':a,'sources':[SOURCE],'source_sha256':c['source_sha256'],'evidence':[{'kind':'json-unit','unit':u}],'calculation':calc,'review':{'method':'schema-reviewed-track-coverage','status':'schema-reviewed','scope':'Exact saved SB presence and literal marks within a complete team or athlete; unavailable fields do not prove absent career records; no race-day or current SB inference.'}})
 out.write_text(json.dumps({'version':1,'entries':entries,'unresolved_chunks':pending},ensure_ascii=False,indent=2)+'\n');print('authored',len(entries),'unresolved',len(pending))
if __name__=='__main__':main()
