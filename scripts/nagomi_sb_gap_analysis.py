#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""なごみ駅伝: SB予想と実績の差を分類し、グラフ付き HTML を生成する。

差 = 実績 − 予想（プラスは換算より遅い）。
5 段階（soft / hard 閾値）:
  - 差 <= −hard → 大きく上回った
  - −hard < 差 <= −soft → 少し上回った
  - |差| < soft → 妥当
  - soft <= 差 < hard → 少し下回った
  - 差 >= hard → 大きく下回った
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Literal

import arato_tamana_records as atr
import generate_nagomi_order_sb_preview as g
from arato_tamana_ranking import top_n_average

ClassName = Literal[
    "beat", "slight_beat", "ok", "slight_miss", "miss", "unknown"
]

CLASS_ORDER: tuple[ClassName, ...] = (
    "beat",
    "slight_beat",
    "ok",
    "slight_miss",
    "miss",
    "unknown",
)

# (soft, hard) 秒。soft 未満=妥当、hard 以上=大きく
LEG_BAND_BY_GENDER = {"女子": (10.0, 20.0), "男子": (15.0, 30.0)}
TEAM_BAND_BY_GENDER = {"女子": (30.0, 60.0), "男子": (60.0, 120.0)}
LEG_THRESHOLD_SEC = 20.0  # 互換: 女子 hard
TEAM_THRESHOLD_SEC = 60.0  # 互換: 女子 hard
LEG_THRESHOLD_BY_GENDER = {k: v[1] for k, v in LEG_BAND_BY_GENDER.items()}
TEAM_THRESHOLD_BY_GENDER = {k: v[1] for k, v in TEAM_BAND_BY_GENDER.items()}

LABEL_JA: dict[ClassName, str] = {
    "beat": "大きく上回った",
    "slight_beat": "少し上回った",
    "ok": "妥当",
    "slight_miss": "少し下回った",
    "miss": "大きく下回った",
    "unknown": "判定不可",
}

CLASS_COLOR: dict[ClassName, str] = {
    "beat": "#0f766e",
    "slight_beat": "#14b8a6",
    "ok": "#475569",
    "slight_miss": "#d97706",
    "miss": "#b45309",
    "unknown": "#94a3b8",
}

# 荒尾・玉名地区（input/arato_tamana_report.yaml affiliation_keywords 準拠）
# NJAC はキーワードに含めず、athlete override（濱北愛→長洲中）のみ学校配分する。
ARATO_TAMANA_KEYWORDS: tuple[str, ...] = (
    "岱明",
    "玉名",
    "ATRC",
    "天水",
    "金栗",
    "附",
    "長洲",
    "南関",
    "玉東",
    "有明",
    "荒尾",
    "玉陵",
    "玉南",
)
SCHOOL_AVG_N_BY_GENDER: dict[str, int] = {"女子": 5, "男子": 6}


def school_avg_n(gender: str) -> int:
    return SCHOOL_AVG_N_BY_GENDER.get(gender, 6)


_CLUB_KEYS: tuple[str, ...] = (
    "玉名アスリーツ",
    "玉東クラブ",
    "金栗PROJECT",
    "ATRC",
    "NJAC",
    "ＮＪＡＣ",
)
_TEAM_SUFFIX_RE = re.compile(r"[\s　]*([A-ZＡ-ＺαβγωΩ]|[Ａ-Ｚ])$")


def _normalize_person_name(name: str) -> str:
    return re.sub(r"[\s　]+", "", name or "")


def _strip_team_suffix(team: str) -> str:
    s = (team or "").strip()
    s = _TEAM_SUFFIX_RE.sub("", s)
    s = re.sub(r"(中学校|中)$", "", s)
    return s.strip()


def entry_club_key(team: str) -> str | None:
    t = team or ""
    for key in _CLUB_KEYS:
        if key in t:
            return "NJAC" if key in ("NJAC", "ＮＪＡＣ") else key
    if "金栗" in t:
        return "金栗PROJECT"
    return None


def load_arato_school_config(path: Path | None = None) -> dict[str, Any]:
    return atr.load_config(path)


def resolve_arato_school(
    team: str,
    name: str,
    config: dict[str, Any] | None = None,
) -> str | None:
    """大会チーム名＋選手名を荒玉学校名へ配分。対象外は None。

    - クラブ（金栗PROJECT / ATRC / 玉名アスリーツ 等）は yaml の school_analysis_* を適用
    - NJAC は athlete override にある選手のみ（女子・濱北愛）。他は除外
    - 金栗所属で exclude_name_keywords に当たる選手は除外
    - 学校チームは接尾辞を除き「◯◯中」に正規化
    """
    cfg = config if config is not None else load_arato_school_config()
    team_s = team or ""
    name_s = name or ""
    nkey = _normalize_person_name(name_s)

    excl_aff = str(cfg.get("exclude_when_affiliation_contains") or "")
    if excl_aff and excl_aff in team_s:
        for kw in cfg.get("exclude_name_keywords") or []:
            if _normalize_person_name(str(kw)) and _normalize_person_name(str(kw)) in nkey:
                return None

    club = entry_club_key(team_s)
    athlete_over = cfg.get("school_analysis_athlete_affiliation_overrides") or {}
    aff_over = cfg.get("school_analysis_affiliation_overrides") or {}

    if club:
        spec = athlete_over.get(club) or {}
        athletes = {
            _normalize_person_name(str(k)): str(v)
            for k, v in (spec.get("athletes") or {}).items()
        }
        if nkey in athletes:
            return athletes[nkey]
        if spec.get("default"):
            return str(spec["default"])
        if club in aff_over:
            return str(aff_over[club])
        # NJAC など default なし・選手未登録 → 荒玉対象外
        return None

    keywords = tuple(cfg.get("affiliation_keywords") or ARATO_TAMANA_KEYWORDS)
    if not any(kw in team_s for kw in keywords):
        return None
    base = _strip_team_suffix(team_s)
    if not base:
        return None
    if base.endswith("中"):
        return base
    return f"{base}中"


def is_arato_tamana_team(team: str, config: dict[str, Any] | None = None) -> bool:
    """学校チームまたは配分対象クラブか（NJAC 本体は False。選手単位で判定）。"""
    if entry_club_key(team or "") == "NJAC":
        return False
    cfg = config if config is not None else load_arato_school_config()
    keywords = tuple(cfg.get("affiliation_keywords") or ARATO_TAMANA_KEYWORDS)
    return any(kw in (team or "") for kw in keywords)


def select_arato_tamana_teams(
    teams: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """関連チームを実順位順で返す（NJAC は除外）。"""
    rows = [t for t in teams if is_arato_tamana_team(str(t.get("team") or ""), config)]
    return sorted(
        rows,
        key=lambda r: (r.get("actual_rank") is None, r.get("actual_rank") or 999, r["team"]),
    )


def build_arato_school_topn_ranking(
    legs: list[dict[str, Any]],
    *,
    gender: str,
    n: int | None = None,
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """学校ごとに実績上位 avg_n 人の平均で順位付けし、内訳は配分全員を付ける。

    女子: 平均5、男子: 平均6。内訳表示は人数制限なし。
    """
    avg_n = school_avg_n(gender) if n is None else n
    cfg = config if config is not None else load_arato_school_config()
    by_school: dict[str, dict[str, dict[str, Any]]] = {}
    for leg in legs:
        if leg.get("actual") is None:
            continue
        if leg.get("gender") not in (None, gender):
            continue
        school = resolve_arato_school(str(leg.get("team") or ""), str(leg.get("name") or ""), cfg)
        if not school:
            continue
        name = str(leg.get("name") or "").strip()
        if not name:
            continue
        bucket = by_school.setdefault(school, {})
        prev = bucket.get(_normalize_person_name(name))
        if prev is None or float(leg["actual"]) < float(prev["actual"]):
            bucket[_normalize_person_name(name)] = {
                **leg,
                "school": school,
                "name": name,
            }

    entries: list[dict[str, Any]] = []
    short_entries: list[dict[str, Any]] = []
    for school, athletes in by_school.items():
        rows = sorted(athletes.values(), key=lambda r: (float(r["actual"]), r["name"]))
        if not rows:
            continue
        complete = len(rows) >= avg_n
        use_avg = min(avg_n, len(rows))
        avg = top_n_average([float(r["actual"]) for r in rows[:use_avg]], use_avg)
        if avg is None:
            continue
        members = []
        for i, r in enumerate(rows, start=1):
            members.append(
                {
                    "slot": i,
                    "name": r["name"],
                    "team": r.get("team") or "",
                    "leg": r.get("leg"),
                    "actual": r.get("actual"),
                    "pred": r.get("pred"),
                    "delta": r.get("delta"),
                    "class": r.get("class") or "unknown",
                    "in_average": i <= use_avg,
                }
            )
        item = {
            "school": school,
            "athlete_count": len(rows),
            "top_n": use_avg,
            "avg_n": avg_n,
            "average": avg,
            "members": members,
            "complete": complete,
        }
        if complete:
            entries.append(item)
        else:
            short_entries.append(item)

    ranked = sorted(entries, key=lambda e: (float(e["average"]), e["school"]))
    for i, e in enumerate(ranked, start=1):
        e["rank"] = i
    short_sorted = sorted(short_entries, key=lambda e: (float(e["average"]), e["school"]))
    for e in short_sorted:
        e["rank"] = None
    return ranked + short_sorted


def leg_band(gender: str | None = None) -> tuple[float, float]:
    if gender and gender in LEG_BAND_BY_GENDER:
        return LEG_BAND_BY_GENDER[gender]
    return (10.0, LEG_THRESHOLD_SEC)


def team_band(gender: str | None = None) -> tuple[float, float]:
    if gender and gender in TEAM_BAND_BY_GENDER:
        return TEAM_BAND_BY_GENDER[gender]
    return (30.0, TEAM_THRESHOLD_SEC)


def leg_threshold(gender: str | None = None) -> float:
    return leg_band(gender)[1]


def team_threshold(gender: str | None = None) -> float:
    return team_band(gender)[1]


def classify_delta(
    delta: float | None,
    soft: float,
    hard: float | None = None,
) -> ClassName:
    """soft / hard の2閾値で5段階分類。hard 省略時は soft のみ（3段階相当）。"""
    if delta is None:
        return "unknown"
    hi = soft if hard is None else hard
    if hi < soft:
        soft, hi = hi, soft
    if delta <= -hi:
        return "beat"
    if delta <= -soft:
        return "slight_beat"
    if delta < soft:
        return "ok"
    if delta < hi:
        return "slight_miss"
    return "miss"


def label_ja(name: ClassName | str) -> str:
    return LABEL_JA.get(name, str(name))  # type: ignore[arg-type]


def summarize_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    c = Counter(r.get("class", "unknown") for r in rows)
    return {k: int(c.get(k, 0)) for k in CLASS_ORDER}


def attach_actuals_by_no(report: dict[str, Any], teams: list[dict[str, Any]]) -> None:
    """2026 向け: オーダー No. で成績を突合する。"""
    by_no = {t["no"]: t for t in teams if t.get("no") is not None}
    for row in report["teams"]:
        actual = by_no.get(row.get("no"))
        if not actual:
            continue
        _apply_actual(row, actual)


def attach_actuals_by_team(report: dict[str, Any], teams: list[dict[str, Any]]) -> None:
    """2025 向け: チーム名で突合する。"""
    by_team = {t["team"]: t for t in teams}
    for row in report["teams"]:
        actual = by_team.get(row["team"])
        if not actual:
            continue
        _apply_actual(row, actual)


def _apply_actual(row: dict[str, Any], actual: dict[str, Any]) -> None:
    row["actual_rank"] = actual.get("rank")
    row["actual_total"] = g.parse_seconds(actual.get("total"))
    row["official"] = actual.get("official", True)
    row["result_team"] = actual.get("team")
    for det, leg in zip(row["legs"], actual.get("legs") or []):
        det["actual"] = g.parse_seconds(leg.get("split"))
        det["actual_rank"] = leg.get("split_rank")
        if det.get("grade") is None:
            det["grade"] = leg.get("grade")
        if det.get("pred") is not None and det.get("actual") is not None:
            det["delta"] = det["actual"] - det["pred"]
        else:
            det["delta"] = None
    if row.get("actual_total") is not None and row.get("total_ref") is not None:
        row["total_delta"] = row["actual_total"] - row["total_ref"]
    else:
        row["total_delta"] = None


def build_analysis_rows(
    report: dict[str, Any], *, year: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    teams_out: list[dict[str, Any]] = []
    legs_out: list[dict[str, Any]] = []
    gender = report["gender"]
    t_soft, t_hard = team_band(gender)
    l_soft, l_hard = leg_band(gender)
    for t in report["teams"]:
        if not t.get("official", True):
            continue
        if t.get("actual_rank") is None and t.get("actual_total") is None:
            continue
        team_delta = t.get("total_delta")
        team_class = classify_delta(team_delta, t_soft, t_hard)
        teams_out.append(
            {
                "year": year,
                "gender": gender,
                "no": t.get("no"),
                "team": t.get("result_team") or t["team"],
                "order_team": t["team"],
                "actual_rank": t.get("actual_rank"),
                "rank_ref": t.get("rank_ref"),
                "actual_total": t.get("actual_total"),
                "total_ref": t.get("total_ref"),
                "total_delta": team_delta,
                "class": team_class,
                "imputed": bool(t.get("imputed")),
            }
        )
        for det in t["legs"]:
            if not det.get("name"):
                continue
            d = det.get("delta")
            legs_out.append(
                {
                    "year": year,
                    "gender": gender,
                    "team": t.get("result_team") or t["team"],
                    "leg": det["leg"],
                    "name": det["name"],
                    "actual": det.get("actual"),
                    "pred": det.get("pred"),
                    "delta": d,
                    "class": classify_delta(d, l_soft, l_hard),
                    "note": det.get("note") or "",
                }
            )
    teams_out.sort(
        key=lambda r: (r["actual_rank"] is None, r["actual_rank"] or 999, r["team"])
    )
    legs_out.sort(key=lambda r: (r["team"], r["leg"]))
    return teams_out, legs_out


def signed_sec(delta: float | None) -> str:
    if delta is None:
        return "—"
    sign = "+" if delta >= 0 else "−"
    return f"{sign}{g.fmt_time(abs(delta), 1)}"


def _bar_chart_svg(
    rows: list[dict[str, Any]],
    *,
    value_key: str,
    label_key: str,
    chart_id: str,
    max_bars: int = 24,
) -> str:
    """ラベル列・バー列・数値列を分離した HTML バーチャート（見切れ防止）。"""
    data = [r for r in rows if r.get(value_key) is not None][:max_bars]
    if not data:
        return f'<p class="empty" id="{html.escape(chart_id)}">比較できるデータがありません</p>'
    vals = [float(r[value_key]) for r in data]
    max_abs = max(abs(v) for v in vals) or 1.0
    rows_html: list[str] = []
    for r in data:
        val = float(r[value_key])
        cls: ClassName = r.get("class") or "unknown"
        color = CLASS_COLOR[cls]
        pct = abs(val) / max_abs * 50.0
        label = html.escape(str(r.get(label_key) or ""))
        delta_s = html.escape(signed_sec(val))
        if val < 0:
            bar_style = (
                f"right:50%;width:{pct:.2f}%;background:{color};"
                "border-radius:4px 0 0 4px"
            )
        else:
            bar_style = (
                f"left:50%;width:{pct:.2f}%;background:{color};"
                "border-radius:0 4px 4px 0"
            )
        rows_html.append(
            f'<div class="bar-row">'
            f'<div class="bar-label" title="{label}">{label}</div>'
            f'<div class="bar-track">'
            f'<div class="bar-zero"></div>'
            f'<div class="bar-fill" style="{bar_style}"></div>'
            f"</div>"
            f'<div class="bar-val cls-{html.escape(cls)}">{delta_s}</div>'
            f"</div>"
        )
    return (
        f'<div class="bar-chart" id="{html.escape(chart_id)}" role="img" '
        f'aria-label="予実差バーチャート">'
        f'<div class="bar-axis">'
        f'<span class="bar-axis-label">チーム / 区間</span>'
        f'<span class="bar-axis-track"><span>速い（−）</span><span>遅い（＋）</span></span>'
        f'<span class="bar-axis-val">差</span>'
        f"</div>"
        + "".join(rows_html)
        + "</div>"
    )


def format_count_pct(n: int, total: int) -> str:
    """件数と割合（四捨五入の整数%）を「N（P%）」形式で返す。"""
    if total <= 0:
        return f"{n}（0%）"
    pct = int(round(100.0 * n / total))
    return f"{n}（{pct}%）"


def _donut_counts(counts: dict[str, int], chart_id: str) -> str:
    raw_total = sum(counts.values())
    total = raw_total or 1
    size = 140
    cx = cy = size / 2
    r = 48
    stroke = 18
    circ = 2 * 3.1415926535 * r
    offset = 0.0
    parts = [
        f'<svg id="{html.escape(chart_id)}" viewBox="0 0 {size} {size}" '
        f'class="donut" role="img" aria-label="分類内訳">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#e2e8f0" '
        f'stroke-width="{stroke}"/>'
    ]
    for key in CLASS_ORDER:
        n = counts.get(key, 0)
        if n <= 0:
            continue
        length = circ * n / total
        pct_label = format_count_pct(n, raw_total)
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
            f'stroke="{CLASS_COLOR[key]}" stroke-width="{stroke}" '
            f'stroke-dasharray="{length:.2f} {circ - length:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 {cx} {cy})">'
            f'<title>{html.escape(label_ja(key))} {html.escape(pct_label)}</title>'
            f"</circle>"
        )
        offset += length
    parts.append(
        f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" class="donut-center">'
        f"{raw_total}</text></svg>"
    )
    legend = "".join(
        f'<li><span class="swatch" style="background:{CLASS_COLOR[k]}"></span>'
        f"{html.escape(label_ja(k))} {html.escape(format_count_pct(counts[k], raw_total))}</li>"
        for k in CLASS_ORDER
        if counts.get(k, 0)
    )
    return (
        f'<div class="donut-wrap">{"".join(parts)}'
        f'<ul class="legend">{legend}</ul></div>'
    )


def _table_teams(rows: list[dict[str, Any]]) -> str:
    body = []
    for r in rows:
        cls = r.get("class") or "unknown"
        body.append(
            "<tr class=\"cls-"
            + html.escape(cls)
            + "\">"
            + "".join(
                f"<td>{html.escape(str(v))}</td>"
                for v in [
                    r.get("actual_rank") or "—",
                    r.get("team") or "",
                    g.fmt_clock(r.get("actual_total")),
                    g.fmt_clock(r.get("total_ref")),
                    signed_sec(r.get("total_delta")),
                    r.get("rank_ref") or "—",
                    (
                        str((r["actual_rank"] or 0) - (r["rank_ref"] or 0))
                        if r.get("actual_rank") and r.get("rank_ref")
                        else "—"
                    ),
                    label_ja(cls),
                    "※" if r.get("imputed") else "",
                ]
            )
            + "</tr>"
        )
    return (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>実順</th><th>チーム</th><th>実総合</th><th>予想総合</th>"
        "<th>差</th><th>予想順</th><th>順位差</th><th>判定</th><th>補完</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def _table_legs(rows: list[dict[str, Any]]) -> str:
    body = []
    for r in rows:
        cls = r.get("class") or "unknown"
        body.append(
            "<tr class=\"cls-"
            + html.escape(cls)
            + "\">"
            + "".join(
                f"<td>{html.escape(str(v))}</td>"
                for v in [
                    r.get("team") or "",
                    f"{r.get('leg')}区",
                    r.get("name") or "",
                    g.fmt_time(r.get("actual"), 0) if r.get("actual") is not None else "—",
                    g.fmt_time(r.get("pred"), 1) if r.get("pred") is not None else "—",
                    signed_sec(r.get("delta")),
                    label_ja(cls),
                    r.get("note") or "",
                ]
            )
            + "</tr>"
        )
    return (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>チーム</th><th>区間</th><th>選手</th><th>実績</th><th>予想</th>"
        "<th>差</th><th>判定</th><th>備考</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def _school_member_rows(members: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for m in members:
        cls = m.get("class") or "unknown"
        rows.append(
            "<tr class=\"cls-"
            + html.escape(cls)
            + "\">"
            + "".join(
                f"<td>{html.escape(str(v))}</td>"
                for v in [
                    m.get("slot") or "",
                    m.get("name") or "",
                    m.get("team") or "",
                    f"{m.get('leg')}区",
                    g.fmt_time(m.get("actual"), 0) if m.get("actual") is not None else "—",
                    signed_sec(m.get("delta")),
                    label_ja(cls),
                ]
            )
            + "</tr>"
        )
    return "".join(rows)


def _school_detail_block(e: dict[str, Any], *, ranked: bool) -> str:
    avg_s = g.fmt_time(e["average"], 1) if e.get("average") is not None else "—"
    use_n = int(e.get("top_n") or e.get("avg_n") or 6)
    if ranked:
        label = f"{e.get('rank')}. {e.get('school')}　上位{use_n}平均 {avg_s}"
    else:
        label = f"（参考）{e.get('school')}　上位{use_n}平均 {avg_s}（{e.get('athlete_count')}人）"
    return (
        f"<details class=\"school-detail\"{' open' if ranked else ''}>"
        f"<summary>{html.escape(label)}</summary>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>#</th><th>選手</th><th>出走チーム</th><th>区間</th>"
        "<th>実績</th><th>差</th><th>判定</th>"
        "</tr></thead><tbody>"
        + _school_member_rows(list(e.get("members") or []))
        + "</tbody></table></div></details>"
    )


def _table_arato_school_ranking(
    entries: list[dict[str, Any]],
    *,
    gender: str,
) -> str:
    avg_n = school_avg_n(gender)
    complete = [e for e in entries if e.get("complete")]
    short = [e for e in entries if not e.get("complete")]
    if not complete and not short:
        return (
            f'<p class="empty">上位{avg_n}人を揃えられる荒玉学校がありません'
            "（配分後・欠測除外）</p>"
        )
    parts: list[str] = []
    if complete:
        summary_rows = []
        for e in complete:
            avg_s = g.fmt_time(e["average"], 1) if e.get("average") is not None else "—"
            summary_rows.append(
                "<tr>"
                + "".join(
                    f"<td>{html.escape(str(v))}</td>"
                    for v in [
                        e.get("rank") or "",
                        e.get("school") or "",
                        avg_s,
                        e.get("athlete_count") or "",
                    ]
                )
                + "</tr>"
            )
        parts.append(
            '<div class="table-wrap"><table><thead><tr>'
            f"<th>順</th><th>学校</th><th>上位{avg_n}平均</th><th>配分人数</th>"
            "</tr></thead><tbody>"
            + "".join(summary_rows)
            + "</tbody></table></div>"
        )
        parts.extend(_school_detail_block(e, ranked=True) for e in complete)
    else:
        parts.append(
            f'<p class="empty">上位{avg_n}人を揃えた学校はありません。'
            "人数不足の学校を参考表示します。</p>"
        )
    if short:
        parts.append(f"<h5>参考（{avg_n}人未満）</h5>")
        parts.extend(_school_detail_block(e, ranked=False) for e in short)
    return "".join(parts)

def render_html(payload: dict[str, Any]) -> str:
    sections: list[str] = []
    for year_block in payload.get("years") or []:
        year = year_block["year"]
        sections.append(
            f"<section class=\"year\" id=\"year-{year}\">"
            f"<h2>{year} なごみ駅伝</h2>"
            f"<p class=\"meta\">出走 {html.escape(str(year_block.get('event_date') or ''))} / "
            f"SB as_of {html.escape(str(year_block.get('as_of') or ''))}</p>"
        )
        for gender_block in year_block.get("genders") or []:
            gender = gender_block["gender"]
            teams = gender_block.get("teams") or []
            legs = gender_block.get("legs") or []
            t_counts = summarize_counts(teams)
            l_counts = summarize_counts([x for x in legs if x.get("delta") is not None])
            chart_teams = sorted(
                [t for t in teams if t.get("total_delta") is not None],
                key=lambda t: t["total_delta"],
            )
            chart_legs = sorted(
                [x for x in legs if x.get("delta") is not None],
                key=lambda x: x["delta"],
            )[:30]
            chart_legs_labeled = [
                {
                    **r,
                    "label": f"{r['team']} {r['leg']}区 {r['name']}",
                }
                for r in chart_legs
            ]
            team_chart = _bar_chart_svg(
                chart_teams,
                value_key="total_delta",
                label_key="team",
                chart_id=f"chart-team-{year}-{gender}",
            )
            leg_chart = _bar_chart_svg(
                chart_legs_labeled,
                value_key="delta",
                label_key="label",
                chart_id=f"chart-leg-{year}-{gender}",
                max_bars=30,
            )
            arato_schools = build_arato_school_topn_ranking(legs, gender=gender)
            arato_teams = select_arato_tamana_teams(teams)
            sections.append(
                f"<article class=\"gender\" id=\"{year}-{html.escape(gender)}\">"
                f"<h3>{html.escape(gender)}</h3>"
                f"<div class=\"cards\">"
                f"<div class=\"card\"><h4>チーム判定</h4>"
                f"{_donut_counts(t_counts, f'donut-team-{year}-{gender}')}</div>"
                f"<div class=\"card\"><h4>区間判定（予想あり）</h4>"
                f"{_donut_counts(l_counts, f'donut-leg-{year}-{gender}')}</div>"
                f"</div>"
                f"<h4 class=\"arato\">荒玉学校対抗：上位{school_avg_n(gender)}人平均</h4>"
                f"<p class=\"meta\">クラブは <code>arato_tamana_report.yaml</code> の学校配分に従う"
                f"（金栗PROJECT→菊水中／例外あり、ATRC→荒尾第四中／例外あり、"
                f"玉名アスリーツ→玉陵中。NJAC は濱北愛→長洲中のみ。他の NJAC と金栗の除外選手は対象外）。"
                f"各校の区間実績から上位{school_avg_n(gender)}人平均で順位付け（内訳は配分全員）。</p>"
                f"{_table_arato_school_ranking(arato_schools, gender=gender)}"
                f"<h4 class=\"arato\">荒尾玉名関連：出走チーム成績</h4>"
                f"{_table_teams(arato_teams) if arato_teams else '<p class=\"empty\">該当チームなし</p>'}"
                f"<h4>チーム総合差（左＝予想より速い）</h4>"
                f"{team_chart}"
                f"<h4>区間差トップ（速い／遅い）</h4>"
                f"{leg_chart}"
                f"<h4>チーム一覧</h4>{_table_teams(teams)}"
                f"<h4>区間一覧</h4>{_table_legs(legs)}"
                f"</article>"
            )
        sections.append("</section>")

    css = """
:root{--bg:#f4f7fb;--ink:#0f172a;--muted:#64748b;--card:#fff;--line:#dbe3ee;
--beat:#0f766e;--slight-beat:#14b8a6;--ok:#475569;--slight-miss:#d97706;--miss:#b45309}
*{box-sizing:border-box}body{margin:0;font-family:"Hiragino Sans","Noto Sans JP",system-ui,sans-serif;
color:var(--ink);background:linear-gradient(180deg,#e8eef7 0%,var(--bg) 220px)}
main{max-width:1100px;margin:0 auto;padding:28px 18px 64px}
h1{font-size:1.65rem;margin:0 0 8px}h2{margin:36px 0 8px;font-size:1.35rem}
h3{margin:28px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h4{margin:22px 0 10px;font-size:1rem;color:#334155}
h4.arato{color:#0f766e;border-left:3px solid #0f766e;padding-left:10px}
.school-detail{background:var(--card);border:1px solid var(--line);border-radius:12px;
margin:10px 0;padding:8px 12px}
.school-detail summary{cursor:pointer;font-weight:650;color:#0f766e;padding:6px 0}
.lead,.meta{color:var(--muted);line-height:1.55}.note{background:#fffbeb;border-left:4px solid #d97706;
padding:12px 14px;margin:16px 0;border-radius:0 10px 10px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin:12px 0 8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
.donut-wrap{display:flex;gap:12px;align-items:center}.donut-center{font-size:18px;font-weight:700;fill:var(--ink)}
.legend{list-style:none;padding:0;margin:0;font-size:13px;line-height:1.7}
.swatch{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
.bar-chart{width:100%;background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:12px 14px 10px;overflow:visible}
.bar-axis,.bar-row{display:grid;grid-template-columns:minmax(160px,38%) minmax(0,1fr) 4.5rem;
gap:10px;align-items:center}
.bar-axis{margin:0 0 8px;font-size:11px;color:var(--muted)}
.bar-axis-track{display:flex;justify-content:space-between}
.bar-axis-val,.bar-val{text-align:right;font-variant-numeric:tabular-nums}
.bar-row{min-height:28px;margin:0 0 4px}
.bar-label{font-size:12px;line-height:1.35;color:#334155;overflow-wrap:anywhere;word-break:break-word}
.bar-track{position:relative;height:18px;background:#f1f5f9;border-radius:4px;overflow:hidden}
.bar-zero{position:absolute;left:50%;top:0;bottom:0;width:1px;background:#94a3b8;z-index:1}
.bar-fill{position:absolute;top:2px;bottom:2px;z-index:2;min-width:2px}
.bar-val{font-size:12px;font-weight:650;color:#475569}
.bar-val.cls-beat{color:var(--beat)}.bar-val.cls-slight_beat{color:var(--slight-beat)}
.bar-val.cls-miss{color:var(--miss)}.bar-val.cls-slight_miss{color:var(--slight-miss)}
@media (max-width:640px){
.bar-axis,.bar-row{grid-template-columns:1fr 3.5rem;grid-template-areas:"label val" "track track"}
.bar-axis-label,.bar-label{grid-area:label}.bar-axis-val,.bar-val{grid-area:val}
.bar-axis-track,.bar-track{grid-area:track}.bar-axis-track{display:none}
.bar-label{font-size:11px;margin-bottom:2px}
}
.table-wrap{overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}
th,td{padding:8px 10px;border-bottom:1px solid #edf1f5;text-align:left}
th{position:sticky;top:0;background:#eef3f8;font-weight:650}
tr.cls-beat,tr.cls-slight_beat{background:#f0fdfa}
tr.cls-miss{background:#fff7ed}tr.cls-slight_miss{background:#fffbeb}
tr.cls-beat td:nth-last-child(2),tr.cls-slight_beat td:nth-last-child(2){color:var(--beat);font-weight:650}
tr.cls-miss td:nth-last-child(2),tr.cls-slight_miss td:nth-last-child(2){color:var(--miss);font-weight:650}
footer{margin-top:28px;color:var(--muted);font-size:12px;line-height:1.5}
.nav{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}
.nav a{background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 12px;
text-decoration:none;color:#0f172a;font-size:13px}
.empty{color:var(--muted);padding:12px}
"""
    nav = "".join(
        f'<a href="#year-{yb["year"]}">{yb["year"]}</a>'
        for yb in payload.get("years") or []
    )
    body = (
        f"<!doctype html><html lang=\"ja\"><head><meta charset=\"utf-8\">"
        f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>なごみ駅伝 SB予想と実績のギャップ分析</title>"
        f"<style>{css}</style></head><body><main class=\"nagomi-sb-gap\">"
        f"<h1>なごみ駅伝：SB予想と実績のギャップ</h1>"
        f"<p class=\"lead\">各個人・チームについて、レース前 SB 換算の予想と実際の区間／総合タイムの差を分類します。"
        f"差 = 実績 − 予想（マイナス＝予想より速い＝上回った）。</p>"
        f"<div class=\"note\"><strong>判定閾値（5段階）</strong>：区間 soft/hard が女子 "
        f"{LEG_BAND_BY_GENDER['女子'][0]:.0f}/{LEG_BAND_BY_GENDER['女子'][1]:.0f}秒・男子 "
        f"{LEG_BAND_BY_GENDER['男子'][0]:.0f}/{LEG_BAND_BY_GENDER['男子'][1]:.0f}秒。"
        f"総合は女子 {TEAM_BAND_BY_GENDER['女子'][0]:.0f}/{TEAM_BAND_BY_GENDER['女子'][1]:.0f}秒・男子 "
        f"{TEAM_BAND_BY_GENDER['男子'][0]:.0f}/{TEAM_BAND_BY_GENDER['男子'][1]:.0f}秒。"
        f"|差|&lt;soft → 妥当、soft〜hard → 少し上回った／少し下回った、hard 以上 → "
        f"大きく上回った／大きく下回った。"
        f"欠測 SB の区間は判定不可。チーム予想は欠測中央値補完（※）を含む場合あり。</div>"
        f"<nav class=\"nav\">{nav}</nav>"
        + "".join(sections)
        + "<footer>生成: scripts/generate_nagomi_sb_gap_analysis.py / "
        "根拠: なごみ成績表 + 区間オーダー SB予想（ADR 049 / 051 / 052）</footer>"
        f"<script type=\"application/json\" id=\"payload\">{json.dumps(payload, ensure_ascii=False)}</script>"
        "</main></body></html>"
    )
    return body


def render_gap_markdown(
    *,
    year: int,
    event_date: str,
    as_of: str,
    genders: list[dict[str, Any]],
) -> str:
    lines = [
        f"# なごみ駅伝{year} SB予想と実績の乖離",
        "",
        f"出走: {event_date} 成績表。予想: SB（as_of {as_of}）に既存換算式。",
        "",
        "## 読み方",
        "",
        "- **差** は `実績 − 予想`。プラスは SB 換算より遅かった。",
        "- **判定（5段階）**: |差|<soft → 妥当、soft〜hard → 少し上回った／少し下回った、"
        "hard 以上 → 大きく上回った／大きく下回った。",
        f"- 区間 soft/hard: 女子 {LEG_BAND_BY_GENDER['女子'][0]:.0f}/{LEG_BAND_BY_GENDER['女子'][1]:.0f}秒・"
        f"男子 {LEG_BAND_BY_GENDER['男子'][0]:.0f}/{LEG_BAND_BY_GENDER['男子'][1]:.0f}秒。"
        f"総合: 女子 {TEAM_BAND_BY_GENDER['女子'][0]:.0f}/{TEAM_BAND_BY_GENDER['女子'][1]:.0f}秒・"
        f"男子 {TEAM_BAND_BY_GENDER['男子'][0]:.0f}/{TEAM_BAND_BY_GENDER['男子'][1]:.0f}秒。",
        "- グラフ付き HTML: `out/analysis/nagomi_sb_gap_analysis.html`",
        "",
    ]
    for block in genders:
        gender = block["gender"]
        teams = block["teams"]
        legs = block["legs"]
        t_counts = summarize_counts(teams)
        lines.append(f"## {gender}")
        lines.append("")
        arato_schools = build_arato_school_topn_ranking(legs, gender=gender)
        arato_teams = select_arato_tamana_teams(teams)
        lines.append(f"### 荒玉学校対抗：上位{school_avg_n(gender)}人平均")
        lines.append("")
        lines.append(
            "クラブは `arato_tamana_report.yaml` の学校配分に従う"
            "（NJAC は濱北愛→長洲中のみ。他の NJAC・金栗除外選手は対象外）。"
            f"各校の区間実績から上位{school_avg_n(gender)}人平均で順位付け（内訳は配分全員）。"
        )
        lines.append("")
        if arato_schools:
            complete = [e for e in arato_schools if e.get("complete")]
            short = [e for e in arato_schools if not e.get("complete")]
            if complete:
                lines.append(f"| 順 | 学校 | 上位{school_avg_n(gender)}平均 | 配分人数 |")
                lines.append("| --- | --- | --- | --- |")
                for e in complete:
                    lines.append(
                        "| "
                        + " | ".join(
                            [
                                str(e.get("rank") or ""),
                                e.get("school") or "",
                                g.fmt_time(e.get("average"), 1)
                                if e.get("average") is not None
                                else "",
                                str(e.get("athlete_count") or ""),
                            ]
                        )
                        + " |"
                    )
                lines.append("")
                for e in complete:
                    lines.append(
                        f"#### {e.get('rank')}. {e.get('school')} "
                        f"（平均 {g.fmt_time(e.get('average'), 1)}）"
                    )
                    lines.append("")
                    lines.append("| # | 選手 | 出走チーム | 区間 | 実績 | 差 | 判定 |")
                    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
                    for m in e.get("members") or []:
                        lines.append(
                            "| "
                            + " | ".join(
                                [
                                    str(m.get("slot") or ""),
                                    m.get("name") or "",
                                    m.get("team") or "",
                                    f"{m.get('leg')}区",
                                    g.fmt_time(m.get("actual"), 0)
                                    if m.get("actual") is not None
                                    else "",
                                    signed_sec(m.get("delta")),
                                    label_ja(m.get("class") or "unknown"),
                                ]
                            )
                            + " |"
                        )
                    lines.append("")
            else:
                lines.append(f"（上位{school_avg_n(gender)}人を揃えた学校なし）")
                lines.append("")
            if short:
                lines.append(f"#### 参考（{school_avg_n(gender)}人未満）")
                lines.append("")
                for e in short:
                    use_n = int(e.get("top_n") or 0)
                    lines.append(
                        f"##### {e.get('school')} "
                        f"（上位{use_n}平均 {g.fmt_time(e.get('average'), 1)} / "
                        f"{e.get('athlete_count')}人）"
                    )
                    lines.append("")
                    lines.append("| # | 選手 | 出走チーム | 区間 | 実績 | 差 | 判定 |")
                    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
                    for m in e.get("members") or []:
                        lines.append(
                            "| "
                            + " | ".join(
                                [
                                    str(m.get("slot") or ""),
                                    m.get("name") or "",
                                    m.get("team") or "",
                                    f"{m.get('leg')}区",
                                    g.fmt_time(m.get("actual"), 0)
                                    if m.get("actual") is not None
                                    else "",
                                    signed_sec(m.get("delta")),
                                    label_ja(m.get("class") or "unknown"),
                                ]
                            )
                            + " |"
                        )
                    lines.append("")
        else:
            lines.append("（該当なし）")
            lines.append("")
        lines.append("### 荒尾玉名関連：出走チーム成績")
        lines.append("")
        if arato_teams:
            lines.append("| 実順 | チーム | 実総合 | 予想総合 | 差 | 予想順 | 判定 | 補完 |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
            for t in arato_teams:
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            str(t.get("actual_rank") or ""),
                            t["team"],
                            g.fmt_clock(t.get("actual_total")),
                            g.fmt_clock(t.get("total_ref")),
                            signed_sec(t.get("total_delta")),
                            str(t.get("rank_ref") or ""),
                            label_ja(t["class"]),
                            "※" if t.get("imputed") else "",
                        ]
                    )
                    + " |"
                )
        else:
            lines.append("（該当なし）")
        lines.append("")
        lines.append(
            "- チーム判定: "
            + " / ".join(f"{label_ja(k)} {t_counts[k]}" for k in CLASS_ORDER)
        )
        lines.append("")
        lines.append("| 実順 | チーム | 実総合 | 予想総合 | 差 | 予想順 | 判定 | 補完 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for t in teams:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(t.get("actual_rank") or ""),
                        t["team"],
                        g.fmt_clock(t.get("actual_total")),
                        g.fmt_clock(t.get("total_ref")),
                        signed_sec(t.get("total_delta")),
                        str(t.get("rank_ref") or ""),
                        label_ja(t["class"]),
                        "※" if t.get("imputed") else "",
                    ]
                )
                + " |"
            )
        lines.append("")
        lines.append(f"### {gender} 区間ごと")
        lines.append("")
        lines.append("| チーム | 区間 | 選手 | 実績 | 予想 | 差 | 判定 | 備考 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for det in legs:
            lines.append(
                "| "
                + " | ".join(
                    [
                        det["team"],
                        f"{det['leg']}区",
                        det["name"],
                        g.fmt_time(det.get("actual"), 0) if det.get("actual") is not None else "",
                        g.fmt_time(det.get("pred"), 1) if det.get("pred") is not None else "",
                        signed_sec(det.get("delta")),
                        label_ja(det["class"]),
                        det.get("note") or "",
                    ]
                )
                + " |"
            )
        lines.append("")
    lines.append("## 注意")
    lines.append("")
    lines.append("トラック SB と駅伝は路面・気象・タスキ条件が異なる。換算式の後知恵検証用。")
    lines.append("")
    return "\n".join(lines)
