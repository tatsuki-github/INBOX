#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""荒玉中体連駅伝 2026: 区間オーダー×SB予想（なごみ換算＋距離比例＋5ヶ月鮮度）。"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
import generate_nagomi_order_sb_preview as nagomi  # noqa: E402

MEET_DIR = ROOT / "input/external/drive/shared/大会/2026年度/1014-1015_荒玉中体連駅伝"
CORPUS_MEET = ROOT / "input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝"
EVENT_DATE = "2026-10-14"
DEFAULT_AS_OF = "2026-09-27"
SB_FRESHNESS_DAYS = 152
MEN_3000M_FALLBACK_THRESHOLD_SEC = 30.0

# 2024年以降の区間距離（docs/aragyoku-ekiden-distance-definitions.md）
WOMEN_DISTANCES_KM = [3.00, 1.855, 2.00, 2.00, 3.00]
MEN_DISTANCES_KM = [3.00, 2.855, 3.00, 3.00, 2.855, 3.00]

# 区間バイアス秒（実績−予想の中央値）。calibrate_aragyoku_sb_preview.py で更新。
LEG_BIAS_SEC: dict[str, list[float]] = {
    "女子": [20.8, 1.9, -11.2, 7.8, 37.1],
    "男子": [-5.8, 14.4, 9.9, 35.5, 17.7, 15.2],
}

# 監督確定オーダー（公式スタートリスト未着時のシード）
TAIMEI_KNOWN_LEGS: dict[str, dict[int, str]] = {
    "女子": {1: "村上 咲稀", 2: "山﨑 莉奈", 3: "角田 亜美", 4: "増岡 里俐", 5: "高田 麻由"},
    "男子": {1: "松野 凛空", 2: "山本 哲瑠", 3: "今村 昇磨", 4: "田上 颯人"},
}


def predict_leg(
    name: str,
    gender: str,
    distance_km: float,
    sb_index: dict,
    *,
    bias_sec: float = 0.0,
) -> tuple[float | None, dict, str]:
    athlete = sb_index.get(nagomi.norm_name(name))
    marks = athlete.marks if athlete else {}
    details = {d: marks.get(d) for d in ("800m", "1500m", "3000m")}
    if gender == "女子":
        if details["1500m"]:
            base = details["1500m"].seconds * (2 / 1.5) + nagomi.WOMEN_1500_TO_2K_ADD
            note = "1500m SB→2km式を距離比例"
        elif details["800m"]:
            m = details["800m"].seconds
            base = m * (2000 / 800) ** nagomi.RIEGEL * nagomi.WOMEN_800_TO_2K_COEF
            note = "800m SB→2km式を距離比例"
        else:
            return None, details, "記録なし（5ヶ月窓内）"
        pred = base * distance_km / 2 + bias_sec
        if bias_sec:
            note += f"＋区間バイアス{bias_sec:+.0f}s"
        return pred, details, note

    m1500, m800, m3000 = details["1500m"], details["800m"], details["3000m"]
    from_1500 = m1500.seconds * 2 + nagomi.MEN_1500_TO_3K_ADD if m1500 else None
    from_800 = m800.seconds * (3000 / 800) ** nagomi.RIEGEL * nagomi.MEN_800_TO_3K_COEF if m800 else None
    if m3000:
        if from_1500 is not None and m3000.seconds >= from_1500 + MEN_3000M_FALLBACK_THRESHOLD_SEC:
            base, note = from_1500, f"1500m SB→3km式（3000mが+{m3000.seconds - from_1500:.0f}s遅い）"
        elif from_1500 is None and from_800 is not None and m3000.seconds >= from_800 + MEN_3000M_FALLBACK_THRESHOLD_SEC:
            base, note = from_800, "800m SB→3km式（3000mが遅い）"
        else:
            base, note = m3000.seconds, "3000m SBを距離比例"
    elif from_1500 is not None:
        base, note = from_1500, "1500m SB→3km式を距離比例"
    elif from_800 is not None:
        base, note = from_800, "800m SB→3km式を距離比例"
    else:
        return None, details, "記録なし（5ヶ月窓内）"
    pred = base * distance_km / 3 + bias_sec
    if bias_sec:
        note += f"＋区間バイアス{bias_sec:+.0f}s"
    return pred, details, note


def fmt_time(seconds: float | None, decimals: int = 1) -> str:
    if seconds is None:
        return "—"
    total = int(round(seconds * (10**decimals)))
    unit = 10**decimals
    mins, rem = divmod(total, 60 * unit)
    sec, frac = divmod(rem, unit)
    return f"{mins}:{sec:02d}" + (f".{frac:0{decimals}d}" if decimals else "")


def fmt_total(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    total = int(round(seconds))
    mins, sec = divmod(total, 60)
    return f"{mins}:{sec:02d}"


def build_taimei_team(gender: str, sb_index: dict) -> dict:
    distances = WOMEN_DISTANCES_KM if gender == "女子" else MEN_DISTANCES_KM
    known = TAIMEI_KNOWN_LEGS[gender]
    biases = LEG_BIAS_SEC[gender]
    n_legs = len(distances)
    legs: list[str | None] = []
    preds: list[float | None] = []
    details = []
    for i in range(n_legs):
        leg_no = i + 1
        name = known.get(leg_no)
        legs.append(name)
        if not name:
            preds.append(None)
            details.append(
                {
                    "leg": leg_no,
                    "name": "（未決）",
                    "km": distances[i],
                    "pred": None,
                    "marks": {},
                    "note": "オーダー未決",
                }
            )
            continue
        pred, marks, note = predict_leg(
            name, gender, distances[i], sb_index, bias_sec=biases[i] if i < len(biases) else 0.0
        )
        preds.append(pred)
        details.append(
            {
                "leg": leg_no,
                "name": name,
                "km": distances[i],
                "pred": pred,
                "marks": marks,
                "note": note,
            }
        )
    known_n = sum(v is not None for v in preds)
    complete = known_n == n_legs and all(legs)
    total = sum(v for v in preds if v is not None) if complete else None
    return {
        "no": 1,
        "team": "岱明中",
        "legs": legs,
        "preds": preds,
        "details": details,
        "complete": complete,
        "total": total,
        "known_n": known_n,
    }


def mark_text(mark: nagomi.Mark | None) -> str:
    if not mark:
        return "—"
    date = f" @{mark.date}" if mark.date else ""
    return f"{mark.text}{date}"


def render_gender_md(gender: str, team: dict, as_of: str) -> list[str]:
    distances = WOMEN_DISTANCES_KM if gender == "女子" else MEN_DISTANCES_KM
    lines = [
        f"## {gender}",
        "",
        f"区間距離(km): {', '.join(str(d) for d in distances)}",
        "",
        "### 岱明中（シード・公式オーダー未着）",
        "",
        f"- 総合予想（確定区間のみ合算）: **{fmt_total(sum(p for p in team['preds'] if p is not None) if team['known_n'] else None)}**"
        + (" ※未決区間あり" if not team["complete"] else ""),
        f"- SB予想あり区間: {team['known_n']} / {len(distances)}",
        "",
        "| 区 | km | 選手 | SB予想 | 採用SB | 備考 |",
        "| ---: | ---: | --- | --- | --- | --- |",
    ]
    for d in team["details"]:
        marks = d["marks"]
        sb_bits = []
        for dist in ("800m", "1500m", "3000m"):
            m = marks.get(dist) if marks else None
            if m:
                sb_bits.append(f"{dist} {mark_text(m)}")
        lines.append(
            f"| {d['leg']} | {d['km']} | {d['name']} | {fmt_time(d['pred'])} | "
            f"{'; '.join(sb_bits) if sb_bits else '—'} | {d['note']} |"
        )
    lines.append("")
    return lines


def coverage_rows(gender: str, team: dict, as_of: str, freshness: int | None) -> list[dict]:
    rows = []
    for d in team["details"]:
        marks = d["marks"] or {}
        rows.append(
            {
                "gender": gender,
                "team": team["team"],
                "leg": d["leg"],
                "km": d["km"],
                "name": d["name"],
                "pred_sec": "" if d["pred"] is None else round(d["pred"], 1),
                "pred": fmt_time(d["pred"]),
                "sb_800": mark_text(marks.get("800m")),
                "sb_1500": mark_text(marks.get("1500m")),
                "sb_3000": mark_text(marks.get("3000m")),
                "note": d["note"],
                "as_of": as_of,
                "freshness_days": freshness if freshness is not None else "",
            }
        )
    return rows


def write_coverage(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="荒玉駅伝 SB区間予想")
    parser.add_argument("--as-of", default=DEFAULT_AS_OF, help="SB カットオフ日 YYYY-MM-DD")
    parser.add_argument(
        "--freshness-days",
        type=int,
        default=SB_FRESHNESS_DAYS,
        help="SB鮮度窓（日）。0で無効",
    )
    args = parser.parse_args()
    freshness = None if args.freshness_days <= 0 else args.freshness_days

    women_sb, _ = nagomi.load_sb_index(
        as_of=args.as_of, gender="女子", freshness_days=freshness
    )
    men_sb, _ = nagomi.load_sb_index(
        as_of=args.as_of, gender="男子", freshness_days=freshness
    )
    women = build_taimei_team("女子", women_sb)
    men = build_taimei_team("男子", men_sb)

    header = [
        "# 荒玉中体連駅伝 2026年度SB・区間予想（暫定・岱明シード）",
        "",
        f"as_of: {args.as_of} / event_date: {EVENT_DATE} / freshness_days: {freshness}",
        "",
        "## 算出方法",
        "",
        "- SBは2026年度採用SB・Notion・玉名郡ナイター（SB明記）のうち、as_of以前かつ freshness_days 以内の記録のみ。",
        "- 換算式はなごみ駅伝と同じ（女1500→2km `×(2/1.5)+15`、男1500→3km `×2+35`）。距離比例で荒玉区間kmへ。",
        "- 男子3000m閾値は30秒（ジュニア踏襲）。区間バイアスは `calibrate_aragyoku_sb_preview.py` の LEG_BIAS_SEC を適用。",
        "- 岱明は監督確定オーダーのみ。男子5–6区は未決のため空欄。他校は公式オーダー到着後に追加。",
        "- ジュニア直近フォーム・校別展開は [校別展開予想.md](校別展開予想.md) / ジュニア結果抜粋を参照。",
        "",
    ]
    lines = header + render_gender_md("女子", women, args.as_of) + render_gender_md("男子", men, args.as_of)
    rows = coverage_rows("女子", women, args.as_of, freshness) + coverage_rows(
        "男子", men, args.as_of, freshness
    )

    for out_dir in (MEET_DIR, CORPUS_MEET):
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / "区間オーダー_SB予想.md"
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        write_coverage(out_dir / "区間オーダー_SB予想_coverage.csv", rows)
        print(f"wrote {md_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
