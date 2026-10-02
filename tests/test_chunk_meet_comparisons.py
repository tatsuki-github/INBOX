import copy,csv,io,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from chunk_meet_comparisons import render_meet_comparison,validate_meet_comparison

def fixture():
    h=['名前','所属','性別','距離','記録','大会名','日付'];rows=[{'row':1,'cells':['甲','A','男子','1500m','4:59.99','記録会','2025/06/08']},{'row':2,'cells':['乙','B','男子','1500m','5:00.01','記録会','2025/06/08']}]
    q,a,calc=render_meet_comparison(h,rows,'記録');e={'questions':[q],'answer':a,'calculation':calc,'evidence':[{'kind':'csv-rows','header':h,'rows':rows}]};c={'evidence':{'header':h,'units':rows}};o=io.StringIO();w=csv.writer(o);w.writerow(h);w.writerows(r['cells'] for r in rows);return e,c,o.getvalue()

def test_minute_boundary_is_two_hundredths():
    e,c,s=fixture();validate_meet_comparison(e,c,s);assert e['calculation']['gap_seconds']=='0.02';assert e['questions'][0].startswith('2025-06-08')

@pytest.mark.parametrize('index,value',[(2,'女子'),(3,'800m'),(5,'選手権'),(6,'2025/06/09')])
def test_different_groups_cannot_be_compared(index,value):
    e,c,s=fixture();rows=e['evidence'][0]['rows'];rows[1]['cells'][index]=value
    with pytest.raises(ValueError,match='different meet'):render_meet_comparison(c['evidence']['header'],rows,'記録')

def test_same_athlete_cannot_count_twice():
    e,c,s=fixture();rows=e['evidence'][0]['rows'];rows[1]['cells'][0]='甲'
    with pytest.raises(ValueError,match='same athlete'):render_meet_comparison(c['evidence']['header'],rows,'記録')

def test_source_changes_and_outside_chunk_are_rejected():
    e,c,s=fixture()
    with pytest.raises(ValueError,match='source row'):validate_meet_comparison(e,c,s.replace('4:59.99','4:59.98'))
    c['evidence']['units']=[]
    with pytest.raises(ValueError,match='outside'):validate_meet_comparison(e,c,s)

def test_wrong_winner_is_rejected():
    e,c,s=fixture();e['calculation']['faster_row']=2
    with pytest.raises(ValueError,match='drift'):validate_meet_comparison(e,c,s)
