#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""なごみ駅伝 区間オーダーに今年度SB・区間予想・総合順位を付けた MD / PDF を生成する。

予測式（なごみ運用）:
- 男子 3km: 1500m SB × 2 + 35秒（掛け算＋加算。従来HTMLの+68.50 / 一時+40から変更）
  800m フォールバック: SB × (3000/800)^1.06 × 1.1341
- 女子 2km: 1500m SB × (2/1.5) + 15秒（男子と同型の掛け算＋加算）
  800m フォールバック: SB のみのとき SB × (2000/800)^1.06 × 1.1142

男子 3km 予想の 3000m SB 扱い:
- 3000m SB があり、かつ 1500m 換算予想より THRESHOLD_SEC 以上遅い場合は
  1500m 換算予想を採用（ユーザー指定）。

女子は 1500m がある限り掛け算＋加算を優先（800換算で上書きしない）。

SB ソース:
- 2026-sb-adopted.json / Notion（SB採用優先）
- 玉名郡ナイター（2026-08-29）は、岱明メモ等で SB 明記された記録のみ
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
MEET_DIR = (
    ROOT
    / "input/external/drive/shared/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会"
)
CORPUS_MEET = (
    ROOT
    / "input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会"
)
SB_ADOPTED = ROOT / "input/external/sb/middle-school/by-year/2026-sb-adopted.json"
NOTION_ROWS = ROOT / "input/external/notion/databases/2026年度中学生記録/rows.json"
TAMANA_NIGHTER_DIR = (
    ROOT / "input/external/drive/shared/大会/2026年度/0829_玉名郡ナイター中・長距離記録会"
)
TAMANA_NIGHTER_FULL_MD = TAMANA_NIGHTER_DIR / "全結果.md"
TAMANA_NIGHTER_DAIMYO_MD = TAMANA_NIGHTER_DIR / "岱明の結果.md"
OUT_DIR = MEET_DIR
FONT_PATH = ROOT / "assets/fonts/NotoSansJP-Regular.ttf"

# 男子3km: ×2+35。女子2km: ×(2/1.5)+15
MEN_1500_TO_3K_ADD = 35.0
MEN_800_TO_3K_COEF = 1.1341
WOMEN_1500_TO_2K_ADD = 15.0
WOMEN_800_TO_2K_COEF = 1.1142
RIEGEL = 1.06
# 3000m SB が 1500 換算よりこの秒数以上遅い → 1500 換算を採用
THRESHOLD_SEC = 20.0


def norm_name(name: str) -> str:
    s = str(name or "")
    for a, b in (
        (" ", ""),
        ("　", ""),
        ("﨑", "崎"),
        ("邊", "邉"),
        ("髙", "高"),
        ("濵", "濱"),
        ("凜", "凛"),
        ("瀨", "瀬"),
        ("﨑", "崎"),
    ):
        s = s.replace(a, b)
    return s


def parse_seconds(v: object) -> float | None:
    if v in (None, "", "—", "-"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        pass
    m = re.fullmatch(r"(\d+):(\d{2})(?:\.(\d+))?", str(v).strip())
    if not m:
        return None
    frac = float("0." + m.group(3)) if m.group(3) else 0.0
    return int(m.group(1)) * 60 + int(m.group(2)) + frac


def fmt_time(sec: float | None, places: int = 2) -> str:
    if sec is None:
        return ""
    if sec < 0:
        return ""
    m, s = divmod(sec, 60)
    if places == 0:
        return f"{int(m)}:{int(round(s)):02d}"
    return f"{int(m)}:{s:0{places + 3}.{places}f}"


def fmt_clock(sec: float | None) -> str:
    """総合タイム用（秒は整数寄り）。"""
    if sec is None:
        return ""
    total = int(round(sec))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


@dataclass
class Mark:
    seconds: float
    text: str
    url: str = ""
    date: str = ""
    source: str = ""


@dataclass
class AthleteSB:
    name: str
    marks: dict[str, Mark] = field(default_factory=dict)  # distance -> best


_NIGHTER_SECTION = re.compile(r"^(?:##\s*)?(800m|1500m|3000m)\s*(男子|女子)?\s*$")
_NIGHTER_ROW_DAIMYO = re.compile(
    r"^(.+?)\s+\d年\s+(\d+:\d{1,2}(?:\.\d+)?)\b"
)
_NIGHTER_ROW_TABLE = re.compile(
    r"^\|\s*(.+?)\s*\|\s*.+?\s*\|\s*.+?\s*\|\s*(\d+:\d{1,2}(?:\.\d+)?)\s*\|"
)


def iter_tamana_nighter_marks(gender: str | None = None) -> list[tuple[str, str, str]]:
    """SB 明記されたナイター記録だけを返す。

    `全結果.md` はタイムの一覧であって SB 判定を含まないため、そのまま
    SB として取り込まない。SB 明記を含む岱明メモを併読し、男女セクション
    がある場合は指定 gender に絞る。
    """
    paths = [p for p in (TAMANA_NIGHTER_FULL_MD, TAMANA_NIGHTER_DAIMYO_MD) if p.exists()]
    out: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for path in paths:
        distance: str | None = None
        section_gender: str | None = None
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith(
                ("大会", "日付", "ステータス", "場所", "タグ", "集合", "所属", "ソース", "中学生", "| ---", "| 氏名")
            ):
                continue
            sec_m = _NIGHTER_SECTION.match(line)
            if sec_m:
                distance = sec_m.group(1)
                section_gender = sec_m.group(2)
                continue
            if distance is None or "DNS" in line or not re.search(r"(?:^|\s)SB(?:\s|$)", line):
                continue
            if gender and section_gender and section_gender != gender:
                continue
            table_m = _NIGHTER_ROW_TABLE.match(line)
            if table_m:
                row = (table_m.group(1).strip(), distance, table_m.group(2))
            else:
                row_m = _NIGHTER_ROW_DAIMYO.match(line)
                if not row_m:
                    continue
                row = (row_m.group(1).strip(), distance, row_m.group(2))
            if row not in seen:
                seen.add(row)
                out.append(row)
    return out


def apply_tamana_nighter_sb(
    by_name: dict[str, AthleteSB], upsert, *, gender: str | None = None
) -> list[str]:
    """SB 明記された玉名郡ナイター記録を、既存より速い場合だけ取り込む。"""
    date = "2026-08-29"
    updates: list[str] = []
    for name, distance, mark_text in iter_tamana_nighter_marks(gender=gender):
        sec = parse_seconds(mark_text)
        if sec is None:
            continue
        key = norm_name(name)
        before = by_name.get(key).marks.get(distance) if key in by_name else None
        before_sec = before.seconds if before else None
        upsert(name, distance, sec, mark_text, "", date, "tamana-nighter-2026")
        after = by_name[key].marks.get(distance) if key in by_name else None
        if after and after.source == "tamana-nighter-2026" and (
            before_sec is None or after.seconds < before_sec - 1e-9
        ):
            updates.append(
                f"{name} {distance}: "
                f"{before.text if before else '—'} → {after.text}"
            )
    return updates


def date_on_or_before(date_text: str, as_of: str | None) -> bool:
    """SB 行の日付が as_of（YYYY-MM-DD / YYYY/MM/DD）以前か。日付欠落は採用する。"""
    if not as_of:
        return True
    raw = str(date_text or "").strip().replace("-", "/")
    if not raw:
        return True
    return raw <= str(as_of).strip().replace("-", "/")


def load_sb_index(
    sb_path: Path | None = None,
    *,
    as_of: str | None = None,
    include_notion: bool = True,
    include_nighter: bool = True,
    gender: str | None = None,
) -> tuple[dict[str, AthleteSB], list[str]]:
    """正規化氏名 → AthleteSB（距離ごとのベスト）。ナイター更新ログも返す。

    as_of を指定すると、その日以前の記録だけを使う（レース前の公平な予想用）。
    gender は「男子」「女子」。指定時は性別が一致する行だけ採用する。
    """
    by_name: dict[str, AthleteSB] = {}
    adopted_path = sb_path if sb_path is not None else SB_ADOPTED

    def upsert(name: str, distance: str, seconds: float, text: str, url: str, date: str, source: str) -> None:
        if distance not in ("800m", "1500m", "3000m") or seconds is None:
            return
        key = norm_name(name)
        if not key:
            return
        ath = by_name.setdefault(key, AthleteSB(name=name))
        cur = ath.marks.get(distance)
        if cur is None or seconds < cur.seconds:
            ath.marks[distance] = Mark(seconds=seconds, text=text, url=url or "", date=date or "", source=source)

    # 1) SB adopted JSON（SB採用のみ優先的に、ただし秒は SB秒）
    if adopted_path.exists():
        for r in json.loads(adopted_path.read_text(encoding="utf-8")):
            if r.get("SB採用") not in ("__YES__", True, "true", "TRUE", "yes"):
                continue
            if gender and str(r.get("性別") or "") not in ("", gender):
                continue
            if not date_on_or_before(str(r.get("日付") or ""), as_of):
                continue
            sec = parse_seconds(r.get("SB秒") or r.get("SB") or r.get("記録秒"))
            if sec is None:
                continue
            text = str(r.get("SB") or r.get("記録") or fmt_time(sec))
            upsert(
                str(r.get("名前") or ""),
                str(r.get("距離") or ""),
                sec,
                text,
                str(r.get("参考") or ""),
                str(r.get("日付") or ""),
                "sb-adopted",
            )

    # 2) Notion rows（sb_adopted 優先、なければ同距離の最速を後で埋める）
    if include_notion and NOTION_ROWS.exists():
        # first pass: sb_adopted
        for r in json.loads(NOTION_ROWS.read_text(encoding="utf-8")):
            if gender and str(r.get("gender") or r.get("性別") or "") not in ("", gender):
                continue
            if not date_on_or_before(str(r.get("date") or r.get("日付") or ""), as_of):
                continue
            sec = parse_seconds(r.get("sb_text") or r.get("record_seconds") or r.get("time_text"))
            if sec is None:
                continue
            if not r.get("sb_adopted"):
                continue
            text = str(r.get("sb_text") or r.get("time_text") or fmt_time(sec))
            upsert(
                str(r.get("name") or ""),
                str(r.get("distance") or ""),
                sec,
                text,
                str(r.get("url") or ""),
                str(r.get("date") or ""),
                "notion-sb",
            )
        # second pass: fill missing distances with best mark
        for r in json.loads(NOTION_ROWS.read_text(encoding="utf-8")):
            if gender and str(r.get("gender") or r.get("性別") or "") not in ("", gender):
                continue
            if not date_on_or_before(str(r.get("date") or r.get("日付") or ""), as_of):
                continue
            name = str(r.get("name") or "")
            distance = str(r.get("distance") or "")
            key = norm_name(name)
            ath = by_name.get(key)
            if ath and distance in ath.marks:
                continue
            sec = parse_seconds(r.get("record_seconds") or r.get("time_text") or r.get("sb_text"))
            if sec is None:
                continue
            text = str(r.get("time_text") or r.get("sb_text") or fmt_time(sec))
            upsert(name, distance, sec, text, str(r.get("url") or ""), str(r.get("date") or ""), "notion-best")

    # 3) 玉名郡ナイター（2026-08-29）— SB明記かつ既存SBより速いときだけ上書き
    nighter_updates: list[str] = []
    if include_nighter:
        nighter_updates = apply_tamana_nighter_sb(by_name, upsert, gender=gender)

    return by_name, nighter_updates


def parse_order_md(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\| \d+ \|", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 9:
            continue
        no = int(cells[0])
        team = cells[1]
        legs = cells[2:6]
        reserves = cells[6:9]
        rows.append({"no": no, "team": team, "legs": legs, "reserves": reserves})
    return rows


def link_md(text: str, url: str) -> str:
    if not text:
        return ""
    if not url:
        return text
    return f"[{text}]({url})"


def predict_men_3k(marks: dict[str, Mark]) -> tuple[float | None, str]:
    m1500 = marks.get("1500m")
    m800 = marks.get("800m")
    m3000 = marks.get("3000m")
    from_1500 = m1500.seconds * 2 + MEN_1500_TO_3K_ADD if m1500 else None
    from_800 = (
        m800.seconds * (3000 / 800) ** RIEGEL * MEN_800_TO_3K_COEF if m800 else None
    )
    track_from_1500 = m1500.seconds * 2 + 30 if m1500 else None  # arato_tamana 換算

    if m3000 and from_1500 is not None:
        if m3000.seconds > from_1500 + THRESHOLD_SEC:
            return from_1500, f"1500換算採用（3000mSBが+{m3000.seconds - from_1500:.0f}s遅い）"
        return m3000.seconds, "3000m SB"
    if m3000 and from_1500 is None:
        # 1500 無し: 3000 と 800 換算を比較
        if from_800 is not None and m3000.seconds > from_800 + THRESHOLD_SEC:
            return from_800, f"800換算採用（3000mSBが遅い）"
        return m3000.seconds, "3000m SB"
    if from_1500 is not None:
        return from_1500, "1500→3km式"
    if from_800 is not None:
        return from_800, "800→3km式"
    return None, "記録なし"


def predict_women_2k(marks: dict[str, Mark]) -> tuple[float | None, str]:
    """1500 があれば掛け算＋加算を優先。800 は 1500 欠測時のみ。"""
    m1500 = marks.get("1500m")
    m800 = marks.get("800m")
    if m1500:
        return (
            m1500.seconds * (2 / 1.5) + WOMEN_1500_TO_2K_ADD,
            "1500→2km式",
        )
    if m800:
        return (
            m800.seconds * (2000 / 800) ** RIEGEL * WOMEN_800_TO_2K_COEF,
            "800→2km式",
        )
    return None, "記録なし"


def md_mark(m: Mark | None) -> str:
    if not m:
        return ""
    return link_md(m.text, m.url)


def build_gender_report(
    gender: str,
    order_rows: list[dict[str, Any]],
    sb_index: dict[str, AthleteSB],
) -> dict[str, Any]:
    is_men = gender == "男子"
    leg_label = "3km予想" if is_men else "2km予想"
    distances = ("800m", "1500m", "3000m") if is_men else ("800m", "1500m")

    teams_out: list[dict[str, Any]] = []
    for row in order_rows:
        leg_preds: list[float | None] = []
        leg_details: list[dict[str, Any]] = []
        for i, name in enumerate(row["legs"], start=1):
            ath = sb_index.get(norm_name(name)) if name else None
            marks = ath.marks if ath else {}
            if is_men:
                pred, note = predict_men_3k(marks)
            else:
                pred, note = predict_women_2k(marks)
            leg_preds.append(pred)
            leg_details.append(
                {
                    "leg": i,
                    "name": name,
                    "marks": {d: marks.get(d) for d in distances},
                    "pred": pred,
                    "note": note if name else "",
                }
            )
        reserves = []
        for name in row["reserves"]:
            if not name:
                continue
            ath = sb_index.get(norm_name(name))
            marks = ath.marks if ath else {}
            if is_men:
                pred, note = predict_men_3k(marks)
            else:
                pred, note = predict_women_2k(marks)
            reserves.append(
                {
                    "name": name,
                    "marks": {d: marks.get(d) for d in distances},
                    "pred": pred,
                    "note": note,
                }
            )
        complete = all(p is not None for p in leg_preds) and all(row["legs"])
        total = sum(p for p in leg_preds if p is not None) if complete else None
        teams_out.append(
            {
                "no": row["no"],
                "team": row["team"],
                "legs": leg_details,
                "reserves": reserves,
                "total": total,
                "complete": complete,
                "leg_preds": leg_preds,
            }
        )

    ranked_complete = sorted(
        [t for t in teams_out if t["complete"] and t["total"] is not None],
        key=lambda t: t["total"],
    )

    # 参考順位: 欠測区間は同性別の既知予想の中央値で補完
    known = [
        det["pred"]
        for t in teams_out
        for det in t["legs"]
        if det["pred"] is not None
    ]
    known_sorted = sorted(known)
    median = known_sorted[len(known_sorted) // 2] if known_sorted else None
    for t in teams_out:
        if not any(t["legs"][i]["name"] for i in range(4)):
            t["total_ref"] = None
            t["imputed"] = False
            continue
        parts: list[float] = []
        imputed = False
        real_n = 0
        for det in t["legs"]:
            if not det["name"]:
                # 空オーダー（未記入）は補完せず対象外
                parts = []
                imputed = False
                break
            if det["pred"] is not None:
                parts.append(det["pred"])
                real_n += 1
            elif median is not None:
                parts.append(median)
                imputed = True
            else:
                parts = []
                break
        # 実記録由来の予想が2区間未満なら参考順位から除外（中央値だけのチームを避ける）
        if len(parts) == 4 and real_n >= 2:
            t["total_ref"] = sum(parts)
            t["imputed"] = imputed
            t["real_legs"] = real_n
        else:
            t["total_ref"] = None
            t["imputed"] = False
            t["real_legs"] = real_n if parts else 0

    ranked_ref = sorted(
        [t for t in teams_out if t.get("total_ref") is not None],
        key=lambda t: t["total_ref"],
    )
    for i, t in enumerate(ranked_ref, start=1):
        t["rank_ref"] = i
    for t in teams_out:
        t["rank"] = next(
            (i + 1 for i, x in enumerate(ranked_complete) if x is t),
            None,
        )

    attach_predicted_leg_ranks(ranked_ref, median, field_suffix="")
    attach_predicted_leg_ranks(
        ranked_complete, median=None, complete_only=True, field_suffix="_full"
    )

    return {
        "gender": gender,
        "leg_label": leg_label,
        "distances": distances,
        "teams": teams_out,
        "ranked": ranked_complete,
        "ranked_ref": ranked_ref,
        "median_fill": median,
    }


def attach_predicted_leg_ranks(
    teams: list[dict[str, Any]],
    median: float | None,
    *,
    complete_only: bool = False,
    field_suffix: str = "",
) -> None:
    """対象チーム間で、各区の予想区間順位・通過順位を付ける。

    complete_only=True のときは実SB由来の予想のみ（中央値補完なし）。
    field_suffix で参考順位用（""）と完全記録用（"_full"）を分離する。
    """
    if not teams:
        return
    suf = field_suffix
    usable: list[dict[str, Any]] = []
    for t in teams:
        parts: list[float] = []
        ok = True
        for det in t["legs"]:
            if complete_only:
                if det["pred"] is None:
                    ok = False
                    break
                parts.append(det["pred"])
            else:
                if det["pred"] is not None:
                    parts.append(det["pred"])
                elif median is not None and det.get("name"):
                    parts.append(median)
                else:
                    ok = False
                    break
        if not ok or len(parts) != 4:
            continue
        cum = 0.0
        for det, sec in zip(t["legs"], parts):
            cum += sec
            det[f"pred_used{suf}"] = sec
            det[f"pred_cum{suf}"] = cum
            det[f"pred_imputed_leg{suf}"] = det["pred"] is None
        usable.append(t)

    for leg_i in range(4):
        by_sec = sorted(usable, key=lambda t: t["legs"][leg_i][f"pred_used{suf}"])
        for rank, t in enumerate(by_sec, start=1):
            t["legs"][leg_i][f"pred_sec_rank{suf}"] = rank
        by_cum = sorted(usable, key=lambda t: t["legs"][leg_i][f"pred_cum{suf}"])
        for rank, t in enumerate(by_cum, start=1):
            t["legs"][leg_i][f"pred_cum_rank{suf}"] = rank


def fmt_leg_pred_cell(det: dict[str, Any], *, places: int = 1, field_suffix: str = "") -> str:
    """(通過順)通過タイム / (区間順)区間記録。補完区間の区間記録は括弧付き。"""
    suf = field_suffix
    sec = det.get(f"pred_used{suf}")
    if sec is None:
        if det.get("pred") is not None:
            return fmt_time(det["pred"], places)
        return ""
    cum = det.get(f"pred_cum{suf}")
    sec_r = det.get(f"pred_sec_rank{suf}")
    cum_r = det.get(f"pred_cum_rank{suf}")
    sec_s = fmt_time(sec, places)
    if det.get(f"pred_imputed_leg{suf}"):
        sec_s = f"({sec_s})"
    cum_s = fmt_time(cum, places) if cum is not None else ""
    if cum_r is not None and sec_r is not None and cum_s:
        return f"({cum_r}){cum_s} / ({sec_r}){sec_s}"
    if sec_r is not None:
        return f"({sec_r}){sec_s}"
    return sec_s


def render_markdown(report: dict[str, Any]) -> str:
    g = report["gender"]
    leg_label = report["leg_label"]
    distances = report["distances"]
    year = int(report.get("year") or 2026)
    as_of_note = report.get("as_of_note") or (
        "as_of: 2026-09-18 オーダー / 2026年度 SB（SB採用優先）+ ナイターSB明記更新分"
    )
    event_date = report.get("event_date") or "2026-09-20"
    sb_note = report.get("sb_note") or (
        "- **SB反映**: `2026-sb-adopted` / Notion に加え、"
        "玉名郡ナイターで SB 明記された記録を、既存より速い場合のみ上書き"
    )
    heading = report.get("heading") or f"なごみ駅伝{year} {g} 区間オーダー × 今年度SB・予想"
    lines: list[str] = []
    lines.append(f"# {heading}")
    lines.append("")
    lines.append(as_of_note)
    lines.append(f"event_date: {event_date}")
    lines.append("")
    lines.append("## 予測式")
    lines.append("")
    if g == "男子":
        lines.append(
            f"- **3km予想（1500m）**: `SB秒 × 2 + {MEN_1500_TO_3K_ADD:.0f}` "
            "（掛け算＋加算。従来の駅伝予測HTML +68.50 から変更）"
        )
        lines.append(
            f"- **3km予想（800mフォールバック）**: `SB秒 × (3000/800)^{RIEGEL} × {MEN_800_TO_3K_COEF}`"
        )
        lines.append(
            f"- **3000m SB**: 1500換算3km予想より **{THRESHOLD_SEC:.0f}秒以上遅い** 場合は1500換算を採用"
        )
    else:
        lines.append(
            f"- **2km予想（1500m）**: `SB秒 × (2/1.5) + {WOMEN_1500_TO_2K_ADD:.0f}` "
            "（男子と同型の掛け算＋加算）"
        )
        lines.append(
            f"- **2km予想（800mフォールバック）**: 1500欠測時のみ "
            f"`SB秒 × (2000/800)^{RIEGEL} × {WOMEN_800_TO_2K_COEF}`"
        )
    lines.append(sb_note)
    lines.append("- タイムのリンクは当該記録の結果ページ（参考URL）")
    lines.append("- **参考総合順位**: 出走4名そろい、かつ実SB由来の予想が2区間以上。欠落区間は中央値補完（※付き）")
    lines.append("- **完全記録のみ順位**: 4区間すべてに実SB由来の予想があるチームのみ")
    lines.append(
        "- **各区セル**: `(通過順)通過予想 / (区間順)区間記録`。"
        "補完区間の区間記録は括弧付き"
    )
    if report.get("median_fill") is not None:
        lines.append(f"- 欠測補完中央値: `{fmt_time(report['median_fill'], 1)}` / 区間")
    lines.append("")
    lines.append("## 参考総合順位（欠測は中央値補完）")
    lines.append("")
    header = "| 順位 | No. | チーム | 総合予想 | 補完 | 1区 | 2区 | 3区 | 4区 |"
    lines.append(header)
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for t in report["ranked_ref"]:
        cells = [
            str(t["rank_ref"]),
            str(t["no"]),
            t["team"],
            fmt_clock(t["total_ref"]),
            "※" if t.get("imputed") else "",
        ]
        for det in t["legs"]:
            cells.append(fmt_leg_pred_cell(det))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## 完全記録のみ順位")
    lines.append("")
    header = "| 順位 | No. | チーム | 総合予想 | 1区 | 2区 | 3区 | 4区 |"
    lines.append(header)
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for t in report["ranked"]:
        cells = [
            str(t["rank"]),
            str(t["no"]),
            t["team"],
            fmt_clock(t["total"]),
        ]
        for det in t["legs"]:
            cells.append(fmt_leg_pred_cell(det, field_suffix="_full"))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## チーム別詳細")
    lines.append("")
    for t in report["teams"]:
        if t.get("rank_ref"):
            rank_s = f"参考{t['rank_ref']}位"
            if t.get("imputed"):
                rank_s += "※補完"
        else:
            rank_s = "順位対象外"
        if t.get("rank"):
            rank_s += f" / 完全{t['rank']}位"
        total_s = fmt_clock(t.get("total_ref")) if t.get("total_ref") is not None else "—"
        lines.append(f"### {t['no']}. {t['team']}（総合 {total_s} / {rank_s}）")
        lines.append("")
        cols = ["区間", "選手", *distances, leg_label, "通過予想", "通過順", "区間順", "備考"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for det in t["legs"]:
            cum_s = fmt_time(det.get("pred_cum"), 1) if det.get("pred_cum") is not None else ""
            row = [
                f"{det['leg']}区",
                det["name"] or "",
                *[md_mark(det["marks"].get(d)) for d in distances],
                fmt_time(det["pred"], 1) if det["pred"] is not None else (
                    f"({fmt_time(report['median_fill'], 1)})"
                    if det.get("name") and report.get("median_fill") is not None and det.get("pred_imputed_leg")
                    else ""
                ),
                cum_s,
                str(det["pred_cum_rank"]) if det.get("pred_cum_rank") is not None else "",
                str(det["pred_sec_rank"]) if det.get("pred_sec_rank") is not None else "",
                det["note"],
            ]
            lines.append("| " + " | ".join(row) + " |")
        if t["reserves"]:
            for r in t["reserves"]:
                row = [
                    "控え",
                    r["name"],
                    *[md_mark(r["marks"].get(d)) for d in distances],
                    fmt_time(r["pred"], 1) if r["pred"] is not None else "",
                    "",
                    "",
                    "",
                    r["note"],
                ]
                lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    lines.append("## 注意")
    lines.append("")
    lines.append(
        "トラックSBと駅伝は路面・気象・タスキ条件が異なります。"
        "本表は順位検討用の目安であり、出走可否・当日調子は含みません。"
    )
    lines.append("")
    return "\n".join(lines)


def render_pdf(report: dict[str, Any], path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font_name = "NotoSansJP"
    if FONT_PATH.exists():
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, str(FONT_PATH)))
    else:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        font_name = "HeiseiKakuGo-W5"
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleJP", parent=styles["Title"], fontName=font_name, fontSize=14, leading=18
    )
    h_style = ParagraphStyle(
        "HJP", parent=styles["Heading2"], fontName=font_name, fontSize=11, leading=14, spaceBefore=8
    )
    body = ParagraphStyle(
        "BodyJP", parent=styles["Normal"], fontName=font_name, fontSize=7.5, leading=9.5
    )
    cell = ParagraphStyle(
        "CellJP", parent=styles["Normal"], fontName=font_name, fontSize=6.5, leading=8
    )
    cell_leg = ParagraphStyle(
        "CellLegJP", parent=styles["Normal"], fontName=font_name, fontSize=5.5, leading=7
    )
    link_style = ParagraphStyle(
        "LinkJP", parent=cell, textColor=colors.HexColor("#1A56DB")
    )

    def p(text: str, style: ParagraphStyle = body) -> Paragraph:
        return Paragraph(escape(text).replace("\n", "<br/>"), style)

    def time_link(m: Mark | None) -> Any:
        if not m:
            return ""
        label = escape(m.text)
        if m.url:
            href = escape(m.url, {'"': "&quot;"})
            return Paragraph(f'<a href="{href}" color="#1A56DB">{label}</a>', link_style)
        return Paragraph(label, cell)

    story: list[Any] = []
    g = report["gender"]
    leg_label = report["leg_label"]
    distances = report["distances"]
    pdf_title = report.get("pdf_title") or f"なごみ駅伝2026 {g} オーダー×SB・予想"
    pdf_lead = report.get("pdf_lead") or (
        f"オーダー 9/18 20:00 / SBは2026年度（SB採用優先）。"
        f"参考順位は記録欠落区間を中央値補完。"
    )
    formula = (
        f" 男子3km: 1500×2+{MEN_1500_TO_3K_ADD}。3000mが1500換算より{THRESHOLD_SEC:.0f}s超遅い場合は1500換算。"
        if g == "男子"
        else (
            f" 女子2km: 1500×(2/1.5)+{WOMEN_1500_TO_2K_ADD:.0f}。"
            "1500優先（800は欠測時のみ）。"
        )
    )
    story.append(p(pdf_title, title_style))
    story.append(
        p(
            pdf_lead
            + formula
            + " 各区セルは (通過順)通過予想 / (区間順)区間記録。",
            body,
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(p("参考総合順位（※=欠測補完）", h_style))

    rank_header = ["順位", "No.", "チーム", "総合", "※", "1区", "2区", "3区", "4区"]
    rank_data: list[list[Any]] = [[Paragraph(escape(h), cell) for h in rank_header]]
    for t in report["ranked_ref"]:
        cells = [
            Paragraph(str(t["rank_ref"]), cell),
            Paragraph(str(t["no"]), cell),
            Paragraph(escape(t["team"]), cell),
            Paragraph(fmt_clock(t["total_ref"]), cell),
            Paragraph("※" if t.get("imputed") else "", cell),
        ]
        for d in t["legs"]:
            cells.append(Paragraph(escape(fmt_leg_pred_cell(d)), cell_leg))
        rank_data.append(cells)
    rank_table = Table(
        rank_data,
        colWidths=[10 * mm, 9 * mm, 32 * mm, 14 * mm, 7 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm],
        repeatRows=1,
    )
    rank_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F5")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D5DD")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(rank_table)
    story.append(Spacer(1, 6 * mm))
    story.append(p("チーム別詳細（タイムクリックで結果ページ）", h_style))

    for t in report["teams"]:
        if t.get("rank_ref"):
            rank_s = f"参考{t['rank_ref']}位" + ("※" if t.get("imputed") else "")
        else:
            rank_s = "順位対象外"
        total_s = fmt_clock(t.get("total_ref")) if t.get("total_ref") is not None else "—"
        story.append(p(f"{t['no']}. {t['team']}  総合 {total_s} / {rank_s}", h_style))
        header = ["区間", "選手", *distances, leg_label, "通過", "通順", "区順", "備考"]
        data: list[list[Any]] = [[Paragraph(escape(h), cell) for h in header]]
        for det in t["legs"]:
            pred_s = fmt_time(det["pred"], 1) if det["pred"] is not None else ""
            if not pred_s and det.get("pred_imputed_leg") and det.get("pred_used") is not None:
                pred_s = f"({fmt_time(det['pred_used'], 1)})"
            data.append(
                [
                    Paragraph(f"{det['leg']}区", cell),
                    Paragraph(escape(det["name"] or ""), cell),
                    *[time_link(det["marks"].get(d)) for d in distances],
                    Paragraph(pred_s, cell),
                    Paragraph(
                        fmt_time(det["pred_cum"], 1) if det.get("pred_cum") is not None else "",
                        cell,
                    ),
                    Paragraph(
                        str(det["pred_cum_rank"]) if det.get("pred_cum_rank") is not None else "",
                        cell,
                    ),
                    Paragraph(
                        str(det["pred_sec_rank"]) if det.get("pred_sec_rank") is not None else "",
                        cell,
                    ),
                    Paragraph(escape(det["note"] or ""), cell),
                ]
            )
        for r in t["reserves"]:
            data.append(
                [
                    Paragraph("控え", cell),
                    Paragraph(escape(r["name"]), cell),
                    *[time_link(r["marks"].get(d)) for d in distances],
                    Paragraph(fmt_time(r["pred"], 1) if r["pred"] is not None else "", cell),
                    Paragraph("", cell),
                    Paragraph("", cell),
                    Paragraph("", cell),
                    Paragraph(escape(r["note"] or ""), cell),
                ]
            )
        if g == "男子":
            widths = [9 * mm, 22 * mm, 14 * mm, 14 * mm, 14 * mm, 14 * mm, 14 * mm, 10 * mm, 10 * mm, 28 * mm]
        else:
            widths = [9 * mm, 24 * mm, 16 * mm, 16 * mm, 14 * mm, 14 * mm, 10 * mm, 10 * mm, 32 * mm]
        tbl = Table(data, colWidths=widths, repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F5")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D5DD")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                ]
            )
        )
        story.append(tbl)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=landscape(A4),
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
        title=f"なごみ駅伝2026 {g} SB・予想",
    )
    doc.build(story)


def write_coverage_csv(report: dict[str, Any], path: Path) -> None:
    distances = report["distances"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "gender",
                "team",
                "role",
                "name",
                *distances,
                "pred",
                "pred_cum",
                "pred_cum_rank",
                "pred_sec_rank",
                "note",
            ]
        )
        for t in report["teams"]:
            for det in t["legs"]:
                w.writerow(
                    [
                        report["gender"],
                        t["team"],
                        f"{det['leg']}区",
                        det["name"],
                        *[
                            det["marks"].get(d).text if det["marks"].get(d) else ""
                            for d in distances
                        ],
                        fmt_time(det["pred"], 1) if det["pred"] is not None else "",
                        fmt_time(det["pred_cum"], 1) if det.get("pred_cum") is not None else "",
                        det.get("pred_cum_rank") or "",
                        det.get("pred_sec_rank") or "",
                        det["note"],
                    ]
                )


def main() -> int:
    global THRESHOLD_SEC
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=float, default=20.0)
    args = parser.parse_args()
    THRESHOLD_SEC = float(args.threshold)

    women_sb_index, women_nighter_updates = load_sb_index(gender="女子")
    men_sb_index, men_nighter_updates = load_sb_index(gender="男子")
    nighter_updates = women_nighter_updates + men_nighter_updates
    print(
        f"SB athletes indexed: women={len(women_sb_index)}, "
        f"men={len(men_sb_index)} (threshold={THRESHOLD_SEC}s)"
    )
    if nighter_updates:
        print(f"Tamana nighter SB updates ({len(nighter_updates)}):")
        for u in nighter_updates:
            print(f"  {u}")
    else:
        print("Tamana nighter SB updates: (none)")
    women_order = parse_order_md(MEET_DIR / "女子区間オーダーリスト.md")
    men_order = parse_order_md(MEET_DIR / "男子区間オーダーリスト.md")

    women = build_gender_report("女子", women_order, women_sb_index)
    men = build_gender_report("男子", men_order, men_sb_index)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CORPUS_MEET.mkdir(parents=True, exist_ok=True)

    for report, stem in (
        (women, "女子区間オーダー_SB予想"),
        (men, "男子区間オーダー_SB予想"),
    ):
        md = render_markdown(report)
        md_path = OUT_DIR / f"{stem}.md"
        md_path.write_text(md, encoding="utf-8")
        (CORPUS_MEET / f"{stem}.md").write_text(md, encoding="utf-8")
        pdf_path = OUT_DIR / f"{stem}.pdf"
        render_pdf(report, pdf_path)
        write_coverage_csv(report, OUT_DIR / f"{stem}_coverage.csv")
        write_coverage_csv(report, CORPUS_MEET / f"{stem}_coverage.csv")
        n_ranked = len(report["ranked_ref"])
        n_complete = len(report["ranked"])
        n_teams = len(report["teams"])
        print(f"wrote {md_path}")
        print(f"wrote {pdf_path}")
        print(f"  ref-ranked {n_ranked}/{n_teams} (complete-only {n_complete})")

    # quick daimyo check
    for report in (women, men):
        for t in report["teams"]:
            if "岱明" in t["team"]:
                print(
                    report["gender"],
                    t["team"],
                    "ref",
                    t.get("rank_ref"),
                    "complete",
                    t.get("rank"),
                    "total",
                    fmt_clock(t.get("total_ref")),
                    "imputed",
                    t.get("imputed"),
                    [(d["name"], fmt_time(d["pred"], 1), d["note"]) for d in t["legs"]],
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
