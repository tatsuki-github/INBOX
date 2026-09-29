"""Source-backed recent competition history for each forecast athlete."""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = date(2026, 8, 29)
TRACK = 'input/external/drive/personal/t-tsuchiyama/sb/by-year/2026-single-table.csv'
NOTION = 'out/analysis/notion_records_2026.json'
NAGOMI = 'input/external/drive/shared/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/成績表.json'
JUNIOR = 'input/external/drive/shared/大会/2026年度/0926_第４回県ジュニア陸上（第３回県ジュニア駅伝）/荒玉地区の結果.md'
TRIAL = 'out/analysis/2026-09-29_aragyoku_trial_results.json'
# These are candidate spellings in the junior transcription, not verified aliases.
CANDIDATE_NAMES = {'萩原康秀': '秋原康秀', '荻原大介': '萩原大介', '大原彩遥': '大原彩透'}


def norm(value: str) -> str:
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value)).replace('凜', '凛')


def format_seconds(value: float) -> str:
    minutes, seconds = divmod(round(value, 2), 60)
    if seconds.is_integer():
        return f'{int(minutes)}:{int(seconds):02d}'
    return f'{int(minutes)}:{seconds:05.2f}'


def collect_recent_results(targets: list[dict], through: date | None = None) -> list[dict]:
    through = through or date.today()
    roster = {(r['gender'], norm(r['name'])): r for r in targets}
    records: dict[tuple, dict] = {}

    def add(gender: str, name: str, when: str, event: str, discipline: str,
            km: float | None, result: str, source: str, *, kind: str = 'competition',
            affiliation: str = '', note: str = '', url: str = '') -> None:
        try:
            when_date = date.fromisoformat(when.replace('/', '-')[:10])
        except ValueError:
            return
        if not START <= when_date <= through:
            return
        key = gender, norm(name)
        candidate = False
        if key not in roster and norm(name) in CANDIDATE_NAMES:
            key = gender, norm(CANDIDATE_NAMES[norm(name)])
            candidate = True
        if key not in roster:
            return
        target = roster[key]
        if candidate:
            note = f'氏名照合要確認：原資料「{name}」' + (f'；{note}' if note else '')
        if key == ('男子', norm('松山哲丈')) and affiliation == '山鹿中':
            note = '所属表記：山鹿中（ユーザーが本人のSBと照合）' + (f'；{note}' if note else '')
        result = str(result or '記録未確認').strip()
        # CSV/Notion may contain the same race with differing decimal padding.
        try:
            parts = [float(x) for x in result.split(':')]
            result_identity = round(sum(v * 60 ** i for i, v in enumerate(reversed(parts))), 2)
        except ValueError:
            result_identity = result.upper()
        identity = key, when_date.isoformat(), km, result_identity, kind, discipline
        row = dict(gender=gender, team=target['team'], name=target['name'],
                   date=when_date.isoformat(), event=event, discipline=discipline,
                   distance_km=km, result=result, kind=kind, affiliation=affiliation,
                   note=note, source=source, url=url, identity_confirmed=not candidate)
        if identity not in records:
            records[identity] = row

    with (ROOT / TRACK).open(encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            distance = row['距離']
            m = re.fullmatch(r'([\d.]+)(km|m)', distance)
            km = float(m[1]) * (1 if m[2] == 'km' else .001) if m else None
            notes = []
            if row.get('組'):
                notes.append(f"{row['組']}組")
            if row.get('組着順'):
                notes.append(f"組{row['組着順']}着")
            add(row['性別'], row['名前'], row['日付'], row['大会名'], distance,
                km, row['記録'], TRACK, affiliation=row['所属'],
                note='・'.join(notes), url=row.get('参考', ''))
    for row in json.loads((ROOT / NOTION).read_text()):
        distance = row.get('distance', '')
        m = re.fullmatch(r'([\d.]+)(km|m)', distance)
        km = float(m[1]) * (1 if m[2] == 'km' else .001) if m else None
        add(row.get('gender', ''), row.get('name', ''), row.get('date', ''),
            row.get('meet') or 'Notion陸上記録（大会名未確認）', distance, km,
            row.get('time_text') or format_seconds(float(row['record_seconds'])),
            NOTION, affiliation=row.get('affiliation', ''), url=row.get('url', ''))

    payload = json.loads((ROOT / NAGOMI).read_text())
    for field, gender, km in (('men', '男子', 3.), ('women', '女子', 2.)):
        for team in payload[field]:
            for leg, row in enumerate(team['legs'], 1):
                note = f"区間{row.get('split_rank', '—')}位／チーム{team['rank']}位 {team['total']}"
                add(gender, row.get('name', ''), payload['event']['date'],
                    payload['event']['title'], f'{leg}区', km, row.get('split'),
                    NAGOMI, affiliation=team['team'], note=note)

    section = ''; team = ''; team_note = ''
    for line in (ROOT / JUNIOR).read_text().splitlines():
        line = line.strip()
        if re.fullmatch(r'(男子|女子)(チャンピオンシップ|チャレンジ|オープン)', line):
            section = line; team = ''; team_note = ''; continue
        if not section:
            continue
        gender = section[:2]
        event = '第3回熊本県ジュニア駅伝 ' + section[2:]
        heading = re.fullmatch(r'(\d+)位\s+(.+?)\s+総合(\d+:\d{2})', line)
        if heading:
            team = heading[2]; team_note = f'チーム{heading[1]}位 {heading[3]}'; continue
        split = re.fullmatch(r'(\d+)区\s+([\d.]+)km\s+(.+?)（(\d+)年）(\d+:\d{2})', line)
        if split:
            add(gender, split[3], '2026-09-26', event, f'{split[1]}区',
                float(split[2]), split[5], JUNIOR, affiliation=team, note=team_note)
            continue
        if section.endswith('オープン'):
            item = re.fullmatch(r'(\d+)位\s+(.+?)\s+(.+?)（(\d+)年）(\d+:\d{2})', line)
            if item:
                add(gender, item[3], '2026-09-26', event, 'オープン',
                    2.6 if gender == '男子' else 2.3, item[5], JUNIOR,
                    affiliation=item[2], note=f'{item[1]}位')
        elif section.endswith('チャレンジ') and '／' in line:
            for leg, item in enumerate(line.split('／'), 1):
                split = re.fullmatch(r'(.+?)（(\d+)年）(\d+:\d{2})', item.strip())
                if split:
                    km = (3.0 if leg == 1 else 2.6) if gender == '男子' else (2.7 if leg == 1 else 2.3)
                    add(gender, split[1], '2026-09-26', event, f'{leg}区', km,
                        split[3], JUNIOR, affiliation=team, note=team_note)

    if (ROOT / TRIAL).exists():
        payload = json.loads((ROOT / TRIAL).read_text())
        for row in payload['records']:
            if not row.get('name'):
                continue
            note = '試走（一斉走）' if row.get('start') else '試走'
            if row.get('laps'):
                note += '／ラップ ' + '・'.join(row['laps'])
            if row.get('total_minus_lap_sum_sec'):
                note += f"／報告総タイムはラップ合計より{row['total_minus_lap_sum_sec']}秒多い"
            add('男子', row['name'], payload['date'], payload['event'],
                f"{row['leg']}区", row['distance_km'], row['time'], TRIAL,
                kind='trial', affiliation='岱明中', note=note)
    return sorted(records.values(), key=lambda r: (r['gender'], r['team'], norm(r['name']), r['date'], r['event'], r['discipline']))


def render_recent_results(gender: str, teams: list[dict], records: list[dict]) -> list[str]:
    by_name = defaultdict(list)
    for row in records:
        if row['gender'] == gender:
            by_name[norm(row['name'])].append(row)
    source_ids = {source: f'S{i}' for i, source in enumerate(dict.fromkeys(r['source'] for r in records), 1)}
    lines = ['', '## 各選手の8月29日以降の大会結果', '',
             '対象は2026年8月29日以降の取り込み済み大会資料。SBに限らず、全種目・DNSなどを掲載。順位は原資料にある場合に記載する。氏名・大会名が未確認の記録はその旨を表示する。9月29日の試走は参考記録として併記。', '']
    clean = lambda value: str(value).replace('|', '／').replace('\n', ' ')
    used_sources = set()
    for team in teams:
        lines += [f"### {team['team']}", '',
                  '| 予想区間 | 選手 | 日付 | 大会 | 種目・実績区間 | 距離 | 記録 | 順位・備考 | 出典 |',
                  '| ---: | --- | --- | --- | --- | ---: | ---: | --- | --- |']
        for athlete in team['legs']:
            history = by_name[norm(athlete['name'])]
            if not history:
                lines.append(f"| {athlete['leg']}区 | {athlete['name']} | — | 8/29以降の結果資料未確認 | — | — | — | 出場状況未確認 | — |")
            for row in history:
                sid = source_ids[row['source']]; used_sources.add(row['source'])
                source = f"[{sid}]({row['url']})" if row['url'].startswith(('https://', 'http://')) else sid
                km = f"{row['distance_km']:g}km" if row['distance_km'] is not None else '—'
                vals = [f"{athlete['leg']}区", athlete['name'], row['date'], row['event'],
                        row['discipline'], km, row['result'], row['note'] or '—', source]
                lines.append('| ' + ' | '.join(clean(v) for v in vals) + ' |')
        lines.append('')
    lines += ['出典資料:', '']
    for source, sid in source_ids.items():
        if source in used_sources:
            lines.append(f'- {sid}: `{source}`')
    lines.append('')
    return lines
