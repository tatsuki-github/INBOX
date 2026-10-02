import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from chunk_track_coverage import SOURCE,render_coverage,validate_coverage

def fixture():
 athletes=[{'name':'甲','leg':1,'track_events':{'1500m':{'sb':{'mark':'5:01.25','seconds':301.25,'season':'2025'},'recent':None}}},{'name':'乙','leg':2,'track_events':{}},{'name':'丙','leg':3,'track_events':{'1500m':{'sb':None,'recent':{'mark':'5:00.00'}}}}]
 team={'rank':1,'school':'A中','athletes':athletes};u={'pointer':'/years/0/teams/0','value':team,'context':{'year':2025}};q,a,calc,_=render_coverage(u,'1500m');e={'sources':[SOURCE],'questions':[q],'answer':a,'calculation':calc,'evidence':[{'kind':'json-unit','unit':u}]};c={'evidence':{'units':[copy.deepcopy(u)]}};s=json.dumps({'meta':{'title':'女子駅伝トラック突合'},'years':[{'year':2025,'teams':[team]}]},ensure_ascii=False);return e,c,s

def test_count_only_the_saved_sb_fields():
 e,c,s=fixture();validate_coverage(e,c,s);assert e['calculation']['listed_count']==1;assert e['calculation']['listed']==[{'name':'甲','leg':1,'mark':'5:01.25'}];assert '未掲載でも' in e['answer']

def test_zero_is_not_asserted_as_no_career_record():
 e,c,s=fixture();q,a,calc,key=render_coverage(e['evidence'][0]['unit'],'800m');assert calc['listed_count']==0;assert 'その選手に競技記録がないとは言えません' in a

def test_athlete_scope_uses_verified_ancestor_context():
 e,c,s=fixture();team=e['evidence'][0]['unit']['value'];u={'pointer':'/years/0/teams/0/athletes/0','value':team['athletes'][0],'context':{'year':2025,'rank':1,'school':'A中'}};q,a,calc,key=render_coverage(u,'1500m');e.update(questions=[q],answer=a,calculation=calc,evidence=[{'kind':'json-unit','unit':u}]);validate_coverage(e,{'evidence':{'units':[copy.deepcopy(u)]}},s);assert '1区の甲' in q

@pytest.mark.parametrize('field,value',[('season','2024'),('seconds',300.0),('mark','missing')])
def test_mismatched_season_seconds_or_clock_rejected(field,value):
 e,c,s=fixture();u=e['evidence'][0]['unit'];u['value']['athletes'][0]['track_events']['1500m']['sb'][field]=value
 with pytest.raises(ValueError):render_coverage(u,'1500m')

def test_duplicate_roster_names_rejected_before_counting_people():
 e,c,s=fixture();u=e['evidence'][0]['unit'];u['value']['athletes'][1]['name']='甲'
 with pytest.raises(ValueError,match='ambiguous roster'):render_coverage(u,'1500m')

def test_wrong_gender_year_or_source_rejected():
 e,c,s=fixture()
 with pytest.raises(ValueError,match='gender'):validate_coverage(e,c,s.replace('女子','男子'))
 e['sources']=['other.json']
 with pytest.raises(ValueError,match='source'):validate_coverage(e,c,s)
 e,c,s=fixture();u=e['evidence'][0]['unit'];u['context']['year']='2025'
 with pytest.raises(ValueError,match='year'):render_coverage(u,'1500m')

def test_provenance_arithmetic_and_context_drift_rejected():
 e,c,s=fixture()
 with pytest.raises(ValueError,match='source record'):validate_coverage(e,c,s.replace('5:01.25','5:02.25'))
 c['evidence']['units']=[]
 with pytest.raises(ValueError,match='outside'):validate_coverage(e,c,s)
 e,c,s=fixture();e['calculation']['listed_count']=2
 with pytest.raises(ValueError,match='coverage'):validate_coverage(e,c,s)
