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
OUT = ROOT / "out/analysis/daimyo_sb_ekiden_proximity.html"
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
    rows = json.loads(CURRENT.read_text())['results']
    seen: dict[tuple[str, str], dict] = {}
    for r in rows:
        if r.get("所属") != "岱明中" or r.get("SB採用") != "__YES__":
            continue
        key = (norm(r.get("名前")), r.get("性別", ""))
        seen[key] = {"name": r.get("名前"), "gender": r.get("性別"), "distance": r.get("距離"), "sb": float(r.get("SB秒"))}
    return list(seen.values())


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
            team = next((t for t in y.get("teams", []) if norm(t.get("team")) == "岱明"), None)
            if not team:
                continue
            for leg in team.get("legs", []):
                name = leg.get("name")
                sec = parse_sec(leg.get("split"))
                if name and sec is not None:
                    out.setdefault((year, gender, norm(name)), []).append({"leg": leg.get("leg"), "time": leg.get("split"), "sec": sec, "rank": leg.get("split_rank"), "team_rank": team.get("rank"), "total": team.get("total")})
    return out


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
                matches.append({"current": athlete["name"], "current_sb": athlete["sb"], "gender": athlete["gender"], "distance": athlete["distance"], "historical_year": r["year"], "historical_name": r["name"], "historical_sb": r["sb"], "sb_delta": delta, "leg": leg["leg"], "ekiden_time": leg["time"], "ekiden_sec": leg["sec"], "split_rank": leg["rank"], "team_rank": leg["team_rank"], "team_total": leg["total"], "source": r["source"]})
    matches.sort(key=lambda x: (x["gender"], x["current"], x["historical_year"], x["ekiden_sec"]))
    by_current = {}
    for m in matches:
        by_current.setdefault(m["current"], []).append(m)
    def render_table(gender: str) -> str:
        gender_matches = [m for m in matches if m["gender"] == gender]
        rows = []
        for m in gender_matches:
            rows.append("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in [m['current'], fmt(m['current_sb']), m['distance'], m['historical_year'], m['historical_name'], fmt(m['historical_sb']), f"{m['sb_delta']:+.2f}", f"{m['leg']}区", m['ekiden_time'], f"{m['split_rank'] or '—'}", f"{m['team_rank']}位"]) + "</tr>")
        body = ''.join(rows) if rows else '<tr><td colspan="11">該当する駅伝実績はありません</td></tr>'
        return f'''<h2>{gender}</h2><div class="table-wrap"><table><thead><tr><th>今年度岱明</th><th>今年度SB</th><th>種目</th><th>過去年</th><th>過去選手（全校）</th><th>過去SB</th><th>SB差</th><th>駅伝区間</th><th>駅伝記録</th><th>区間順位</th><th>チーム順位</th></tr></thead><tbody>{body}</tbody></table></div>'''
    payload = json.dumps(matches, ensure_ascii=False)
    summary = f"対象者 {len(current)}人 / SB±3秒に該当する過去SB {len(set((m['historical_year'], m['historical_name'], m['distance']) for m in matches))}件 / 駅伝実績 {len(matches)}件"
    document = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>岱明中 SB±3秒 駅伝実績分析</title><style>body{{font-family:system-ui,-apple-system,sans-serif;color:#1f2937;background:#f7f8fa;margin:0}}main{{max-width:1500px;margin:auto;padding:32px}}h1{{margin:0 0 8px}}h2{{margin:28px 0 10px}}.lead{{color:#596579}}.summary{{background:#fff;border:1px solid #dfe3e8;border-radius:12px;padding:16px;margin:20px 0}}.note{{background:#fffdf3;border-left:4px solid #c9961a;padding:12px 16px;margin:16px 0}}.table-wrap{{overflow:auto;background:white;border:1px solid #dfe3e8;border-radius:12px}}table{{border-collapse:collapse;width:100%;font-size:14px;white-space:nowrap}}th,td{{padding:9px 10px;border-bottom:1px solid #edf0f2;text-align:left}}th{{position:sticky;top:0;background:#eef2f5;font-weight:650}}tr:hover{{background:#f5f8fb}}footer{{margin-top:20px;color:#6b7280;font-size:13px}}</style></head><body><main><h1>岱明中：今年度SB±3秒帯の全校歴代駅伝実績</h1><p class="lead">2026年度に岱明中所属として登録された岱明中生徒を基準に、全校の過去年度SBから同じ性別・同じ種目で±3.00秒以内の選手を抽出し、その選手が岱明中で走った駅伝区間を突合。</p><div class="summary">{summary}</div><div class="note"><strong>解釈上の注意：</strong>比較対象は過去年度の全校生徒です。トラック種目（800m/1500m/3000m）と駅伝区間は距離・路面・コース・気象・タスキ条件が異なるため、駅伝タイムは予測値ではなく、近いSBを持つ過去選手の実績です。過去SBは年度別SB採用データ、駅伝区間は荒玉駅伝結果データを使用しています。</div>{render_table('男子')}{render_table('女子')}<footer>生成元：INBOX内の2026年度岱明中記録、年度別中学生SB採用データ、荒玉中体連駅伝の年度別結果。生成日：2026-09-11。SB差は「過去SB−今年度SB」。</footer><script>const data={payload};</script></main></body></html>'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(document, encoding="utf-8")
    print(f"wrote {OUT} matches={len(matches)} current={len(current)}")


if __name__ == "__main__":
    main()
