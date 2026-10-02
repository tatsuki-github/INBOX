import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from chunk_record_sb_gaps import SOURCES,render_gap,validate_gap

def fixture():
    r={'name':'甲','affiliation':'A','gender':'男子','distance':'1500m','date':'2026/06/08','time_text':'5:00.01','sb_text':'4:59.99','record_seconds':300.01};u={'pointer':'/0','value':r,'context':{}};q,a,calc=render_gap(u);e={'questions':[q],'answer':a,'sources':[sorted(SOURCES)[0]],'calculation':calc,'evidence':[{'kind':'json-unit','unit':u}]};return e,{'evidence':{'units':[u]}},[r]

def test_saved_sb_delta_does_not_assert_current_or_race_day_pb():
    e,c,s=fixture();validate_gap(e,c,json.dumps(s));assert e['calculation']['delta_seconds']=='0.02';assert '同じ保存行' in e['answer'];assert '現在' not in e['answer']

@pytest.mark.parametrize('observed,sb,delta', [('4:59.99','5:00.01','-0.02'),('5:00.01','5:00.01','0')])
def test_faster_and_equal_cells(observed,sb,delta):
    e,c,s=fixture();u=e['evidence'][0]['unit'];u['value'].update(time_text=observed,sb_text=sb,record_seconds=float(observed.split(':')[0])*60+float(observed.split(':')[1]))
    assert render_gap(u)[2]['delta_seconds']==delta

def test_stored_seconds_error_cannot_be_published():
    e,c,s=fixture();u=e['evidence'][0]['unit'];u['value']['record_seconds']=300
    with pytest.raises(ValueError,match='differs'):render_gap(u)

def test_different_source_and_chunk_are_rejected():
    e,c,s=fixture();e['sources']=['other.json']
    with pytest.raises(ValueError,match='unsupported'):validate_gap(e,c,json.dumps(s))
    e['sources']=[sorted(SOURCES)[0]];c['evidence']['units']=[]
    with pytest.raises(ValueError,match='outside'):validate_gap(e,c,json.dumps(s))

def test_wrong_sign_in_answer_is_rejected():
    e,c,s=fixture();e['answer']='記録が0.02秒速い'
    with pytest.raises(ValueError,match='claim drift'):validate_gap(e,c,json.dumps(s))
