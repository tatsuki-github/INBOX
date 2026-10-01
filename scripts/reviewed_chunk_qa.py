"""Validate the manually reviewed checkpoint against its exact source quotes.

The recorded prose/arithmetic review is not an automatic semantic proof.
"""
import json
from functools import lru_cache
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'input/faq/knowledge-chunk-reviewed.json'

@lru_cache(maxsize=None)
def reviewed_entries():
    data = json.loads(MANIFEST.read_text())
    return {e['id']: e for e in data['entries']}

def check_reviewed_entry(entry, reviewed, root=ROOT):
    problems = []
    if not reviewed:
        return ['missing_manual_review']
    for field in ('questions', 'answer', 'sources'):
        if entry.get(field) != reviewed.get(field):
            problems.append('reviewed_' + field + '_drift')
    if reviewed.get('review', {}).get('method') != 'manual-context-review':
        problems.append('missing_context_review')
    sources = reviewed.get('sources') or []
    if len(sources) != 1 or 'prepared-qa' in sources[0]:
        return problems + ['invalid_review_source']
    path = root / sources[0]
    if not path.is_file():
        return problems + ['missing_review_source']
    text = path.read_text()
    evidence = reviewed.get('evidence') or []
    if not evidence or any(v.get('kind') != 'quote' or not v.get('text') or v['text'] not in text for v in evidence):
        problems.append('reviewed_source_quote_drift')
    return problems
