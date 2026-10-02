import csv,io,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from chunk_meet_changes import SOURCE,render_change,validate_change

def fixture():
    h=['姓','名','所属','選手権800m記録','通信800m記録','選手権からのタイム差'];r={'row':1,'cells':['甲','乙','A','3:11.06','2:54.81','-16.25']};q,a,calc=render_change(h,r);e={'questions':[q],'answer':a,'sources':[SOURCE],'calculation':calc,'evidence':[{'kind':'csv-rows','header':h,'rows':[r]}]};c={'evidence':{'header':h,'units':[r]}};s=io.StringIO();w=csv.writer(s);w.writerow(h);w.writerow(r['cells']);return e,c,s.getvalue()

def test_improvement_has_a_negative_signed_delta():
    e,c,s=fixture();validate_change(e,c,s);assert e['calculation']['delta_seconds']=='-16.25';assert '16.25秒速く' in e['answer']

@pytest.mark.parametrize('cells,expected', [(['2:54.81','3:11.06','16.25'],'16.25'),(['3:11.06','3:11.06','0'],'0')])
def test_losses_and_equal_times(cells,expected):
    e,c,s=fixture();r=e['evidence'][0]['rows'][0];r['cells'][3:]=cells
    assert render_change(c['evidence']['header'],r)[2]['delta_seconds']==expected

def test_stored_sign_error_is_not_accepted():
    e,c,s=fixture();r=e['evidence'][0]['rows'][0];r['cells'][-1]='16.25'
    with pytest.raises(ValueError,match='disagrees'):render_change(c['evidence']['header'],r)

def test_other_season_is_rejected():
    e,c,s=fixture();e['sources']=[SOURCE.replace('2025','2026')]
    with pytest.raises(ValueError,match='season'):validate_change(e,c,s)

def test_source_drift_and_other_chunk_are_rejected():
    e,c,s=fixture()
    with pytest.raises(ValueError,match='source row'):validate_change(e,c,s.replace('2:54.81','2:54.80'))
    c['evidence']['units']=[]
    with pytest.raises(ValueError,match='outside'):validate_change(e,c,s)
