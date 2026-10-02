import copy,csv,io,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from chunk_calendar_gaps import render_gap,validate_gap

def fixture(start='2024-02-28',end='2024-03-01'):
 units=[{'pointer':'/events/0','value':{'title':'合同練習会','date':start},'context':{'year':2024}},{'pointer':'/events/1','value':{'title':'県陸上選手権','date':end},'context':{'year':2024}}]
 q,a,calc=render_gap(units);e={'sources':['input/events.2024.yaml'],'questions':[q],'answer':a,'calculation':calc,'evidence':[{'kind':'calendar-json-units','units':units}]};c={'evidence':{'units':copy.deepcopy(units)}};s=json.dumps({'year':2024,'events':[u['value'] for u in units]},ensure_ascii=False);return e,c,s

def test_leap_year_is_elapsed_not_inclusive():
 e,c,s=fixture();validate_gap(e,c,s);assert e['calculation']['days']==2

def test_year_boundary():
 e,c,s=fixture('2024-12-31','2025-01-01');validate_gap(e,c,s);assert e['calculation']['days']==1

def test_yaml_dates_are_literal_and_normalized():
 e,c,s=fixture();s='year: 2024\nevents:\n  - title: 合同練習会\n    date: 2024-02-28\n  - title: 県陸上選手権\n    date: 2024-03-01\n';validate_gap(e,c,s)

@pytest.mark.parametrize('title', ['自分の練習','健康診断','個人陸上練習','謝礼の陸上連絡','口座大会'])
def test_private_or_sensitive_titles_are_not_selected(title):
 e,c,s=fixture();u=e['evidence'][0]['units'];u[0]['value']['title']=title
 with pytest.raises(ValueError,match='public'):render_gap(u)

def test_private_flag_and_same_day_rejected():
 e,c,s=fixture();u=e['evidence'][0]['units'];u[0]['value']['private']=True
 with pytest.raises(ValueError,match='public'):render_gap(u)
 u[0]['value'].pop('private');u[1]['value']['date']=u[0]['value']['date']
 with pytest.raises(ValueError,match='ordered'):render_gap(u)

def test_wrong_source_assignment_and_fabricated_arithmetic_rejected():
 e,c,s=fixture()
 with pytest.raises(ValueError,match='source record'):validate_gap(e,c,s.replace('2024-03-01','2024-03-02'))
 c['evidence']['units']=[]
 with pytest.raises(ValueError,match='outside'):validate_gap(e,c,s)
 e,c,s=fixture();e['calculation']['days']=3
 with pytest.raises(ValueError,match='arithmetic'):validate_gap(e,c,s)

def test_google_csv_dates_and_cell_alignment():
 h=['Subject','Start Date','Private'];rows=[{'row':1,'cells':['合同練習会','02/28/2024','False']},{'row':2,'cells':['県陸上選手権','03/01/2024','False']}];q,a,calc=render_gap(rows,h);e={'sources':['out/2024/google.csv'],'questions':[q],'answer':a,'calculation':calc,'evidence':[{'kind':'csv-rows','header':h,'rows':rows}]};c={'evidence':{'header':h,'units':copy.deepcopy(rows)}};f=io.StringIO();w=csv.writer(f);w.writerow(h);w.writerows(r['cells'] for r in rows);s=f.getvalue();validate_gap(e,c,s)
 with pytest.raises(ValueError,match='source row'):validate_gap(e,c,s.replace('03/01/2024','03/02/2024'))
 with pytest.raises(ValueError,match='column'):render_gap([{'cells':['broken']},rows[1]],h)
