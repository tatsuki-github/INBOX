import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from manual_json_evidence import validate_manual_json

def fixture():
    s={'years':{'2019':{'year':2019,'gender':'男子','teams':[{'rank':1,'team':'甲','total':None}]}}};u={'pointer':'/years/2019/teams/0','value':s['years']['2019']['teams'][0],'context':{'year':2019,'gender':'男子'}};return {'evidence':[{'kind':'json-unit','unit':u}]},{'evidence':{'units':[u]}},s

def test_null_values_are_grounded_without_inventing_a_time():
    e,c,s=fixture();validate_manual_json(e,c,json.dumps(s))

def test_wrong_year_cannot_supply_context():
    e,c,s=fixture();e['evidence'][0]['unit']['context']['year']=2020
    with pytest.raises(ValueError,match='context'):validate_manual_json(e,c,json.dumps(s))

def test_record_from_a_different_chunk_is_rejected():
    e,c,s=fixture();c['evidence']['units']=[]
    with pytest.raises(ValueError,match='outside'):validate_manual_json(e,c,json.dumps(s))

def test_changed_source_invalidates_review():
    e,c,s=fixture();s=copy.deepcopy(s);s['years']['2019']['teams'][0]['total']='60:00'
    with pytest.raises(ValueError,match='changed'):validate_manual_json(e,c,json.dumps(s))
