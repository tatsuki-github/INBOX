#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第3回熊本県ジュニア駅伝の区間オーダーに2026年度SB予想を付ける。"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from statistics import median
from xml.sax.saxutils import escape

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
import generate_nagomi_order_sb_preview as nagomi  # noqa: E402

MEET_DIR = ROOT / "input/external/drive/shared/大会/2026年度/0926_第４回県ジュニア陸上（第３回県ジュニア駅伝）"
EVENT_DATE = "2026-09-26"
AS_OF = "2026-09-24"
MEN_3000M_FALLBACK_THRESHOLD_SEC = 30.0
TAIMEI_ORDER_OVERRIDES = {
    ("女子", "チャンピオンシップ", 7, "岱明中"): {3: "増岡 里俐"},
    ("男子", "チャンピオンシップ", 7, "岱明中"): {1: "松野 凛空", 2: "山本 哲瑠"},
}
STARTER_OVERRIDES = {
    ("女子", "チャンピオンシップ", 13, "ＡＬＬ八代"): {4: "田本 凪"},
    ("男子", "チャンピオンシップ", 13, "県立八代中"): {5: "龍野 翔太郎"},
    ("女子", "チャレンジ", 48, "菊池南中B"): {1: "川口 結花"},
    ("女子", "チャレンジ", 27, "人吉二中"): {3: "吉村 虹奈"},
    # 村上葉侑は南関中B/C双方の補員欄にある。同一レースのためCのみ起用。
    ("男子", "チャレンジ", 29, "南関中C"): {2: "村上 葉侑"},
    ("男子", "チャレンジ", 49, "玉名中"): {4: "中村 龍之介"},
}

DIVISIONS = [
    {"gender": "女子", "division": "チャンピオンシップ", "pdf": "チャンピオンシップの部_スタートリスト.pdf", "pages": [0], "legs": 4, "first_km": 2.7, "other_km": 2.3},
    {"gender": "男子", "division": "チャンピオンシップ", "pdf": "チャンピオンシップの部_スタートリスト.pdf", "pages": [1], "legs": 5, "first_km": 3.0, "other_km": 2.6},
    {"gender": "女子", "division": "チャレンジ", "pdf": "チャレンジの部_スタートリスト.pdf", "pages": [0, 1], "legs": 4, "first_km": 2.7, "other_km": 2.3},
    {"gender": "男子", "division": "チャレンジ", "pdf": "チャレンジの部_スタートリスト.pdf", "pages": [2, 3], "legs": 5, "first_km": 3.0, "other_km": 2.6},
]


def clean_entry(value: str | None) -> str:
    return re.sub(r"[①②③➀➁➂]$", "", (value or "").strip())


def parse_division(spec: dict) -> list[dict]:
    entries: list[dict] = []
    pdf_path = MEET_DIR / spec["pdf"]
    with pdfplumber.open(pdf_path) as pdf:
        for page_index in spec["pages"]:
            tables = pdf.pages[page_index].extract_tables()
            if not tables:
                continue
            for table in tables:
                for row in table:
                    if not row or not (row[0] or "").strip().isdigit():
                        continue
                    if len(row) < 3 + spec["legs"]:
                        continue
                    n = int(row[0].strip())
                    team = (row[1] or "").strip()
                    legs = [clean_entry(row[3 + i]) for i in range(spec["legs"])]
                    key = (spec["gender"], spec["division"], n, team)
                    overrides = {**TAIMEI_ORDER_OVERRIDES.get(key, {}), **STARTER_OVERRIDES.get(key, {})}
                    for leg_number, athlete in overrides.items():
                        legs[leg_number - 1] = athlete
                    if len(legs) == spec["legs"] and all(legs):
                        entries.append({"no": n, "team": team, "legs": legs})
    # Avoid duplicates if the PDF extractor returns overlapping tables.
    unique = {(e["no"], e["team"]): e for e in entries}
    return list(unique.values())


def predict(name: str, gender: str, distance_km: float, sb_index: dict) -> tuple[float | None, dict, str]:
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
            return None, details, "記録なし"
        return base * distance_km / 2, details, note

    m1500, m800, m3000 = details["1500m"], details["800m"], details["3000m"]
    from_1500 = m1500.seconds * 2 + nagomi.MEN_1500_TO_3K_ADD if m1500 else None
    from_800 = m800.seconds * (3000 / 800) ** nagomi.RIEGEL * nagomi.MEN_800_TO_3K_COEF if m800 else None
    if m3000:
        if from_1500 is not None and m3000.seconds >= from_1500 + MEN_3000M_FALLBACK_THRESHOLD_SEC:
            base, note = from_1500, f"1500m SB→3km式を距離比例（3000m SBが+{m3000.seconds-from_1500:.0f}s遅い）"
        elif from_1500 is None and from_800 is not None and m3000.seconds >= from_800 + MEN_3000M_FALLBACK_THRESHOLD_SEC:
            base, note = from_800, "800m SB→3km式を距離比例（3000m SBが遅い）"
        else:
            base, note = m3000.seconds, "3000m SBを距離比例"
    elif from_1500 is not None:
        base, note = from_1500, "1500m SB→3km式を距離比例"
    elif from_800 is not None:
        base, note = from_800, "800m SB→3km式を距離比例"
    else:
        return None, details, "記録なし"
    return base * distance_km / 3, details, note


def rank_values(values: list[float | None]) -> list[int | None]:
    indexed = [(i, v) for i, v in enumerate(values) if v is not None]
    indexed.sort(key=lambda x: x[1])
    ranks: list[int | None] = [None] * len(values)
    previous: float | None = None
    place = 0
    for position, (idx, value) in enumerate(indexed, 1):
        if previous is None or abs(value - previous) > 1e-6:
            place = position
        ranks[idx] = place
        previous = value
    return ranks


def fmt_time(seconds: float | None, decimals: int = 1) -> str:
    if seconds is None:
        return "—"
    total = int(round(seconds * (10 ** decimals)))
    unit = 10 ** decimals
    mins, rem = divmod(total, 60 * unit)
    sec, frac = divmod(rem, unit)
    return f"{mins}:{sec:02d}" + (f".{frac:0{decimals}d}" if decimals else "")


def fmt_total(seconds: float) -> str:
    total = int(round(seconds))
    mins, sec = divmod(total, 60)
    return f"{mins}:{sec:02d}"


def make_report(spec: dict, sb_index: dict) -> tuple[list[str], list[dict], list[dict], list[float | None], list[dict], list[dict]]:
    teams = parse_division(spec)
    n_legs = spec["legs"]
    for team in teams:
        team["preds"] = []
        team["details"] = []
        for leg, name in enumerate(team["legs"], 1):
            distance = spec["first_km"] if leg == 1 else spec["other_km"]
            pred, marks, note = predict(name, spec["gender"], distance, sb_index)
            team["preds"].append(pred)
            team["details"].append({"leg": leg, "name": name, "km": distance, "pred": pred, "marks": marks, "note": note})

    section_ranks: list[list[int | None]] = []
    cum_ranks: list[list[int | None]] = []
    medians: list[float | None] = []
    for leg in range(n_legs):
        values = [team["preds"][leg] for team in teams]
        medians.append(median([v for v in values if v is not None]) if any(v is not None for v in values) else None)
        section_ranks.append(rank_values(values))
        cumulatives = [sum(t["preds"][i] for i in range(leg + 1)) if all(t["preds"][i] is not None for i in range(leg + 1)) else None for t in teams]
        cum_ranks.append(rank_values(cumulatives))
    for ti, team in enumerate(teams):
        for leg in range(n_legs):
            team["details"][leg]["section_rank"] = section_ranks[leg][ti]
            team["details"][leg]["cum_rank"] = cum_ranks[leg][ti]
        known_n = sum(v is not None for v in team["preds"])
        team["complete"] = known_n == n_legs
        team["total"] = sum(v for v in team["preds"] if v is not None) if team["complete"] else None
        team["total_ref"] = sum((team["preds"][i] if team["preds"][i] is not None else medians[i] or 0) for i in range(n_legs)) if known_n >= 2 else None
        team["imputed"] = team["total_ref"] is not None and not team["complete"]

    full = sorted((t for t in teams if t["total"] is not None), key=lambda t: t["total"])
    ref = sorted((t for t in teams if t["total_ref"] is not None), key=lambda t: t["total_ref"])
    for ordered, key in ((full, "rank_full"), (ref, "rank_ref")):
        for i, team in enumerate(ordered, 1):
            team[key] = i

    title = f"{spec['gender']} {spec['division']}"
    lines = [f"## {title}", "", f"対象チーム: {len(teams)} / 区間: {n_legs}", "", "### 総合予想順位（SB欠測は同区間中央値で補完、実SB予想が2区間以上）", ""]
    headers = ["順位", "No.", "チーム", "総合予想", "SB欠測"] + [f"{i}区 通過/区間" for i in range(1, n_legs + 1)]
    lines += ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for t in ref:
        cells = [str(t["rank_ref"]), str(t["no"]), t["team"], fmt_total(t["total_ref"]), "※" if t["imputed"] else ""]
        for d in t["details"]:
            cum = sum(t["preds"][:d["leg"]][i] if t["preds"][i] is not None else medians[i] or 0 for i in range(d["leg"]))
            cr = rank_values([sum(x["preds"][i] if x["preds"][i] is not None else medians[i] or 0 for i in range(d["leg"])) for x in teams])[teams.index(t)]
            sr_values = [x["preds"][d["leg"] - 1] if x["preds"][d["leg"] - 1] is not None else medians[d["leg"] - 1] for x in teams]
            sr = rank_values(sr_values)[teams.index(t)]
            split_time = fmt_time(d["pred"] if d["pred"] is not None else medians[d["leg"] - 1])
            if d["pred"] is None:
                split_time = f"({split_time})"
            cells.append(f"({cr or '—'}){fmt_time(cum)} / ({sr or '—'}){split_time}")
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "### 完全SB予想のみの総合順位", "", "| 順位 | No. | チーム | 総合予想 |", "| --- | --- | --- | --- |"]
    for t in full:
        lines.append(f"| {t['rank_full']} | {t['no']} | {t['team']} | {fmt_total(t['total'])} |")
    lines += ["", "### チーム別区間・SB詳細", ""]
    lookup = {t["no"]: t for t in teams}
    for t in teams:
        rank = t.get("rank_ref")
        rank_text = f"予想{rank}位" if rank else "総合順位対象外（SB予想が2区間未満）"
        if t.get("imputed"):
            rank_text += "・中央値補完"
        lines += [f"#### {t['no']} {t['team']}（{rank_text}）", "", "| 区 | 距離 | 選手 | 800m SB | 1500m SB | 3000m SB | 区間予想 | 区間順位 | 通過予想 | 通過順位 | 採用式 |", "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
        for d in t["details"]:
            details = d["marks"]
            leg_idx = d["leg"] - 1
            cum = sum(t["preds"][i] if t["preds"][i] is not None else medians[i] or 0 for i in range(d["leg"]))
            sr_values = [x["preds"][leg_idx] if x["preds"][leg_idx] is not None else medians[leg_idx] for x in teams]
            sr = rank_values(sr_values)[teams.index(t)]
            cum_values = [sum(x["preds"][i] if x["preds"][i] is not None else medians[i] or 0 for i in range(d["leg"])) for x in teams]
            cr = rank_values(cum_values)[teams.index(t)]
            marks = [details[x].text if details[x] else "—" for x in ("800m", "1500m", "3000m")]
            pred = fmt_time(d["pred"] if d["pred"] is not None else medians[leg_idx])
            if d["pred"] is None:
                pred = f"({pred})※"
            lines.append(f"| {d['leg']}区 | {d['km']:.1f}km | {d['name']} | {marks[0]} | {marks[1]} | {marks[2]} | {pred} | {sr or '—'} | {fmt_time(cum)} | {cr or '—'} | {d['note']} |")
        lines.append("")

    coverage = [{
        "gender": spec["gender"], "division": spec["division"], "no": t["no"], "team": t["team"],
        "predicted_legs": sum(v is not None for v in t["preds"]), "total_legs": n_legs,
        "reference_rank": t.get("rank_ref", ""), "complete_rank": t.get("rank_full", ""),
        "predicted_total_sec": round(t["total"], 1) if t["total"] is not None else "",
        "reference_total_sec": round(t["total_ref"], 1) if t["total_ref"] is not None else "",
        **{f"leg_{i+1}_athlete": t["legs"][i] for i in range(n_legs)},
        **{f"leg_{i+1}_pred_sec": round(t["preds"][i], 1) if t["preds"][i] is not None else "" for i in range(n_legs)},
    } for t in teams]
    return lines, coverage, teams, medians, ref, full


def render_pdf(reports: list[tuple[dict, list[dict], list[float | None], list[dict], list[dict]]], path: Path) -> None:
    """全4部門の順位と区間別SB詳細をまとめ、記録セルから記録大会へリンクする。"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font_name = "NotoSansJP"
    font_path = ROOT / "assets/fonts/NotoSansJP-Regular.ttf"
    if font_path.exists():
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
    else:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        font_name = "HeiseiKakuGo-W5"
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("JuniorTitle", parent=styles["Title"], fontName=font_name, fontSize=15, leading=19)
    section_style = ParagraphStyle("JuniorSection", parent=styles["Heading1"], fontName=font_name, fontSize=13, leading=16, spaceBefore=8, spaceAfter=5)
    team_style = ParagraphStyle("JuniorTeam", parent=styles["Heading3"], fontName=font_name, fontSize=8, leading=10, spaceBefore=5, spaceAfter=2)
    body_style = ParagraphStyle("JuniorBody", parent=styles["Normal"], fontName=font_name, fontSize=7, leading=9)
    cell_style = ParagraphStyle("JuniorCell", parent=styles["Normal"], fontName=font_name, fontSize=6.5, leading=8)
    small_style = ParagraphStyle("JuniorSmall", parent=cell_style, fontSize=5.6, leading=7)
    link_style = ParagraphStyle("JuniorLink", parent=cell_style, textColor=colors.HexColor("#1459A6"))

    def para(text: object, style=cell_style) -> Paragraph:
        return Paragraph(escape(str(text or "")).replace("\n", "<br/>"), style)

    def mark_para(mark: object) -> Any:
        if not mark:
            return para("—")
        label = escape(mark.text)
        if mark.url:
            href = escape(mark.url, {'"': "&quot;"})
            return Paragraph(f'<a href="{href}" color="#1459A6">{label}</a>', link_style)
        return para(label)

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(font_name, 7)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawString(9 * mm, 5 * mm, "2026年度SBによる参考予想 / 青色のSB記録をクリックすると記録掲載大会へ移動")
        canvas.drawRightString(landscape(A4)[0] - 9 * mm, 5 * mm, f"{doc.page}")
        canvas.restoreState()

    story: list[Any] = [para("第3回 熊本県ジュニア駅伝 2026年度SB・区間順位予想", title_style),
                        para("SB基準日 2026-09-24 / 大会日 2026-09-26。男子は3000m実測SBが1500m換算予想より30秒以上遅い場合に1500m換算を採用。SB記録セルのリンク先は各記録の掲載大会ページです。", body_style),
                        Spacer(1, 3 * mm)]
    for spec, teams, medians, ref, full in reports:
        n_legs = spec["legs"]
        gender, division = spec["gender"], spec["division"]
        story.append(para(f"{gender} {division}（{len(teams)}チーム）", section_style))
        story.append(para("参考総合順位。SBが2区間以上あるチームを対象とし、欠測区間は区間中央値で補完（※）。", body_style))
        summary_header = ["順位", "No.", "チーム", "予想合計", "補完"] + [f"{i}区 通過 / 区間" for i in range(1, n_legs + 1)]
        summary = [[para(h) for h in summary_header]]
        for team in ref:
            cells: list[Any] = [para(team.get("rank_ref")), para(team["no"]), para(team["team"]), para(fmt_total(team["total_ref"])), para("※" if team["imputed"] else "")]
            for det in team["details"]:
                leg_idx = det["leg"] - 1
                cum = sum(team["preds"][i] if team["preds"][i] is not None else medians[i] or 0 for i in range(det["leg"]))
                cum_values = [sum(t["preds"][i] if t["preds"][i] is not None else medians[i] or 0 for i in range(det["leg"])) for t in teams]
                cum_rank = rank_values(cum_values)[teams.index(team)]
                section_values = [t["preds"][leg_idx] if t["preds"][leg_idx] is not None else medians[leg_idx] for t in teams]
                section_rank = rank_values(section_values)[teams.index(team)]
                split = det["pred"] if det["pred"] is not None else medians[leg_idx]
                split_s = fmt_time(split)
                if det["pred"] is None:
                    split_s = f"({split_s})"
                cells.append(para(f"({cum_rank or '—'}){fmt_time(cum)} / ({section_rank or '—'}){split_s}", small_style))
            summary.append(cells)
        fixed_width = 77 * mm  # 順位・No.・チーム・合計・補完
        leg_w = (landscape(A4)[0] - 18 * mm - fixed_width) / n_legs
        widths = [10 * mm, 10 * mm, 32 * mm, 18 * mm, 7 * mm] + [leg_w] * n_legs
        tbl = Table(summary, colWidths=widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F6")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CDD5DF")),
            ("FONTNAME", (0, 0), (-1, -1), font_name), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.extend([tbl, Spacer(1, 2 * mm), para("完全SB順位", team_style)])
        complete_data = [[para(x) for x in ("順位", "No.", "チーム", "予想合計")]]
        complete_data.extend([[para(t["rank_full"]), para(t["no"]), para(t["team"]), para(fmt_total(t["total"]))] for t in full])
        complete = Table(complete_data, colWidths=[15 * mm, 15 * mm, 55 * mm, 25 * mm], repeatRows=1)
        complete.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F6")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CDD5DF")),
            ("FONTNAME", (0, 0), (-1, -1), font_name), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ]))
        story.append(complete)
        story.append(para("区間別詳細（SB記録クリックで掲載大会へ）", team_style))
        for team in teams:
            rank = f"予想{team['rank_ref']}位" if team.get("rank_ref") else "総合順位対象外"
            if team.get("imputed"):
                rank += "・中央値補完"
            team_story: list[Any] = [para(f"No.{team['no']} {team['team']} / {rank}", team_style)]
            headers = ["区", "選手", "800m SB", "1500m SB", "3000m SB", "区間予想", "区間順", "通過予想", "通過順", "換算式"]
            rows: list[list[Any]] = [[para(h) for h in headers]]
            for det in team["details"]:
                idx = det["leg"] - 1
                pred = det["pred"] if det["pred"] is not None else medians[idx]
                pred_text = fmt_time(pred)
                if det["pred"] is None:
                    pred_text = f"({pred_text})※"
                cum = sum(team["preds"][i] if team["preds"][i] is not None else medians[i] or 0 for i in range(det["leg"]))
                cum_values = [sum(t["preds"][i] if t["preds"][i] is not None else medians[i] or 0 for i in range(det["leg"])) for t in teams]
                cum_rank = rank_values(cum_values)[teams.index(team)]
                rows.append([para(f"{det['leg']}区"), para(det["name"]), mark_para(det["marks"].get("800m")), mark_para(det["marks"].get("1500m")), mark_para(det["marks"].get("3000m")), para(pred_text), para(det["section_rank"] or "—"), para(fmt_time(cum)), para(cum_rank or "—"), para(det["note"], small_style)])
            detail = Table(rows, colWidths=[9 * mm, 25 * mm, 17 * mm, 17 * mm, 17 * mm, 17 * mm, 10 * mm, 17 * mm, 10 * mm, 65 * mm], repeatRows=1)
            detail.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F4F7")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0D5DD")),
                ("FONTNAME", (0, 0), (-1, -1), font_name), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]))
            team_story.append(detail)
            story.append(KeepTogether(team_story))
        story.append(Spacer(1, 4 * mm))

    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), leftMargin=9 * mm, rightMargin=9 * mm, topMargin=9 * mm, bottomMargin=11 * mm,
                            title="第3回熊本県ジュニア駅伝 2026年度SB・区間予想")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main() -> int:
    women_sb, _ = nagomi.load_sb_index(as_of=AS_OF, gender="女子")
    men_sb, _ = nagomi.load_sb_index(as_of=AS_OF, gender="男子")
    all_lines = ["# 第3回 熊本県ジュニア駅伝競走大会 2026年度SB・区間順位予想", "", f"as_of: {AS_OF} / event_date: {EVENT_DATE}", "", "## 算出方法", "", "- SBは2026年度採用SB・Notion採用SB・玉名郡ナイターでSB明記された記録を対象日以前で照合。SB採用済みを優先。", "- 換算式は2026年なごみ駅伝と同じ。女子は1500m SBから2km予想 `SB秒×(2/1.5)+15`、1500mがなければ800m Riegel換算。男子は1500m SBから3km予想 `SB秒×2+35`、800m Riegel換算。男子の3000m実測SBが1500m換算予想より30秒以上遅い場合は1500m換算を採用。", "- 区間距離に合わせて2km/3km予想を距離比例で調整。女子1区2.7km・2-4区2.3km、男子1区3.0km・2-5区2.6km。2026要項はオープンコース距離（女子2.3km・男子2.6km）を記載し、駅伝1区距離は明記していないため、1区は2025年第2回大会の記録資料にある距離を踏襲した推定。", "- 岱明中と一部チームのオーダー変更は[区間オーダー変更.md](区間オーダー変更.md)に記録。SB予想は記録済みの最新オーダーを反映し、公式PDFの公表オーダーとは区別している。", "- 各区の区間順位は各部門内の換算予想順。通過順位は予想累計タイム順。総合順位は全区間の換算予想合計。", "- SB予想の欠測は区間ごとの中央値で参考総合順位を補完（※）。完全順位は全区間に実SB予想があるチームのみ。", ""]
    coverages = []
    pdf_reports = []
    for spec in DIVISIONS:
        sb = women_sb if spec["gender"] == "女子" else men_sb
        lines, coverage, teams, medians, ref, full = make_report(spec, sb)
        all_lines += lines
        coverages += coverage
        pdf_reports.append((spec, teams, medians, ref, full))
    (MEET_DIR / "区間オーダー_SB予想.md").write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    coverage_path = MEET_DIR / "区間オーダー_SB予想_coverage.csv"
    fields = list(coverages[0])
    with coverage_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(coverages)
    pdf_path = MEET_DIR / "区間オーダー_SB予想.pdf"
    render_pdf(pdf_reports, pdf_path)
    print(f"wrote {pdf_path}")
    for spec in DIVISIONS:
        teams = parse_division(spec)
        block = next(line for line in all_lines if line == f"## {spec['gender']} {spec['division']}")
        print(f"{block}: {len(teams)} teams")
    print(f"wrote {MEET_DIR / '区間オーダー_SB予想.md'}")
    print(f"wrote {coverage_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
