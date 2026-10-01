"""Independent fixtures for CSV clock comparison semantics and provenance."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from chunk_time_comparisons import clock_seconds, render_comparison, validate_csv_comparison

HEADER=['名前','所属','性別','カテゴリー','1500mSB']

def fixture(a='9:59.99',b='10:00.01'):
    rows=[{'row':1,'cells':['甲','甲中','男子','中学生',a]}, {'row':2,'cells':['乙','乙中','男子','中学生',b]}]
    q,answer,calc=render_comparison(HEADER,rows,'1500mSB')
    entry={'questions':[q],'answer':answer,'calculation':calc,'evidence':[{'kind':'csv-rows','header':HEADER,'rows':rows}]}
    chunk={'evidence':{'header':HEADER,'units':rows}}
    source=','.join(HEADER)+'\n'+ '\n'.join(','.join(r['cells']) for r in rows)+'\n'
    return entry,chunk,source


def test_minute_boundary_is_a_two_hundredths_gap():
    e,c,s=fixture()
    assert e['calculation']['gap_seconds']=='0.02'
    assert e['calculation']['faster_row']==1
    assert '0.02秒速い' in e['answer']
    validate_csv_comparison(e,c,s)


def test_tie_has_no_invented_winner():
    e,c,s=fixture('4:30.13','4:30.13')
    assert e['calculation']['gap_seconds']=='0'
    assert e['calculation']['faster_row'] is None
    assert '同タイム' in e['answer']
    validate_csv_comparison(e,c,s)


def test_record_moved_outside_the_chunk_is_rejected():
    e,c,s=fixture();c['evidence']['units']=c['evidence']['units'][:1]
    with pytest.raises(ValueError,match='outside assigned chunk'):validate_csv_comparison(e,c,s)


def test_wrong_winner_cannot_be_published():
    e,c,s=fixture();e['calculation']['faster_row']=2
    with pytest.raises(ValueError,match='arithmetic drift'):validate_csv_comparison(e,c,s)


@pytest.mark.parametrize('value',['1:75','DNS','0:00','4:5','-1:30'])
def test_invalid_or_absent_clock_is_not_invented(value):
    with pytest.raises(ValueError):clock_seconds(value)
