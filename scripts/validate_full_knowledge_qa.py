#!/usr/bin/env python3
"""Source-pinned coverage checks and publication for manually reviewed chunk QAs.

Partial coverage is reported honestly. Publication requires manual review plus
source/quote checks and the real TypeScript normalization/routing check.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[1]
BATCHES = ROOT / 'input/faq/full-knowledge-qa'
OUT = ROOT / 'out/qa-chunks'
FAQ = ROOT / 'input/faq/prepared-qa.v1.yaml'


def read_batches():
    paths = sorted(BATCHES.glob('reviewed-*.json'))
    carry = BATCHES / 'carry-forward.json'
    if carry.is_file(): paths.append(carry)
    return [e for p in paths for e in json.loads(p.read_text())['entries']]


def validate_entry(entry, chunk, root=ROOT):
    if entry.get('chunk_id') != chunk['id']:
        raise ValueError('wrong chunk identity')
    if entry.get('sources') != [chunk['source']]:
        raise ValueError('wrong source identity')
    if entry.get('source_sha256') != chunk['source_sha256']:
        raise ValueError('review source hash differs from chunk')
    path = root / chunk['source']
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry['source_sha256']:
        raise ValueError('source changed after review')
    review = entry.get('review', {})
    allowed_review = (review.get('method'), review.get('status')) in {
        ('manual-context-review', 'manual-context-reviewed'),
        ('schema-reviewed-time-comparison', 'schema-reviewed'),
    }
    if not allowed_review:
        raise ValueError('missing manual context review')
    if not entry.get('questions') or not entry.get('answer'):
        raise ValueError('missing question or answer')
    if not entry.get('evidence'):
        raise ValueError('missing evidence')
    if chunk['evidence']['kind'] == 'csv' and review.get('method') == 'schema-reviewed-time-comparison':
        from chunk_time_comparisons import validate_csv_comparison
        validate_csv_comparison(entry, chunk, path.read_text())
        return
    if chunk['evidence']['kind'] != 'text':
        raise ValueError('typed evidence validator required')
    text = chunk['evidence']['text']
    source = path.read_text()
    for evidence in entry['evidence']:
        quote = evidence.get('text')
        if evidence.get('kind') != 'quote' or not quote or quote not in text or quote not in source:
            raise ValueError('quote is not grounded in the assigned chunk')


def check_coverage(entries, chunks):
    ids = [e['id'] for e in entries]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate authored QA ids')
    by_id = {c['id']: c for c in chunks}
    counts = Counter()
    for e in entries:
        if e['chunk_id'] not in by_id:
            raise ValueError('unknown or outdated chunk: ' + e['chunk_id'])
        validate_entry(e, by_id[e['chunk_id']])
        counts[e['chunk_id']] += 1
    if any(n > 3 for n in counts.values()):
        raise ValueError('more than three assigned QAs in a chunk')
    pending = [{'chunk_id': c['id'], 'source': c['source'], 'index': c['index'],
                'remaining_qa': 3 - counts[c['id']]} for c in chunks if counts[c['id']] < 3]
    return {'status': 'complete' if not pending else 'in_progress',
            'total_chunks': len(chunks), 'complete_chunks': sum(n == 3 for n in counts.values()),
            'authored_qa': len(entries), 'carried_forward_qa': sum(bool(e.get('carry_forward')) for e in entries), 'required_qa': len(chunks) * 3,
            'remaining_qa': sum(p['remaining_qa'] for p in pending), 'pending': pending,
            'limitations': ['Literal grounding and manual review records are checked; not automatic semantic proof.']}


def publish(entries):
    # Check against both the current catalog and all new questions with the
    # application's actual normalization and matcher before changing the YAML.
    subprocess.run(['npx', 'tsx', 'scripts/check-reviewed-knowledge-qa.ts'], cwd=ROOT / 'backend', check=True)
    text = FAQ.read_text(); data = yaml.load(text, Loader=yaml.CSafeLoader)
    existing = {e['id']: e for e in data['entries']}
    added = []
    for e in entries:
        plain = {k: e[k] for k in ('id', 'questions', 'answer', 'sources')}
        plain['tags'] = ['knowledge-chunk', 'validated-time-comparison'] if e.get('calculation') else ['knowledge-chunk', 'manual-context-reviewed']
        if e['id'] in existing:
            if any(existing[e['id']].get(k) != e[k] for k in ('questions', 'answer', 'sources')):
                raise ValueError('published entry drift: ' + e['id'])
        else:
            added.append(plain)
    if added:
        text = re.sub(r'(?m)^total: \d+$', 'total: ' + str(len(existing) + len(added)), text, count=1)
        text = text.rstrip() + '\n' + ''.join(yaml.safe_dump([e], allow_unicode=True, sort_keys=False, width=1000) for e in added)
        FAQ.write_text(text)
        subprocess.run(['python3', 'scripts/sync_prepared_qa.py'], cwd=ROOT, check=True)
    subprocess.run(['npx', 'tsx', 'scripts/check-reviewed-knowledge-qa.ts', '--published'], cwd=ROOT / 'backend', check=True)
    print(json.dumps({'published_new_qa': len(added), 'total': len(existing) + len(added)}))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--publish-reviewed', action='store_true'); ap.add_argument('--require-complete', action='store_true'); args = ap.parse_args()
    chunks = [json.loads(line) for p in sorted(OUT.glob('chunks-*.jsonl')) for line in p.read_text().split('\n') if line]
    if not chunks:
        raise ValueError('missing chunk inventory')
    entries = read_batches(); report = check_coverage(entries, chunks)
    if args.publish_reviewed:
        publish(entries)
    (OUT / 'qa-progress.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'pending'}, ensure_ascii=False))
    if args.require_complete and report['status'] != 'complete':
        raise SystemExit('Full three-QA-per-chunk coverage is not complete.')

if __name__ == '__main__':
    main()
