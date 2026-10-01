"""Independent negative cases for coverage and chunk-local grounding."""
import hashlib
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import validate_full_knowledge_qa as v


def fixture(tmp_path):
    source = tmp_path / 'source.md'
    source.write_text('2026年男子1500m。甲4:30.13、乙4:34.21。\n別の節に女子800m。\n')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    chunk = {'id': 'knowledge-fixture', 'source': 'source.md', 'index': 0,
             'source_sha256': digest, 'evidence': {'kind': 'text', 'text': '2026年男子1500m。甲4:30.13、乙4:34.21。'}}
    entry = {'id': 'fullchunkqa-fixture-1', 'chunk_id': chunk['id'], 'sources': ['source.md'],
             'source_sha256': digest, 'questions': ['甲と乙の差は？'], 'answer': '甲が4.08秒速い。',
             'evidence': [{'kind': 'quote', 'text': chunk['evidence']['text']}],
             'review': {'method': 'manual-context-review', 'status': 'manual-context-reviewed'}}
    return chunk, entry


def test_quote_from_other_chunk_cannot_be_used(tmp_path):
    chunk, entry = fixture(tmp_path)
    entry['evidence'] = [{'kind': 'quote', 'text': '別の節に女子800m。'}]
    with pytest.raises(ValueError, match='assigned chunk'):
        v.validate_entry(entry, chunk, tmp_path)


def test_editing_a_source_invalidates_the_review(tmp_path):
    chunk, entry = fixture(tmp_path)
    (tmp_path / 'source.md').write_text('2025年女子1500m。甲4:30.13、乙4:34.21。')
    with pytest.raises(ValueError, match='source changed'):
        v.validate_entry(entry, chunk, tmp_path)


def test_two_answers_do_not_complete_a_chunk(tmp_path, monkeypatch):
    chunk, entry = fixture(tmp_path)
    original = v.validate_entry
    monkeypatch.setattr(v, 'validate_entry', lambda e, c: original(e, c, tmp_path))
    report = v.check_coverage([entry, {**entry, 'id': 'fullchunkqa-fixture-2'}], [chunk])
    assert report['status'] == 'in_progress'
    assert report['complete_chunks'] == 0
    assert report['remaining_qa'] == 1


def test_duplicate_qa_ids_cannot_fill_coverage(tmp_path):
    chunk, entry = fixture(tmp_path)
    with pytest.raises(ValueError, match='duplicate authored QA ids'):
        v.check_coverage([entry, entry, entry], [chunk])
