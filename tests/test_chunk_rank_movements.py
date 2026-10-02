import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from chunk_rank_movements import render_movement,validate_movement

def fixture():
    team={'team':'甲','legs':[{'leg':1,'passing_rank':12,'split_rank':2,'status':'ok'},{'leg':2,'passing_rank':9,'split_rank':15,'status':'ok'}]}
    unit={'pointer':'/years/2020/teams/0','value':team,'context':{'year':2020,'gender':'男子'}}
    q,a,calc=render_movement(unit,1,2)
    entry={'questions':[q],'answer':a,'calculation':calc,'evidence':[{'kind':'json-unit','unit':unit}]}
    source={'years':{'2020':{'year':2020,'gender':'男子','teams':[team]}}}
    return entry,{'evidence':{'units':[unit]}},source

def test_net_rank_is_not_split_rank():
    e,c,s=fixture();validate_movement(e,c,json.dumps(s));assert e['calculation']['places_gained']==3;assert '3つ上が' in e['answer']

@pytest.mark.parametrize('ranks,expected', [((9,12),-3),((9,9),0)])
def test_losses_and_equal_ranks(ranks,expected):
    e,c,s=fixture();u=e['evidence'][0]['unit']
    for l,r in zip(u['value']['legs'],ranks):l['passing_rank']=r
    assert render_movement(u,1,2)[2]['places_gained']==expected

def test_dnf_cannot_produce_a_rank_change():
    e,c,s=fixture();u=e['evidence'][0]['unit'];u['value']['legs'][1]['status']='dnf'
    with pytest.raises(ValueError,match='incomplete'):render_movement(u,1,2)

def test_other_chunk_cannot_supply_the_team():
    e,c,s=fixture();c['evidence']['units']=[]
    with pytest.raises(ValueError,match='outside'):validate_movement(e,c,json.dumps(s))

def test_wrong_year_context_is_rejected():
    e,c,s=fixture();s['years']['2020']['year']=2019
    with pytest.raises(ValueError,match='context'):validate_movement(e,c,json.dumps(s))

def test_edited_answer_requires_a_new_review():
    e,c,s=fixture();e['answer']='3つ下がった'
    with pytest.raises(ValueError,match='claim drift'):validate_movement(e,c,json.dumps(s))

def test_complete_year_unit_can_ground_its_nested_team():
    from chunk_rank_movements import expand_team_units
    e,c,s=fixture();parent={'pointer':'/years/2020','value':s['years']['2020'],'context':{}}
    e['evidence']=[{'kind':'json-unit','unit':parent}];c['evidence']['units']=[parent]
    assert expand_team_units(parent)[0]['context']['year']==2020
    validate_movement(e,c,json.dumps(s))

def test_nested_pointer_cannot_escape_the_evidence_year():
    e,c,s=fixture();parent={'pointer':'/years/2020','value':s['years']['2020'],'context':{}}
    e['evidence']=[{'kind':'json-unit','unit':parent}];c['evidence']['units']=[parent];e['calculation']['pointer']='/years/2019/teams/0'
    with pytest.raises(ValueError,match='outside evidence'):validate_movement(e,c,json.dumps(s))

def transcript_fixture():
    e,c,s=fixture();s=s['years']['2020'];u=e['evidence'][0]['unit'];u['pointer']='/teams/0'
    q,a,calc=render_movement(u,1,2);e.update(questions=[q],answer=a,calculation=calc)
    return e,c,s

def test_transcript_root_preserves_printed_year_gender_and_ranks():
    e,c,s=transcript_fixture();validate_movement(e,c,json.dumps(s));assert e['calculation']['places_gained']==3
    s['gender']='女子'
    with pytest.raises(ValueError,match='context'):validate_movement(e,c,json.dumps(s))

def test_transcript_teams_list_unit_expands_with_source_context():
    from chunk_rank_movements import expand_team_units
    e,c,s=transcript_fixture();p={'pointer':'/teams','value':s['teams'],'context':{'year':2020,'gender':'男子'}}
    e['evidence']=[{'kind':'json-unit','unit':p}];c['evidence']['units']=[p]
    assert expand_team_units(p)[0]['pointer']=='/teams/0'
    validate_movement(e,c,json.dumps(s))

def test_duplicate_legs_cannot_be_silently_collapsed():
    e,c,s=fixture();u=e['evidence'][0]['unit'];u['value']['legs'].append(copy.deepcopy(u['value']['legs'][0]))
    with pytest.raises(ValueError,match='duplicate'):render_movement(u,1,2)
