"""Reviewed schema for net passing-rank changes within a team and year.

Passing rank is never treated as split rank or as a count of actual overtakes.
Only literal, nonmissing ranks with distinct known leg numbers are used.
"""
import json
import re
from prepare_knowledge_qa_chunks import resolve_pointer

TEAM_POINTER = re.compile(r'^/years/(20\d{2})/teams/(\d+)$')


def render_movement(unit, from_leg, to_leg):
    match = TEAM_POINTER.fullmatch(unit['pointer'])
    team = unit['value']; context = unit['context']
    if not match or not isinstance(team, dict) or not team.get('team'):
        raise ValueError('unsupported team record')
    year = int(match[1]); gender = context.get('gender')
    if context.get('year') != year or gender not in ('男子', '女子'):
        raise ValueError('year or gender context differs')
    legs = {r['leg']: r for r in team.get('legs', [])}
    if from_leg >= to_leg or from_leg not in legs or to_leg not in legs:
        raise ValueError('invalid leg sequence')
    a, b = legs[from_leg], legs[to_leg]
    ranks = [a.get('passing_rank'), b.get('passing_rank')]
    if any(type(n) is not int or n < 1 for n in ranks):
        raise ValueError('missing or invalid passing rank')
    if a.get('status') != 'ok' or b.get('status') != 'ok':
        raise ValueError('incomplete result')
    before, after = ranks; delta = before - after
    change = f'{delta}つ上がっています' if delta > 0 else f'{-delta}つ下がっています' if delta < 0 else '変わっていません'
    q = f'{year}年荒玉駅伝{gender}の{team["team"]}は、{from_leg}区終了から{to_leg}区終了で通過順位が何位変わった？'
    answer = f'{from_leg}区終了時は{before}位、{to_leg}区終了時は{after}位で、通過順位は{change}。'
    calc = {'operation': 'passing_rank_change', 'pointer': unit['pointer'], 'from_leg': from_leg,
            'to_leg': to_leg, 'before_rank': before, 'after_rank': after, 'places_gained': delta}
    return q, answer, calc


def expand_team_units(unit):
    if TEAM_POINTER.fullmatch(unit['pointer']):
        return [unit]
    if not re.fullmatch(r'/years/20\d{2}', unit['pointer']) or not isinstance(unit['value'], dict):
        return []
    year = unit['value']
    labels = {k:v for k,v in year.items() if not isinstance(v,(dict,list)) and len(str(v))<=160}
    return [{'pointer':unit['pointer']+'/teams/'+str(i),'value':team,
             'context':{**unit['context'],**labels}}
            for i,team in enumerate(year.get('teams',[]))]


def validate_movement(entry, chunk, source_text):
    evidence = entry.get('evidence') or []
    if len(evidence) != 1 or evidence[0].get('kind') != 'json-unit':
        raise ValueError('expected typed JSON record')
    parent = evidence[0]['unit']; pointer = entry['calculation']['pointer']
    assigned = {u['pointer']: u for u in chunk['evidence']['units']}
    if assigned.get(parent['pointer']) != parent:
        raise ValueError('record outside assigned chunk')
    from manual_json_evidence import validate_manual_json
    validate_manual_json(entry, chunk, source_text)
    matches = [u for u in expand_team_units(parent) if u['pointer'] == pointer]
    if not matches:
        raise ValueError('team record outside evidence unit')
    unit = matches[0]
    source = json.loads(source_text)
    if resolve_pointer(source, pointer) != unit['value']:
        raise ValueError('source record drift')
    match = TEAM_POINTER.fullmatch(pointer)
    if not match:
        raise ValueError('unsupported JSON pointer')
    year_record = source['years'][match[1]]
    expected_year = year_record.get('year', int(match[1]))
    expected_gender = year_record.get('gender', source.get('meta', {}).get('gender'))
    if unit['context'].get('year') != expected_year or unit['context'].get('gender') != expected_gender:
        raise ValueError('source context drift')
    calculation = entry['calculation']
    q, a, calc = render_movement(unit, calculation['from_leg'], calculation['to_leg'])
    if entry['questions'] != [q] or entry['answer'] != a or calculation != calc:
        raise ValueError('movement claim drift')
    # Independent net-change assertion; a positive value means a lower rank.
    ranks = {l['leg']: l['passing_rank'] for l in unit['value']['legs']}
    if calc['places_gained'] + ranks[calc['to_leg']] != ranks[calc['from_leg']]:
        raise ValueError('independent rank arithmetic failed')
