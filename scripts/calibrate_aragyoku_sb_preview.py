#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""荒玉駅伝: 歴代結果×当時SBで区間バイアス（実績−予想）を推定する。"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
import generate_aragyoku_ekiden_sb_preview as aragyoku  # noqa: E402
import generate_nagomi_order_sb_preview as nagomi  # noqa: E402

TRANSCRIPT_DIR = ROOT / "input/aragyoku/transcripts"
SB_DIR = ROOT / "input/external/sb/middle-school/by-year"
OUT_MD = ROOT / "out/analysis/aragyoku_sb_calibration.md"
OUT_JSON = ROOT / "out/analysis/aragyoku_sb_calibration.json"
YEARS = (2024, 2025)
FRESHNESS_DAYS = 152


def event_as_of(year: int) -> str:
    # 荒玉は例年10月中旬。transcript の date があれば前日を使う。
    path = TRANSCRIPT_DIR / f"{year}-男子.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    date = str(data.get("date") or f"{year}-10-15")
    y, m, d = (int(x) for x in date.replace("/", "-").split("-"))
    from datetime import date as date_cls, timedelta

    return (date_cls(y, m, d) - timedelta(days=1)).isoformat()


def load_year_sb(year: int, gender: str, as_of: str) -> dict:
    path = SB_DIR / f"{year}-sb-adopted.json"
    return nagomi.load_sb_index(
        sb_path=path,
        as_of=as_of,
        include_notion=False,
        include_nighter=False,
        gender=gender,
        freshness_days=FRESHNESS_DAYS,
    )[0]


def calibrate_year(year: int) -> dict:
    as_of = event_as_of(year)
    result: dict = {"year": year, "as_of": as_of, "genders": {}}
    for gender in ("男子", "女子"):
        path = TRANSCRIPT_DIR / f"{year}-{gender}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("legs"):
            distances = [float(x["distance_km"]) for x in data["legs"]]
        elif gender == "女子":
            distances = list(aragyoku.WOMEN_DISTANCES_KM)
        else:
            # 2024以降定義。2023以前は別テーブルだが本キャリブは2024–2025のみ。
            distances = list(aragyoku.MEN_DISTANCES_KM)
        sb_index = load_year_sb(year, gender, as_of)
        gaps: dict[int, list[float]] = defaultdict(list)
        matched = 0
        for team in data.get("teams", []):
            for leg in team.get("legs", []):
                if leg.get("status") not in (None, "ok", ""):
                    continue
                name = leg.get("name") or ""
                split = nagomi.parse_seconds(leg.get("split"))
                leg_no = int(leg.get("leg") or 0)
                if not name or split is None or not (1 <= leg_no <= len(distances)):
                    continue
                pred, _, _ = aragyoku.predict_leg(
                    name, gender, distances[leg_no - 1], sb_index, bias_sec=0.0
                )
                if pred is None:
                    continue
                gaps[leg_no].append(split - pred)
                matched += 1
        leg_stats = {}
        for leg_no, vals in sorted(gaps.items()):
            leg_stats[leg_no] = {
                "n": len(vals),
                "median_gap_sec": round(median(vals), 1),
                "mean_gap_sec": round(mean(vals), 1),
                "mae_sec": round(mean(abs(v) for v in vals), 1),
            }
        result["genders"][gender] = {
            "matched_legs": matched,
            "distances_km": distances,
            "legs": leg_stats,
        }
    return result


def aggregate_bias(year_results: list[dict]) -> dict[str, list[float]]:
    """性別×区間の中央値ギャップをバイアス初期値にする（正＝予想が楽観＝遅め補正）。"""
    buckets: dict[tuple[str, int], list[float]] = defaultdict(list)
    for yr in year_results:
        for gender, g in yr["genders"].items():
            for leg_s, st in g["legs"].items():
                buckets[(gender, int(leg_s))].append(st["median_gap_sec"])
    out: dict[str, list[float]] = {"女子": [0.0] * 5, "男子": [0.0] * 6}
    for (gender, leg), vals in buckets.items():
        idx = leg - 1
        if 0 <= idx < len(out[gender]):
            out[gender][idx] = round(median(vals), 1)
    return out


def junior_2026_sanity() -> list[str]:
    """ジュニア2026岱明予実の sanity note（女子スタミナ）。"""
    return [
        "## ジュニア2026 sanity（岱明）",
        "",
        "- 女子CS: 実績36:52 / SB予想34:54 → 総合約+118秒。中盤3人が約9分帯。",
        "- 男子CS: 実績44:23 / SB予想44:22 → ほぼ一致。",
        "- 荒玉女子1・5区（3km）はジュニアより長いため、歴代中央値バイアスに加え女子長距離区間は楽観に注意。",
        "- 男子は過大な遅延補正を掛けない（ジュニアが示す通り）。",
        "",
    ]


def render_md(year_results: list[dict], bias: dict[str, list[float]]) -> str:
    lines = [
        "# 荒玉駅伝 SB 区間キャリブレーション",
        "",
        f"対象年: {', '.join(str(y['year']) for y in year_results)}",
        f"鮮度窓: {FRESHNESS_DAYS}日 / Notion・ナイターは履歴年では未使用",
        "",
        "## 推奨区間バイアス秒（実績−予想の中央値）",
        "",
        "正の値＝予想が速すぎた（遅めに補正）。`generate_aragyoku_ekiden_sb_preview.LEG_BIAS_SEC` に反映。",
        "",
    ]
    for gender, vals in bias.items():
        lines.append(f"- **{gender}**: {vals}")
    lines.append("")
    for yr in year_results:
        lines += [f"## {yr['year']}（as_of {yr['as_of']}）", ""]
        for gender, g in yr["genders"].items():
            lines += [
                f"### {gender}（照合区間 {g['matched_legs']}）",
                "",
                "| 区 | km | n | 中央値ギャップ秒 | 平均ギャップ秒 | MAE秒 |",
                "| ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
            for leg, st in sorted(g["legs"].items(), key=lambda x: int(x[0])):
                km = g["distances_km"][int(leg) - 1] if int(leg) <= len(g["distances_km"]) else ""
                lines.append(
                    f"| {leg} | {km} | {st['n']} | {st['median_gap_sec']} | {st['mean_gap_sec']} | {st['mae_sec']} |"
                )
            lines.append("")
    lines += junior_2026_sanity()
    return "\n".join(lines) + "\n"


def main() -> int:
    year_results = [calibrate_year(y) for y in YEARS]
    bias = aggregate_bias(year_results)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    payload = {"years": year_results, "recommended_leg_bias_sec": bias, "freshness_days": FRESHNESS_DAYS}
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_md(year_results, bias), encoding="utf-8")

    # 生成スクリプトのバイアスを同期
    aragyoku_path = ROOT / "scripts/generate_aragyoku_ekiden_sb_preview.py"
    text = aragyoku_path.read_text(encoding="utf-8")
    import re

    new_block = (
        "LEG_BIAS_SEC: dict[str, list[float]] = {\n"
        f'    "女子": {bias["女子"]},\n'
        f'    "男子": {bias["男子"]},\n'
        "}"
    )
    text2, n = re.subn(
        r"LEG_BIAS_SEC: dict\[str, list\[float\]\] = \{.*?\n\}",
        new_block,
        text,
        count=1,
        flags=re.S,
    )
    if n:
        aragyoku_path.write_text(text2, encoding="utf-8")
        print(f"updated LEG_BIAS_SEC in {aragyoku_path}")
    print(f"wrote {OUT_MD}")
    print(f"wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
