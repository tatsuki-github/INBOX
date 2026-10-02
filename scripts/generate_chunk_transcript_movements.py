#!/usr/bin/env python3
"""New net passing-rank changes from explicitly dated historical transcripts.

Typed validators independently check parent records, year/gender context and
arithmetic. Existing year/team/leg-pair intents block repeats across formats.
"""
import argparse,itertools,json,re,unicodedata
from collections import Counter
from pathlib import Path
from chunk_rank_movements import expand_team_units,render_movement
from validate_full_knowledge_qa import read_batches,validate_entry
ROOT=Path(__file__).resolve().parents[1]
PATH=re.compile(r'^input/aragyoku/transcripts/(20\d{2})-(男子|女子)\.json$')

def norm(s):return ''.join(unicodedata.normalize('NFKC',s).split())

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args();out=Path(args.output)
 if out.exists():raise SystemExit('Refuse to overwrite a reviewed batch; select a new output.')
 reviewed=read_batches();counts=Counter(e['chunk_id'] for e in reviewed);claimed=set()
 for e in reviewed:
  if e.get('calculation',{}).get('operation')!='passing_rank_change':continue
  calc=e['calculation'];parent=e['evidence'][0]['unit'];u=next(u for u in expand_team_units(parent) if u['pointer']==calc['pointer'])
  claimed.add((u['context']['year'],u['context']['gender'],norm(u['value']['team']),calc['from_leg'],calc['to_leg']))
 existing=json.loads((ROOT/'backend/data/prepared-qa.json').read_text())['entries'];questions=[]
 for e in existing:
  for q in e['questions']:
   s=norm(q)
   if '順位' in s and re.search('上が|上げ|下が|下げ|変わ|変化|推移',s):questions.append(s)
 entries=[];unresolved=[]
 cs=[json.loads(l) for p in sorted((ROOT/'out/qa-chunks').glob('chunks-*.jsonl')) for l in p.read_text().split('\n') if l]
 for c in cs:
  m=PATH.fullmatch(c['source'])
  if not m or counts[c['id']]>=3:continue
  candidates=[];local=set()
  for parent in c['evidence']['units']:
   for u in expand_team_units(parent):
    if u['context'].get('year')!=int(m[1]) or u['context'].get('gender')!=m[2]:continue
    for lo,hi in itertools.combinations(sorted(r['leg'] for r in u['value'].get('legs',[])),2):
     try:q,a,calc=render_movement(u,lo,hi)
     except (ValueError,KeyError,TypeError):continue
     key=(int(m[1]),m[2],norm(u['value']['team']),lo,hi)
     if key in claimed or key in local:continue
     if any(str(key[0]) in s and key[1] in s and key[2] in s and f'{lo}区' in s and f'{hi}区' in s for s in questions):continue
     local.add(key);candidates.append((q,a,calc,parent,key))
  need=3-counts[c['id']]
  if len(candidates)<need:unresolved.append({'chunk_id':c['id'],'available':len(candidates)});continue
  for q,a,calc,parent,key in candidates[:need]:
   ordinal=counts[c['id']]+1
   e={'id':'fullchunkqa-'+c['id'].removeprefix('knowledge-')+f'-{ordinal}','chunk_id':c['id'],'questions':[q],'answer':a,'sources':[c['source']],'source_sha256':c['source_sha256'],'evidence':[{'kind':'json-unit','unit':parent}],'calculation':calc,'review':{'method':'schema-reviewed-passing-rank-change','status':'schema-reviewed','scope':'Same team, printed year and gender; net change of valid passing ranks only, no split-rank substitution or inferred overtakes.'}}
   validate_entry(e,c);claimed.add(key);counts[c['id']]+=1;entries.append(e)
 out.write_text(json.dumps({'version':1,'entries':entries,'unresolved_chunks':unresolved},ensure_ascii=False,indent=2)+'\n');print('Revalidated new transcript movements:',len(entries),'unresolved chunks:',len(unresolved))
if __name__=='__main__':main()
