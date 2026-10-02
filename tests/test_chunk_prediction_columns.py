import copy,csv,io,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from chunk_prediction_columns import SOURCE,COLUMNS,PAIRS,render_columns,validate_columns

def fixture():
 h=['所属','種目','性別',*COLUMNS];r={'row':1,'cells':['A中','3000m予想','女子','11:01.25（4人）','10:59.10（4人）','11:31.31（8人）','11:15.20（8人）']};q,a,calc,_=render_columns(h,r,PAIRS[0]);e={'sources':[SOURCE],'questions':[q],'answer':a,'calculation':calc,'evidence':[{'kind':'csv-rows','header':h,'rows':[r]}]};c={'evidence':{'header':h,'units':[copy.deepcopy(r)]}};f=io.StringIO();w=csv.writer(f);w.writerow(h);w.writerow(r['cells']);return e,c,f.getvalue()

def test_exact_decimal_gap_and_population_labels():
 e,c,s=fixture();validate_columns(e,c,s);assert e['calculation']['delta_seconds']=='30.06';assert e['calculation']['populations']==[4,8];assert '保存された予想欄' in e['answer']

@pytest.mark.parametrize('cell,delta',[('10:59.15（8人）','-2.1'),('11:01.25（8人）','0')])
def test_negative_and_zero_differences(cell,delta):
 e,c,s=fixture();r=e['evidence'][0]['rows'][0];r['cells'][5]=cell
 assert render_columns(c['evidence']['header'],r,PAIRS[0])[2]['delta_seconds']==delta

@pytest.mark.parametrize('cell',['11:60.00（8人）','11:01.25','11:01.25（0人）','予測不可（8人）'])
def test_damaged_clock_or_population_is_not_guessed(cell):
 e,c,s=fixture();r=e['evidence'][0]['rows'][0];r['cells'][5]=cell
 with pytest.raises(ValueError):render_columns(c['evidence']['header'],r,PAIRS[0])

def test_different_source_kind_gender_and_season_rejected():
 e,c,s=fixture();e['sources']=[SOURCE.replace('2025','2026')]
 with pytest.raises(ValueError,match='source/year'):validate_columns(e,c,s)
 e,c,s=fixture();r=e['evidence'][0]['rows'][0];r['cells'][1]='3000m実測'
 with pytest.raises(ValueError,match='identity'):render_columns(c['evidence']['header'],r,PAIRS[0])
 r['cells'][1]='3000m予想';r['cells'][2]='不明'
 with pytest.raises(ValueError,match='identity'):render_columns(c['evidence']['header'],r,PAIRS[0])

def test_assignment_cell_and_calculation_drift_rejected():
 e,c,s=fixture()
 with pytest.raises(ValueError,match='source row'):validate_columns(e,c,s.replace('11:31.31','11:31.32'))
 c['evidence']['units']=[]
 with pytest.raises(ValueError,match='outside'):validate_columns(e,c,s)
 e,c,s=fixture();e['calculation']['delta_seconds']='30'
 with pytest.raises(ValueError,match='arithmetic'):validate_columns(e,c,s)
