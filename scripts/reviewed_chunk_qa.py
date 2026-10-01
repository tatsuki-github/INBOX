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
    rows = list(data['entries'])
    for batch in sorted((ROOT / 'input/faq/full-knowledge-qa').glob('reviewed-*.json')):
        rows.extend(json.loads(batch.read_text())['entries'])
    if len({e['id'] for e in rows}) != len(rows):
        raise ValueError('duplicate reviewed QA identity')
    return {e['id']: e for e in rows}

def check_reviewed_entry(entry, reviewed, root=ROOT):
    problems = []
    if not reviewed:
        return ['missing_manual_review']
    for field in ('questions', 'answer', 'sources'):
        if entry.get(field) != reviewed.get(field):
            problems.append('reviewed_' + field + '_drift')
    method = reviewed.get('review', {}).get('method')
    if method not in ('manual-context-review', 'schema-reviewed-time-comparison'):
        problems.append('missing_context_review')
    sources = reviewed.get('sources') or []
    if len(sources) != 1 or 'prepared-qa' in sources[0]:
        return problems + ['invalid_review_source']
    path = root / sources[0]
    if not path.is_file():
        return problems + ['missing_review_source']
    text = path.read_text()
    evidence = reviewed.get('evidence') or []
    if method == 'schema-reviewed-time-comparison':
        from chunk_time_comparisons import validate_csv_comparison
        try:
            ev = evidence[0]
            chunk = {'evidence': {'header': ev['header'], 'units': ev['rows']}}
            validate_csv_comparison(reviewed, chunk, text)
        except (ValueError, KeyError, IndexError):
            problems.append('reviewed_source_record_or_arithmetic_drift')
        return problems
    if not evidence or any(v.get('kind') != 'quote' or not v.get('text') or v['text'] not in text for v in evidence):
        problems.append('reviewed_source_quote_drift')
    return problems
