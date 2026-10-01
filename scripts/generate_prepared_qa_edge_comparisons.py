#!/usr/bin/env python3
"""Add 5000 distinct, dated comparisons from validated race snapshot records.

No cross-year/course comparisons, incomplete totals, or inferred athlete names.
--check verifies the stored batch AND source-pointer evidence without writing.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import re
from collections import Counter, defaultdict, deque
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / 'input/faq/prepared-qa.v1.yaml'
LOG = ROOT / 'backend/data/eval-gaps/edge-comparisons-5000.jsonl'
PREFIX = 'edgecmp-'
QUOTAS = {'total': 800, 'split': 2400, 'cumulative': 1200, 'closing': 600}


def seconds(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{1,3}:[0-5]\d', value):
        return None
    m, s = map(int, value.split(':'))
    return m * 60 + s


def clean_team(team, count):
    """Cumulative claims require every split, sum, and final total to agree."""
    legs = team.get('legs', [])
    if len(legs) != count or [l.get('leg') for l in legs] != list(range(1, count + 1)):
        return False
    acc = 0
    for leg in legs:
        split = seconds(leg.get('split'))
        if leg.get('status') != 'ok' or split is None or split <= 0:
            return False
        acc += split
        if seconds(leg.get('cumulative')) != acc:
            return False
    return seconds(team.get('total')) == acc


def usable_leg(leg):
    name = leg.get('name', '')
    return (leg.get('status') == 'ok' and seconds(leg.get('split')) not in (None, 0)
            and bool(name) and not re.search(r'unknown|不明|[?？—]', name, re.I))


def relation(a, b, va, vb, verb):
    if va == vb:
        return f'{a}と{b}は同タイムです（差0秒）。'
    first, second = (a, b) if va < vb else (b, a)
    return f'{first}が{second}より{abs(va-vb)}秒{verb}。'


def make_entry(kind, year, gender, a, b, leg, src, pa, pb):
    """Render a single explicit two-school question and its narrowly scoped answer."""
    an, bn = a['team'], b['team']
    header = f'{year}年荒玉駅伝{gender}'
    common = f'{header}の{an}と{bn}'
    evidence = {'kind': kind, 'year': year, 'gender': gender, 'source': src,
                'a': pa, 'b': pb, 'leg': leg}
    if kind == 'total':
        va, vb = seconds(a['total']), seconds(b['total'])
        questions = [f'{common}の総合タイム差は？', f'{header}で{bn}と{an}の総合記録は何秒差？']
        answer = f'{header}の総合タイムは{an}が{a["total"]}、{bn}が{b["total"]}です。' + relation(an, bn, va, vb, '速いです')
    else:
        la = next(l for l in a['legs'] if l['leg'] == leg)
        lb = next(l for l in b['legs'] if l['leg'] == leg)
        va, vb = seconds(la['split']), seconds(lb['split'])
        ca, cb = seconds(la.get('cumulative')), seconds(lb.get('cumulative'))
        if kind == 'split':
            questions = [f'{common}の{leg}区の区間タイム差は？', f'{header}の{leg}区で{bn}と{an}の区間記録は何秒差？']
            answer = (f'{header}{leg}区の区間タイムは{an}の{la["name"]}が{la["split"]}、'
                      f'{bn}の{lb["name"]}が{lb["split"]}です。' + relation(an, bn, va, vb, '速いです')
                      + '区間単独の比較です。')
        elif kind == 'cumulative':
            questions = [f'{common}の{leg}区終了時点の累計タイム差は？', f'{header}で{bn}と{an}は{leg}区までの累計で何秒差？']
            answer = (f'{header}{leg}区終了時点の累計タイムは{an}が{la["cumulative"]}、'
                      f'{bn}が{lb["cumulative"]}です。' + relation(an, bn, ca, cb, '先行しています')
                      + '区間単独の差ではありません。')
        else:
            final_a, final_b = seconds(a['total']), seconds(b['total'])
            change = (ca - cb) - (final_a - final_b)
            # The signed change remains correct even if a team overtakes.
            questions = [f'{header}で{an}は{bn}に対して{leg}区終了後からゴールまで何秒取り戻した？',
                         f'{header}の{an}は{bn}との相対的なタイム差を{leg}区後からゴールまでどう変えた？']
            label = f'相対的に{change}秒取り戻しました' if change > 0 else (
                f'相対的に{-change}秒失いました' if change < 0 else '相対的なタイム差は変わりませんでした')
            answer = (f'{header}で{an}は{bn}に対して、{leg}区終了後からゴールまでに{label}。'
                      f'{leg}区終了時の累計は{an}{la["cumulative"]}・{bn}{lb["cumulative"]}、'
                      f'総合タイムは{an}{a["total"]}・{bn}{b["total"]}です。'
                      '累計の差と総合の差の変化で、抜いた人数を表すものではありません。')
    identity = json.dumps([kind, year, gender, an, bn, leg], ensure_ascii=False)
    eid = f'{PREFIX}{year}-{kind}-' + hashlib.sha256(identity.encode()).hexdigest()[:16]
    return {'id': eid, 'questions': questions, 'answer': answer, 'sources': [src],
            'tags': ['aragyoku', 'edge-comparisons', kind, gender, year]}, evidence


def candidates():
    buckets = defaultdict(list)
    for gender, file, count in [('男子', 'men', 6), ('女子', 'women', 5)]:
        src = f'input/aragyoku/{file}_full_2012_2025.json'
        data = json.loads((ROOT / src).read_text())
        for year, yd in sorted(data['years'].items(), reverse=True):
            teams = yd['teams']
            counts = Counter(t.get('team') for t in teams)
            pairs = list(itertools.combinations(enumerate(teams), 2))
            # Prioritize local team while distributing across all years/sexes/legs.
            pairs.sort(key=lambda p: ('岱明' not in (p[0][1].get('team'), p[1][1].get('team')), p[0][0], p[1][0]))
            for (ai, a), (bi, b) in pairs:
                if any(not t.get('team') or counts[t['team']] != 1 for t in (a, b)):
                    continue
                pa, pb = f'/years/{year}/teams/{ai}', f'/years/{year}/teams/{bi}'
                full = clean_team(a, count) and clean_team(b, count)
                if full:
                    e = make_entry('total', int(year), gender, a, b, None, src, pa, pb)
                    buckets[('total', year, gender, 0)].append(e)
                for n in range(1, count + 1):
                    als = [l for l in a.get('legs', []) if l.get('leg') == n]
                    bls = [l for l in b.get('legs', []) if l.get('leg') == n]
                    if len(als) != 1 or len(bls) != 1:
                        continue
                    if usable_leg(als[0]) and usable_leg(bls[0]):
                        buckets[('split', year, gender, n)].append(make_entry('split', int(year), gender, a, b, n, src, pa, pb))
                    if full and 1 < n < count:
                        for kind in ['cumulative', 'closing']:
                            buckets[(kind, year, gender, n)].append(make_entry(kind, int(year), gender, a, b, n, src, pa, pb))
    return buckets


def gen_entries():
    """Full read-only projection for the existing factual auditor."""
    return [e for bucket in candidates().values() for e, _ in bucket]


def select(existing):
    seen_id = {e['id'] for e in existing}
    seen_q = {q for e in existing for q in e['questions']}
    chosen = []
    pools = candidates()
    for kind, quota in QUOTAS.items():
        queues = [deque(v) for k, v in sorted(pools.items()) if k[0] == kind]
        got = 0
        while got < quota and any(queues):
            for queue in queues:
                if got == quota:
                    break
                while queue:
                    e, evidence = queue.popleft()
                    if e['id'] in seen_id or any(q in seen_q for q in e['questions']):
                        continue
                    seen_id.add(e['id'])
                    seen_q.update(e['questions'])
                    chosen.append((e, evidence))
                    got += 1
                    break
        if got != quota:
            raise ValueError(f'{kind}: only {got} novel entries available; expected {quota}')
    return chosen


def pointer(doc, path):
    for part in path.strip('/').split('/'):
        doc = doc[int(part)] if isinstance(doc, list) else doc[part]
    return doc


def verify(entries, rows):
    """Validate exact answer/identities from source pointers; no FAQ as evidence."""
    by_id = {e['id']: e for e in entries if e['id'].startswith(PREFIX)}
    assert len(rows) == len(by_id) == 5000, 'batch must contain exactly 5000 entries'
    assert len({r['id'] for r in rows}) == len(rows), 'duplicate evidence IDs'
    sources = {}
    for r in rows:
        ev = r['evidence']
        src = ev['source']
        if src not in sources:
            raw = (ROOT / src).read_bytes()
            sources[src] = (json.loads(raw), hashlib.sha256(raw).hexdigest())
        doc, digest = sources[src]
        assert digest == r['source_sha256'], f'source drift: {src}'
        a, b = pointer(doc, ev['a']), pointer(doc, ev['b'])
        year = doc['years'][str(ev['year'])]
        assert year['gender'] == ev['gender']
        assert ev['a'].startswith(f'/years/{ev["year"]}/') and ev['b'].startswith(f'/years/{ev["year"]}/')
        count = 6 if ev['gender'] == '男子' else 5
        if ev['kind'] != 'split':
            assert clean_team(a, count) and clean_team(b, count), 'inconsistent cumulative record'
        else:
            assert all(usable_leg(next(l for l in t['legs'] if l['leg'] == ev['leg'])) for t in (a, b))
        expected, _ = make_entry(ev['kind'], ev['year'], ev['gender'], a, b, ev['leg'], src, ev['a'], ev['b'])
        assert by_id[r['id']] == expected, f'answer/question/source drift: {r["id"]}'
        assert all(str(ev['year']) in q for q in expected['questions'])
        assert not re.search(r'input/|out/|unknown|None|\?', expected['answer'])
        assert len(expected['answer']) < 400
    assert Counter(r['evidence']['kind'] for r in rows) == Counter(QUOTAS)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    data = yaml.load(FAQ.read_text(), Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
    if args.check or any(e['id'].startswith(PREFIX) for e in data['entries']):
        rows = [json.loads(s) for s in LOG.read_text().splitlines()]
        verify(data['entries'], rows)
        print('OK: all 5000 comparisons match source records; no writes')
        return
    chosen = select(data['entries'])
    hashes = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in {s for e, _ in chosen for s in e['sources']}}
    rows = [{'id': e['id'], 'evidence': ev, 'source_sha256': hashes[ev['source']]} for e, ev in chosen]
    merged = data['entries'] + [e for e, _ in chosen]
    verify(merged, rows)
    print(f'Validated +{len(chosen)} entries ({QUOTAS}); total={len(merged)}')
    for e, _ in chosen[::1000]:
        print(e['questions'][0], '=>', e['answer'])
    if args.dry_run:
        return
    data['entries'] = merged
    data['total'] = len(merged)
    data['note'] = data.get('note', '').rstrip() + '\nedge-comparisons-5000: 同一大会・男女・区間の学校間比較を追加5000件（総合差・区間差・累計差・終盤の差の変化）。\n'
    original_body = FAQ.read_text().split('\nentries:\n', 1)[1]
    header = yaml.safe_dump({k: v for k, v in data.items() if k != 'entries'},
                            allow_unicode=True, sort_keys=False, width=120)
    FAQ.write_text(header + 'entries:\n' + original_body.rstrip() + '\n' +
                   yaml.safe_dump([e for e, _ in chosen], allow_unicode=True, sort_keys=False, width=120))
    LOG.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))

if __name__ == '__main__':
    main()
