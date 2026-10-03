"""Regressions against independent facts and explicit conflicting fixtures."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import prepared_qa_source_checks as checks


def test_career_same_clock_does_not_validate_wrong_school_or_count():
    expected = '選手Aの荒玉駅伝出走歴は1回です。2022年男子・岱明2区（9:44）／総合8位。'
    wrong = '選手Aの荒玉駅伝出走歴は2回です。2022年男子・有明2区（9:44）／総合8位。'
    assert set(checks.check_career(wrong, expected)) == {'career_identity_or_count_mismatch', 'career_race_identity_mismatch'}
    assert checks.check_career(expected, expected) == []


def test_saved_distance_is_not_replaced_by_lap_calculation():
    practice = {'items': [{'type': 'jog', 'laps': 10, 'distance_km': 4.95, 'pace': '4:30/km'}]}
    original = copy.deepcopy(practice)
    answer = checks.render_practice(practice)
    assert '4.95km' in answer and '10周' in answer and '4:30/km' in answer
    assert '5.60km' not in answer
    assert practice == original


def test_km_only_intervals_and_legacy_labels_keep_saved_facts():
    answer = checks.render_practice({'items': [
        {'type': 'interval', 'distance_km': 2.5, 'reps': 2},
        {'type': 'set', 'label': '600m +300m k/3:00', 'segments': [{'distance_m': 100}]}]})
    assert '2500m×2' in answer
    assert '600m +300m k/3:00' in answer
    assert '100m' not in answer


def test_rest_day_does_not_borrow_evening_session():
    fresh = checks.calendar_projections()['cal-2026-20260826-いだてん岱明朝練休み']
    assert '朝練は休みです' in fresh['answer']
    assert 'ジョグ' not in fresh['answer']
    entry = {'questions': ['いだてん岱明朝練のメニューは？', '2026-08-26の朝練は？']}
    assert checks.dated_practice_questions(entry, fresh) == ['2026-08-26の朝練は？']


def test_changed_grade_and_board_runner_fail_even_when_clock_matches():
    entry = {'id': 'edge5k-splitrank-2025-男子-leg6-r2', 'answer': '2位 本戸優貴（2年）9:44'}
    assert checks.check_source_semantics(entry, {'answer': '2位 本戸優貴（3年）9:44'})
    entry = {'id': 'aragyoku-2022-女子-leg5-board', 'answer': '1位 高田麻由（11:28）'}
    assert checks.check_source_semantics(entry, {'answer': '1位 高田麻那（11:28）'})


def test_full_list_answers_include_tail_and_missing_year():
    entries = checks.complete_list_projections()
    assert '20位 内野翼' in entries['sb-1500-top20']['answer']
    assert '4区 内田千惺' in entries['aragyoku-2025-women-leg-awards']['answer']
    assert '5区 大木莉子' in entries['aragyoku-2025-women-leg-awards']['answer']
    assert '2012年男子: 玉名' in entries['aragyoku-winners-all']['answer']
    assert '2014年女子の優勝校は未収録' in entries['aragyoku-winners-all']['answer']


def test_nagomi_parser_skips_leg_only_continuation_rows(tmp_path):
    import generate_prepared_qa_nagomi_team_results as nagomi
    path = tmp_path / 'results.md'
    path.write_text('| 1 | 21 | チームA | 38:33 | 選手A1 (5)9:33 | 選手B3 (3)9:19 | 選手C3 (7)10:01 | 選手D3 (3)9:40 |\n'
                    '| 4区 |  |  |  |  |  |  |  |\n')
    rows = nagomi.parse_results_md(path)
    assert len(rows) == 1
    assert (rows[0]['rank'], rows[0]['team'], rows[0]['total']) == ('1', 'チームA', '38:33')
    assert rows[0]['legs'][0] == '選手A 9:33'


def test_cancelled_practice_is_not_announced_as_held():
    fresh = checks.calendar_projections()['practice-2026-20260820-練習会-岱明--県民スポーツ大会中止に伴い中止']
    assert '中止です' in fresh['answer']
    assert '実施済みです' not in fresh['answer']


def test_legacy_nagomi_athlete_row_is_not_a_team():
    answer = checks.nagomi_projections()['nagomi-team-2026-松浦眞大']['answer']
    assert '金栗PROJECT Aの2区で9:26（区間4位）' in answer
    assert '通過3位・累計19:10' in answer
    assert '総合2位・38:49' in answer
    assert '2区位' not in answer


def test_audit_rejects_a_leg_label_used_as_overall_rank():
    import audit_prepared_qa_facts as audit
    entry = {'id': 'fixture', 'answer': '男子・は総合4区位・。', 'sources': []}
    assert 'invalid_team_result_row' in audit.check_entry(entry, None)['problems']
