#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""800m/1500m SBから駅伝区間タイムを90%上限で予測するHTMLを作る。"""
from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SB_DIR = ROOT / "input/external/sb/middle-school/by-year"
EKIDEN_DIR = ROOT / "input/aragyoku/transcripts"
OUT_DIR = ROOT / "out/analysis/ekiden-prediction"

EVENT_DISTANCE = {"800m": 800.0, "1500m": 1500.0}
RIEGEL_EXPONENT = 1.06


def norm(v: object) -> str:
    return str(v or "").replace(" ", "").replace("　", "")


def sec(v: object) -> float | None:
    if v in (None, "", "—", "-"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        m = re.fullmatch(r"(\d+):(\d{2})(?:\.(\d+))?", str(v).strip())
        if not m:
            return None
        return int(m.group(1)) * 60 + int(m.group(2)) + float("0." + (m.group(3) or "0"))


def fmt(v: float) -> str:
    m, s = divmod(v, 60)
    return f"{int(m)}:{s:05.2f}"


def quantile(values: list[float], q: float) -> float:
    values = sorted(values)
    pos = (len(values) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def load_sb() -> dict[tuple[int, str, str, str], list[dict]]:
    out = {}
    for p in sorted(SB_DIR.glob("*-sb-adopted.json")):
        if not p.stem[:4].isdigit():
            continue
        year = int(p.stem[:4])
        for r in json.loads(p.read_text()):
            event = r.get("距離")
            value = sec(r.get("SB秒") or r.get("SB"))
            if event not in EVENT_DISTANCE or value is None:
                continue
            key = (year, r.get("性別", ""), norm(r.get("名前")), event)
            out.setdefault(key, []).append({"name": r.get("名前"), "school": r.get("所属"), "sb": value})
    return out


def load_ekiden() -> dict[tuple[int, str, str], list[dict]]:
    out = {}
    for p in sorted(EKIDEN_DIR.glob("*.json")):
        m = re.fullmatch(r"(\d+)-(男子|女子)\.json", p.name)
        if not m:
            continue
        year, gender = int(m.group(1)), m.group(2)
        data = json.loads(p.read_text())
        distance_by_leg = {x["leg"]: x["distance_km"] for x in data.get("legs", [])}
        for team in data.get("teams", []):
            for leg in team.get("legs", []):
                leg_no = leg.get("leg")
                distance = distance_by_leg.get(leg_no)
                value = sec(leg.get("split"))
                if distance is None or value is None:
                    continue
                key = (year, gender, norm(leg.get("name")))
                out.setdefault(key, []).append({"team": team.get("team"), "leg": leg_no, "distance": distance, "time": value, "rank": leg.get("split_rank"), "team_rank": team.get("rank")})
    return out


def build_rows(event: str, gender: str, sb: dict, ekiden: dict) -> list[dict]:
    rows = []
    for (year, g, name, e), records in sb.items():
        if g != gender or e != event or year >= 2026:
            continue
        for r in records:
            for leg in ekiden.get((year, gender, name), []):
                baseline = r["sb"] * (leg["distance"] * 1000 / EVENT_DISTANCE[event]) ** RIEGEL_EXPONENT
                rows.append({**r, **leg, "year": year, "baseline": baseline, "ratio": leg["time"] / baseline})
    return rows


def make_html(event: str, gender: str, rows: list[dict], out: Path) -> None:
    by_distance = {}
    for r in rows:
        if event == "1500m":
            r["simple_base"] = r["sb"] * r["distance"] * 1000 / 1500
            by_distance.setdefault(r["distance"], []).append(r["time"] - r["simple_base"])
        else:
            by_distance.setdefault(r["distance"], []).append(r["ratio"])
    coeff = {d: quantile(vals, 0.8) for d, vals in by_distance.items()}
    summary = f"{gender} / {event} / 突合 {len(rows)}件 / 区間 {len(coeff)}種類"
    formulas = []
    for d in sorted(coeff):
        n = len(by_distance[d])
        if event == "1500m":
            formula = f"予測秒 = SB秒 × ({d:g}km ÷ 1.5km) + {coeff[d]:.2f}秒"
            value = f"{coeff[d]:.2f}秒"
        else:
            formula = f"予測秒 = SB秒 × ({d:g}km ÷ {EVENT_DISTANCE[event]:g}m)^{RIEGEL_EXPONENT:.2f} × {coeff[d]:.4f}"
            value = f"{coeff[d]:.4f}"
        formulas.append(f"<tr><td>{d:g}km</td><td>{n}</td><td>{value}</td><td>{formula}</td></tr>")
    examples = []
    for sb_sec in [120.0, 150.0, 180.0, 270.0, 300.0]:
        for d in sorted(coeff):
            if event == "1500m":
                pred = sb_sec * d * 1000 / 1500 + coeff[d]
            else:
                pred = sb_sec * (d * 1000 / EVENT_DISTANCE[event]) ** RIEGEL_EXPONENT * coeff[d]
            examples.append(f"<tr><td>{fmt(sb_sec)}</td><td>{d:g}km</td><td>{fmt(pred)}</td></tr>")
    detail = []
    for r in sorted(rows, key=lambda x: (x["distance"], x["year"], x["name"])):
        pred = r["simple_base"] + coeff[r["distance"]] if event == "1500m" else r["baseline"] * coeff[r["distance"]]
        detail.append("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in [r["year"], r["name"], r["school"], fmt(r["sb"]), f"{r['distance']:g}km", f"{r['leg']}区", fmt(r["time"]), fmt(pred), f"{r['time']-pred:+.1f}"]) + "</tr>")
    if event == "1500m":
        formula_text = "予測秒 = SB秒 × (駅伝距離 ÷ 1500m) + X秒"
    else:
        formula_text = f"予測秒 = SB秒 × (駅伝距離 ÷ {EVENT_DISTANCE[event]:g}m)^{RIEGEL_EXPONENT:.2f} × 区間係数"
    doc = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{gender} {event} 駅伝予測式</title><style>body{{font-family:system-ui,-apple-system,sans-serif;background:#f7f8fa;color:#1f2937;margin:0}}main{{max-width:1400px;margin:auto;padding:32px}}h1{{margin-bottom:8px}}h2{{margin-top:28px}}.summary,.note,.formula{{background:white;border:1px solid #dfe3e8;border-radius:12px;padding:16px;margin:16px 0}}.note{{background:#fffdf3;border-left:4px solid #c9961a}}table{{border-collapse:collapse;width:100%;background:white;white-space:nowrap;font-size:14px}}th,td{{padding:8px 10px;border-bottom:1px solid #edf0f2;text-align:left}}th{{background:#eef2f5;position:sticky;top:0}}.wrap{{overflow:auto;border:1px solid #dfe3e8;border-radius:12px}}code{{font-size:1.05em}}</style></head><body><main><h1>{gender} {event}：駅伝区間予測式</h1><p>{summary}</p><div class="note"><strong>80%設定：</strong>過去実績の残差または比率の80パーセンタイルを採用し、過去データの約80%が予測タイム以内に収まる設定です。</div><div class="formula"><code>{formula_text}</code><br>※駅伝距離は、男子3km/2.855km、女子3km/1.855km/2kmの区分で計算。</div><h2>区間別係数</h2><div class="wrap"><table><thead><tr><th>駅伝距離</th><th>サンプル数</th><th>{'X秒（80%残差）' if event == '1500m' else '80%係数'}</th><th>式</th></tr></thead><tbody>{''.join(formulas)}</tbody></table></div><h2>計算例</h2><div class="wrap"><table><thead><tr><th>SB</th><th>駅伝距離</th><th>予測タイム</th></tr></thead><tbody>{''.join(examples)}</tbody></table></div><h2>突合データ</h2><div class="wrap"><table><thead><tr><th>年度</th><th>選手</th><th>所属</th><th>{event} SB</th><th>駅伝距離</th><th>区間</th><th>実績</th><th>80%予測</th><th>実績−予測</th></tr></thead><tbody>{''.join(detail)}</tbody></table></div><p>注：トラックSBと駅伝は路面・コース・気象・タスキ条件が異なります。係数はこのリポジトリ内の過去データに基づく目安です。</p></main></body></html>'''
    out.write_text(doc, encoding="utf-8")


def main() -> None:
    sb, ekiden = load_sb(), load_ekiden()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for gender in ("男子", "女子"):
        for event in ("800m", "1500m"):
            path = OUT_DIR / f"{gender}_{event}_prediction.html"
            rows = build_rows(event, gender, sb, ekiden)
            make_html(event, gender, rows, path)
            print(path, len(rows))


if __name__ == "__main__":
    main()
