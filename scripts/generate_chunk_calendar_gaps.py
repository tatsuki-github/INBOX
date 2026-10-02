#!/usr/bin/env python3
"""Select new calendar date pairs conservatively; retain published assignments."""
import argparse,itertools,json,re
from collections import Counter
from pathlib import Path
from chunk_calendar_gaps import PATH,event,render_gap
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(ROOT/'input/faq/full-knowledge-qa/reviewed-0017.json'));args=ap.parse_args();out=Path(args.output)
 old=json.loads(out.read_text())['entries'] if out.is_file() else [];old_ids={e['id'] for e in old};entries=list(old);claimed={(e['calculation']['from_date'],e['calculation']['to_date']) for e in old};counts=Counter(e['chunk_id'] for e in old)
 for p in (ROOT/'input/faq/full-knowledge-qa').glob('*.json'):
  for e in json.loads(p.read_text()).get('entries',[]):
   if e['id'] not in old_ids:counts[e['chunk_id']]+=1
 # Existing questions with two dates and a day-gap intent block the pair,
 # regardless of copies, event title wording, or source format.
 for e in json.loads((ROOT/'backend/data/prepared-qa.json').read_text())['entries']:
  if e['id'] in old_ids:continue
  for q in e['questions']:
   if re.search('何日|日間|間隔|日付差',q):
    ds=re.findall(r'20\d{2}[-/]\d{2}[-/]\d{2}',q)
    if len(ds)==2:claimed.add(tuple(sorted(d.replace('/','-') for d in ds)))
 chunks=[json.loads(l) for p in sorted((ROOT/'out/qa-chunks').glob('chunks-*.jsonl')) for l in p.read_text().split('\n') if l];pending=[]
 for c in chunks:
  if not PATH.fullmatch(c['source']) or counts[c['id']]>=3:continue
  header=c['evidence'].get('header');valid=[]
  for u in c['evidence']['units']:
   try:label,day=event(u,header)
   except (ValueError,KeyError,TypeError):continue
   valid.append((day,label,u))
  valid.sort(key=lambda t:(t[0],t[1]));candidates=[];local=set()
  for a,b in itertools.combinations(valid,2):
   key=(a[0].isoformat(),b[0].isoformat())
   if a[0]>=b[0] or key in claimed or key in local:continue
   try:q,answer,calc=render_gap([a[2],b[2]],header)
   except ValueError:continue
   local.add(key);candidates.append((q,answer,calc,[a[2],b[2]],key))
  needed=3-counts[c['id']]
  if len(candidates)<needed:pending.append({'chunk_id':c['id'],'available':len(candidates)});continue
  for q,answer,calc,units,key in candidates[:needed]:
   i=counts[c['id']]+1;counts[c['id']]+=1;claimed.add(key)
   ev={'kind':'csv-rows','header':header,'rows':units} if header else {'kind':'calendar-json-units','units':units}
   entries.append({'id':'fullchunkqa-'+c['id'].removeprefix('knowledge-')+'-'+str(i),'chunk_id':c['id'],'questions':[q],'answer':answer,'sources':[c['source']],'source_sha256':c['source_sha256'],'evidence':[ev],'calculation':calc,'review':{'method':'schema-reviewed-calendar-gap','status':'schema-reviewed','scope':'Public event title and saved start date only; elapsed days, no inferred completion or private personal events.'}})
 out.write_text(json.dumps({'version':1,'entries':entries,'unresolved_chunks':pending},ensure_ascii=False,indent=2)+'\n');print('authored',len(entries),'unresolved',len(pending))
if __name__=='__main__':main()
