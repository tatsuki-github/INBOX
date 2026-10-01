"""Independent arithmetic fixtures for comparison answers and dirty source rows."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import generate_prepared_qa_edge_comparisons as g


def team(name, splits):
    acc = 0
    legs = []
    for i, split in enumerate(splits, 1):
        acc += g.seconds(split)
        legs.append({'leg': i, 'split': split, 'cumulative': f'{acc//60}:{acc%60:02}',
                     'name': name + '選手', 'status': 'ok'})
    return {'team': name, 'total': f'{acc//60}:{acc%60:02}', 'legs': legs}


def render(kind, a, b, leg=None):
    return g.make_entry(kind, 2025, '女子', a, b, leg, 'fixture.json', '/a', '/b')[0]['answer']


def test_split_gap_and_cumulative_gap_have_different_leaders():
    a = team('岱明', ['10:00', '6:00', '6:00'])
    b = team('玉名', ['9:00', '6:30', '6:30'])
    assert '岱明が玉名より30秒速いです' in render('split', a, b, 2)
    assert '玉名が岱明より30秒先行しています' in render('cumulative', a, b, 2)
    assert '同タイムです（差0秒）' in render('total', a, b)


def test_closing_change_survives_overtaking():
    a = team('岱明', ['10:00', '6:00', '5:00'])
    b = team('玉名', ['9:00', '6:30', '6:00'])
    assert '相対的に60秒取り戻しました' in render('closing', a, b, 2)
    assert '相対的に60秒失いました' in render('closing', b, a, 2)


@pytest.mark.parametrize('mark', ['—', '9:60', '10:00?', '', None, 'dns'])
def test_bad_times_are_excluded(mark):
    assert g.seconds(mark) is None


def test_cumulative_and_total_must_agree_with_every_split():
    a = team('岱明', ['10:00', '6:00', '6:00'])
    assert g.clean_team(a, 3)
    bad = copy.deepcopy(a)
    bad['legs'][1]['cumulative'] = '16:01'
    assert not g.clean_team(bad, 3)
    bad = copy.deepcopy(a)
    bad['total'] = '22:01'
    assert not g.clean_team(bad, 3)
    bad = copy.deepcopy(a)
    bad['legs'][1]['status'] = 'dnf'
    assert not g.clean_team(bad, 3)
    assert not g.clean_team(a, 5)


def test_uncertain_name_never_becomes_an_athlete_claim():
    a = team('岱明', ['10:00'])['legs'][0]
    a['name'] = 'unknown'
    assert not g.usable_leg(a)


def test_auditor_rejects_swapped_identity_or_wrong_difference():
    import audit_prepared_qa_facts as audit
    a, b = team('岱明', ['10:00']), team('玉名', ['10:30'])
    e, _ = g.make_entry('split', 2025, '女子', a, b, 1, 'fixture.json', '/a', '/b')
    bad = {**e, 'sources': [], 'answer': e['answer'].replace('30秒速い', '20秒速い')}
    assert 'source_projection_drift' in audit.check_entry(bad, e)['problems']


def test_comparison_cannot_fall_back_to_loose_time_checks():
    import audit_prepared_qa_facts as audit
    assert "missing_source_projection" in audit.check_entry(
        {"id": "edgecmp-2025-missing", "sources": [], "answer": "差は10秒です。"}, None
    )["problems"]
