#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026年度岱明中のSB±3秒に該当する歴代選手の駅伝実績をHTML化する。"""
from __future__ import annotations

import html
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/analysis/1500m_sb_band_ekiden.html"
CURRENT = ROOT / "input/external/notion/databases/2026年度中学生記録/rows_daimyo_view.json"
SB_DIR = ROOT / "input/external/sb/middle-school/by-year"
EKIDEN = {
    "女子": ROOT / "input/aragyoku/women_full_2012_2025.json",
    "男子": ROOT / "input/aragyoku/men_full_2012_2025.json",
}


def norm(s: str) -> str:
    return unicodedata.normalize("NFKC", str(s or "")).replace(" ", "").replace("　", "")


def parse_sec(s: str | float | int | None) -> float | None:
    if s in (None, "", "—", "-"):
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).replace("’", ":").replace("'", ":")
    if re.fullmatch(r"\d+(?:\.\d+)?", s.strip()):
        return float(s.strip())
    m = re.fullmatch(r"(\d+):(\d{2})(?:\.(\d+))?", s.strip())
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2)) + float("0." + (m.group(3) or "0"))


def fmt(sec: float | None) -> str:
    if sec is None:
        return "—"
    m, s = divmod(sec, 60)
    return f"{int(m)}:{s:05.2f}"


def load_current() -> list[dict]:
    targets = {
        "男子": [270.0, 285.0, 300.0],
        "女子": [285.0, 300.0, 315.0, 330.0],
    }
    return [
        {"name": f"{gender} 1500m {fmt(sec)}基準", "gender": gender, "distance": "1500m", "sb": sec}
        for gender, seconds in targets.items()
        for sec in seconds
    ]


def load_sb() -> list[dict]:
    out = []
    for p in sorted(SB_DIR.glob("*-sb-adopted.json")):
        if not p.stem[:4].isdigit() or p.stem.endswith("status"):
            continue
        year = int(p.stem[:4])
        for r in json.loads(p.read_text()):
            sec = parse_sec(r.get("SB秒") or r.get("SB"))
            if sec is None:
                continue
            out.append({"year": year, "name": r.get("名前"), "gender": r.get("性別"), "distance": r.get("距離"), "sb": sec, "source": r.get("参考")})
    return out


def load_ekiden() -> dict[tuple[int, str, str], list[dict]]:
    out: dict[tuple[int, str, str], list[dict]] = {}
    for gender, path in EKIDEN.items():
        data = json.loads(path.read_text())
        for year_text, y in data.get("years", {}).items():
            year = int(year_text)
            for team in y.get("teams", []):
              for leg in team.get("legs", []):
                name = leg.get("name")
                sec = parse_sec(leg.get("split"))
                if name and sec is not None:
                    out.setdefault((year, gender, norm(name)), []).append({"team": team.get("team"), "leg": leg.get("leg"), "distance_km": leg_distance(gender, leg.get("leg")), "time": leg.get("split"), "sec": sec, "rank": leg.get("split_rank"), "team_rank": team.get("rank"), "total": team.get("total")})
    return out


def leg_distance(gender: str, leg: int | None) -> float | None:
    if gender == "女子":
        return {1: 3.0, 2: 1.855, 3: 2.0, 4: 2.0, 5: 3.0}.get(leg)
    return {1: 3.0, 2: 2.855, 3: 2.855, 4: 2.855, 5: 2.855, 6: 3.0}.get(leg)


def main() -> None:
    current, sb, ekiden = load_current(), load_sb(), load_ekiden()
    matches = []
    for athlete in current:
        for r in sb:
            delta = r["sb"] - athlete["sb"]
            if r["year"] == 2026 or r["gender"] != athlete["gender"] or r["distance"] != athlete["distance"] or abs(delta) > 3:
                continue
            legs = ekiden.get((r["year"], r["gender"], norm(r["name"])), [])
            for leg in legs:
                matches.append({"current": athlete["name"], "current_sb": athlete["sb"], "gender": athlete["gender"], "distance": athlete["distance"], "historical_year": r["year"], "historical_name": r["name"], "historical_school": r.get("所属"), "historical_sb": r["sb"], "sb_delta": delta, "team": leg["team"], "leg": leg["leg"], "ekiden_distance_km": leg["distance_km"], "ekiden_time": leg["time"], "ekiden_sec": leg["sec"], "split_rank": leg["rank"], "team_rank": leg["team_rank"], "team_total": leg["total"], "source": r["source"]})
    matches.sort(key=lambda x: (x["gender"], x["current"], x["historical_year"], x["ekiden_sec"]))
    by_current = {}
    for m in matches:
        by_current.setdefault(m["current"], []).append(m)
    def render_table(gender: str) -> str:
        gender_matches = [m for m in matches if m["gender"] == gender]
        rows = []
        for m in gender_matches:
            rows.append("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in [m['current'], m['distance'], m['historical_year'], m['historical_name'], m.get('historical_school') or '—', fmt(m['historical_sb']), f"{m['sb_delta']:+.2f}", m['team'], f"{m['leg']}区", f"{m['ekiden_distance_km']}km", m['ekiden_time'], f"{m['split_rank'] or '—'}", f"{m['team_rank']}位"]) + "</tr>")
        body = ''.join(rows) if rows else '<tr><td colspan="13">該当する駅伝実績はありません</td></tr>'
        return f'''<h2>{gender}</h2><div class="table-wrap"><table><thead><tr><th>基準SB帯</th><th>種目</th><th>過去年</th><th>過去選手（全校）</th><th>過去所属</th><th>過去SB</th><th>SB差</th><th>駅伝学校</th><th>駅伝区間</th><th>駅伝距離</th><th>駅伝記録</th><th>区間順位</th><th>チーム順位</th></tr></thead><tbody>{body}</tbody></table></div>'''
    payload = json.dumps(matches, ensure_ascii=False)
    summary = f"基準SB {len(current)}帯 / ±3秒に該当する過去SB {len(set((m['historical_year'], m['historical_name'], m['distance']) for m in matches))}件 / 駅伝実績 {len(matches)}件"
    document = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>1500m SB帯別 駅伝実績分析</title><style>body{{font-family:system-ui,-apple-system,sans-serif;color:#1f2937;background:#f7f8fa;margin:0}}main{{max-width:1500px;margin:auto;padding:32px}}h1{{margin:0 0 8px}}h2{{margin:28px 0 10px}}.lead{{color:#596579}}.summary{{background:#fff;border:1px solid #dfe3e8;border-radius:12px;padding:16px;margin:20px 0}}.note{{background:#fffdf3;border-left:4px solid #c9961a;padding:12px 16px;margin:16px 0}}.table-wrap{{overflow:auto;background:white;border:1px solid #dfe3e8;border-radius:12px}}table{{border-collapse:collapse;width:100%;font-size:14px;white-space:nowrap}}th,td{{padding:9px 10px;border-bottom:1px solid #edf0f2;text-align:left}}th{{position:sticky;top:0;background:#eef2f5;font-weight:650}}tr:hover{{background:#f5f8fb}}footer{{margin-top:20px;color:#6b7280;font-size:13px}}</style></head><body><main><h1>1500m SB帯別：全校選手の駅伝実績</h1><p class="lead">男子は4:30・4:45・5:00、女子は4:45・5:00・5:15・5:30を基準に、各±3.00秒の範囲に入る全学校の選手を抽出し、荒玉駅伝での走りを突合。</p><div class="summary">{summary}</div><div class="note"><strong>解釈上の注意：</strong>駅伝記録はトラック1500mの記録そのものではありません。区間距離・路面・コース・気象・タスキ条件が異なるため、近いSB帯の選手が駅伝で実際に走った記録として参照してください。過去SBは年度別SB採用データ、駅伝区間は荒玉駅伝結果データを使用しています。</div>{render_table('男子')}{render_table('女子')}<footer>生成元：年度別中学生SB採用データ、荒玉中体連駅伝の年度別結果。生成日：2026-09-11。SB差は「過去SB−基準SB」。</footer><script>const data={payload};</script></main></body></html>'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(document, encoding="utf-8")
    print(f"wrote {OUT} matches={len(matches)} current={len(current)}")


if __name__ == "__main__":
    main()
