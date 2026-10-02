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
    if method not in ('manual-context-review', 'schema-reviewed-time-comparison', 'schema-reviewed-passing-rank-change', 'schema-reviewed-dated-meet-comparison', 'schema-reviewed-within-athlete-meet-change', 'schema-reviewed-record-vs-saved-sb', 'schema-reviewed-calendar-gap', 'schema-reviewed-track-coverage', 'schema-reviewed-prediction-columns'):
        problems.append('missing_context_review')
    sources = reviewed.get('sources') or []
    if len(sources) != 1 or 'prepared-qa' in sources[0]:
        return problems + ['invalid_review_source']
    path = root / sources[0]
    if not path.is_file():
        return problems + ['missing_review_source']
    text = path.read_text()
    evidence = reviewed.get('evidence') or []
    if method == 'schema-reviewed-prediction-columns':
        from chunk_prediction_columns import validate_columns
        try:
            ev = evidence[0]
            validate_columns(reviewed, {'evidence': {'header': ev['header'], 'units': ev['rows']}}, text)
        except (ValueError, KeyError, IndexError, TypeError):
            problems.append('reviewed_prediction_columns_drift')
        return problems
    if method == 'schema-reviewed-track-coverage':
        from chunk_track_coverage import validate_coverage
        try:
            validate_coverage(reviewed, {'evidence': {'units': [evidence[0]['unit']]}}, text)
        except (ValueError, KeyError, IndexError, TypeError):
            problems.append('reviewed_track_coverage_drift')
        return problems
    if method == 'schema-reviewed-calendar-gap':
        from chunk_calendar_gaps import validate_gap
        try:
            ev = evidence[0]
            chunk = {'evidence': {'units': ev.get('units', ev.get('rows')), 'header': ev.get('header')}}
            validate_gap(reviewed, chunk, text)
        except (ValueError, KeyError, IndexError, TypeError):
            problems.append('reviewed_calendar_date_or_arithmetic_drift')
        return problems
    if method == 'schema-reviewed-time-comparison':
        from chunk_time_comparisons import validate_csv_comparison
        try:
            ev = evidence[0]
            chunk = {'evidence': {'header': ev['header'], 'units': ev['rows']}}
            validate_csv_comparison(reviewed, chunk, text)
        except (ValueError, KeyError, IndexError):
            problems.append('reviewed_source_record_or_arithmetic_drift')
        return problems
    if method == 'schema-reviewed-within-athlete-meet-change':
        from chunk_meet_changes import validate_change
        try:
            ev = evidence[0]
            validate_change(reviewed, {'evidence': {'header': ev['header'], 'units': ev['rows']}}, text)
        except (ValueError, KeyError, IndexError):
            problems.append('reviewed_within_athlete_meet_change_drift')
        return problems
    if method == 'schema-reviewed-dated-meet-comparison':
        from chunk_meet_comparisons import validate_meet_comparison
        try:
            ev = evidence[0]
            validate_meet_comparison(reviewed, {'evidence': {'header': ev['header'], 'units': ev['rows']}}, text)
        except (ValueError, KeyError, IndexError):
            problems.append('reviewed_source_meet_or_arithmetic_drift')
        return problems
    if method == 'schema-reviewed-passing-rank-change':
        from chunk_rank_movements import validate_movement
        try:
            validate_movement(reviewed, {'evidence': {'units': [evidence[0]['unit']]}}, text)
        except (ValueError, KeyError, IndexError):
            problems.append('reviewed_source_rank_or_arithmetic_drift')
        return problems
    if method == 'schema-reviewed-record-vs-saved-sb':
        from chunk_record_sb_gaps import validate_gap
        try:
            validate_gap(reviewed, {'evidence': {'units': [evidence[0]['unit']]}}, text)
        except (ValueError, KeyError, IndexError):
            problems.append('reviewed_record_saved_sb_gap_drift')
        return problems
    if method == 'manual-context-review' and evidence and all(e.get('kind') == 'json-unit' for e in evidence):
        from manual_json_evidence import validate_manual_json
        try:
            validate_manual_json(reviewed, {'evidence': {'units': [e['unit'] for e in evidence]}}, text)
        except (ValueError, KeyError, IndexError):
            problems.append('reviewed_json_record_or_context_drift')
        return problems
    if not evidence or any(v.get('kind') != 'quote' or not v.get('text') or v['text'] not in text for v in evidence):
        problems.append('reviewed_source_quote_drift')
    return problems
