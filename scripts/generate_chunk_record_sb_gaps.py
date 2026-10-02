#!/usr/bin/env python3
import json,re,unicodedata
from pathlib import Path
from chunk_record_sb_gaps import SOURCES,render_gap
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'input/faq/full-knowledge-qa/reviewed-0012.json'
old=json.loads(OUT.read_text())['entries'] if OUT.is_file() else [];old_ids={e['id'] for e in old};old_by={}
for e in old:old_by.setdefault(e['chunk_id'],[]).append(e)
def norm(s):return ''.join(unicodedata.normalize('NFKC',s).split())
prior=[norm(q) for e in json.loads((ROOT/'backend/data/prepared-qa.json').read_text())['entries'] if e['id'] not in old_ids for q in e['questions'] if re.search('SB|ベスト',q,re.I) and re.search('差|違|速|遅',q)]
cs=[json.loads(l) for p in sorted((ROOT/'out/qa-chunks').glob('chunks-*.jsonl')) for l in p.read_text().split('\n') if l]
def key(u):
 r=u['value'];return (r['date'].replace('/','-'),r['gender'],r['distance'],norm(r['name']),r['time_text'],r['sb_text'])
claimed={key(e['evidence'][0]['unit']) for e in old};entries=[];pending=[]
for c in cs:
 if c['source'] not in SOURCES:continue
 if c['id'] in old_by:entries.extend(old_by[c['id']]);continue
 candidates=[];local=set()
 for unit in c['evidence']['units']:
  try:q,a,calc=render_gap(unit);identity=key(unit)
  except (ValueError,KeyError,TypeError):continue
  if identity in claimed or identity in local:continue
  day,g,d,name,t,sb=identity
  if any(day in p.replace('/','-') and name in p and d in p for p in prior):continue
  local.add(identity);candidates.append((q,a,calc,unit,identity))
 if len(candidates)<3:pending.append(c['id']);continue
 for i,(q,a,calc,unit,identity) in enumerate(candidates[:3],1):
  claimed.add(identity);entries.append({'id':'fullchunkqa-'+c['id'].removeprefix('knowledge-')+'-'+str(i),'chunk_id':c['id'],'questions':[q],'answer':a,'sources':[c['source']],'source_sha256':c['source_sha256'],'evidence':[{'kind':'json-unit','unit':unit}],'calculation':calc,'review':{'method':'schema-reviewed-record-vs-saved-sb','status':'schema-reviewed','scope':'Observed time versus the SB cell in the same dated snapshot row; no current/race-day PB or heat inference.'}})
OUT.write_text(json.dumps({'version':1,'entries':entries,'unresolved_chunks':pending},ensure_ascii=False,indent=2)+'\n');print('authored',len(entries),'unresolved',len(pending))
