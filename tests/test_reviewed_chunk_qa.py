from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from reviewed_chunk_qa import check_reviewed_entry

def fixture(tmp_path):
    (tmp_path / 'race.md').write_text('2026年男子1500m\n甲 4:30.13\n乙 4:34.21\n')
    reviewed = {'id':'chunkqa-fixture','questions':['2026年男子1500mの甲と乙の差は？'],
                'answer':'甲が4.08秒速い記録です。','sources':['race.md'],
                'review':{'method':'manual-context-review'},
                'evidence':[{'kind':'quote','text':'2026年男子1500m\n甲 4:30.13\n乙 4:34.21'}]}
    return reviewed

def test_changed_result_cannot_use_an_old_review(tmp_path):
    row=fixture(tmp_path)
    (tmp_path/'race.md').write_text('2025年女子1500m\n甲 4:30.13\n乙 4:34.21\n')
    assert 'reviewed_source_quote_drift' in check_reviewed_entry(row,row,tmp_path)

def test_answer_change_requires_review(tmp_path):
    row=fixture(tmp_path)
    changed={**row,'answer':'乙が4.08秒速い記録です。'}
    assert 'reviewed_answer_drift' in check_reviewed_entry(changed,row,tmp_path)

def test_self_reference_cannot_support_a_review(tmp_path):
    row=fixture(tmp_path);row['sources']=['prepared-qa.v1.yaml']
    assert 'invalid_review_source' in check_reviewed_entry(row,row,tmp_path)
