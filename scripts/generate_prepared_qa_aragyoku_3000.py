#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add ~3000 aragyoku-ekiden prepared FAQ entries (ADR 059).

Covers remaining knowledge heavily used for 「荒玉」questions:
  - last-year / all-year split_rank & passing_rank
  - leg awards ranks, meet records
  - 2026 thorough guide PDF (extracted text)
  - 2026 formula / order predictions, trial, recent track-ekiden results
  - focus-team & team-history digests, track SB rankings

Usage:
  python3 scripts/generate_prepared_qa_aragyoku_3000.py
  python3 scripts/generate_prepared_qa_aragyoku_3000.py --dry-run
  python3 scripts/generate_prepared_qa_aragyoku_3000.py --target 3000
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import entry, slug  # noqa: E402
from generate_prepared_qa_knowledge_1000 import take  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
TRANSCRIPTS = ROOT / "input" / "aragyoku" / "transcripts"
GUIDE_TXT = ROOT / "input" / "aragyoku" / "guides" / "荒玉駅伝2026徹底対策.extracted.txt"
GUIDE_PDF = ROOT / "outputs" / "荒玉駅伝2026徹底対策.pdf"
DEFAULT_YEAR = 2026
LAST_YEAR = 2025


def load_transcripts() -> list[dict]:
    out = []
    if not TRANSCRIPTS.exists():
        return out
    for p in sorted(TRANSCRIPTS.glob("*.json"), reverse=True):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    # Prefer recent years for 「昨年/今年」系の当たりやすさ
    out.sort(key=lambda d: (-int(d.get("year") or 0), d.get("gender") or ""))
    return out


def gen_split_ranks(existing_ids: set[str], limit: int) -> list[dict]:
    """Team×leg split_rank / passing_rank — 「昨年の区間順位」系。"""
    out: list[dict] = []
    for d in load_transcripts():
        year = int(d.get("year") or 0)
        gender = d.get("gender") or ""
        if not year or not gender:
            continue
        src = f"input/aragyoku/transcripts/{year}-{gender}.json"
        for team in d.get("teams") or []:
            tname = team.get("team") or ""
            if not tname:
                continue
            for lg in team.get("legs") or []:
                runner = (lg.get("name") or "").replace(" ", "")
                leg = lg.get("leg")
                split = lg.get("split") or "?"
                srank = lg.get("split_rank")
                prank = lg.get("passing_rank")
                grade = lg.get("grade")
                if not runner or not leg or not srank:
                    continue
                eid = f"aragyoku-{year}-{gender}-{slug(tname)}-leg{leg}-splitrank"
                if eid in existing_ids or any(e["id"] == eid for e in out):
                    continue
                qs = [
                    f"{year}年荒玉{gender}の{tname}{leg}区の区間順位は？",
                    f"{year}年荒玉駅伝{gender}{tname}{leg}区は何位？",
                    f"{tname}の{year}年荒玉{gender}{leg}区の区間順",
                ]
                if year == LAST_YEAR:
                    qs.extend(
                        [
                            f"昨年の荒玉{gender}{tname}{leg}区の区間順位は？",
                            f"去年の{tname}{gender}{leg}区は区間何位？",
                        ]
                    )
                gbit = f"{grade}年・" if grade else ""
                ans = (
                    f"{year}年荒玉駅伝{gender}・{tname}{leg}区は{runner}"
                    f"（{gbit}区間タイム{split}）で区間{srank}位です。"
                )
                if prank:
                    ans += f" 通過順位は{prank}位。"
                if lg.get("split_record"):
                    ans += " 区間新。"
                out.append(
                    entry(
                        eid,
                        qs,
                        ans,
                        [src, "out/analysis/aragyoku_leg_awards.md"],
                        ["aragyoku", "split-rank", gender, year, tname],
                    )
                )
                if len(out) >= limit:
                    return out
    return out


def gen_leg_rank_board(existing_ids: set[str], limit: int) -> list[dict]:
    """Per year/gender/leg: who was 1st–5th (区間順位表)."""
    out: list[dict] = []
    for d in load_transcripts():
        year = int(d.get("year") or 0)
        gender = d.get("gender") or ""
        src = f"input/aragyoku/transcripts/{year}-{gender}.json"
        by_leg: dict[int, list[dict]] = defaultdict(list)
        for team in d.get("teams") or []:
            tname = team.get("team") or ""
            for lg in team.get("legs") or []:
                if not lg.get("split_rank") or not lg.get("name"):
                    continue
                by_leg[int(lg["leg"])].append(
                    {
                        "team": tname,
                        "name": (lg.get("name") or "").replace(" ", ""),
                        "grade": lg.get("grade"),
                        "split": lg.get("split") or "?",
                        "rank": int(lg["split_rank"]),
                        "record": bool(lg.get("split_record")),
                    }
                )
        for leg, rows in sorted(by_leg.items()):
            rows = sorted(rows, key=lambda x: x["rank"])
            # full board entry
            eid_board = f"aragyoku-{year}-{gender}-leg{leg}-board"
            if eid_board not in existing_ids and not any(
                e["id"] == eid_board for e in out
            ):
                top = rows[:8]
                lines = [
                    f"{r['rank']}位 {r['name']}（{r['team']}・{r['split']}"
                    + ("・区間新" if r["record"] else "")
                    + ")"
                    for r in top
                ]
                qs = [
                    f"{year}年荒玉{gender}{leg}区の区間順位は？",
                    f"{year}年荒玉駅伝{gender}の{leg}区順位表",
                    f"{year}荒玉{gender}{leg}区の上位は誰？",
                    f"{year}年{gender}{leg}区の荒玉駅伝の区間順位",
                    f"{year}年の{gender}{leg}区の荒玉の区間順位は？",
                    f"{year}年荒玉駅伝の{gender}{leg}区の区間順位",
                ]
                if year == LAST_YEAR:
                    qs.extend(
                        [
                            f"昨年の荒玉{gender}{leg}区の区間順位は？",
                            f"去年の荒玉{gender}{leg}区の区間順位は？",
                            f"去年の{gender}{leg}区の荒玉駅伝の区間順位",
                            f"昨年の{gender}{leg}区の荒玉駅伝の区間順位",
                            f"去年の荒玉駅伝{gender}{leg}区の区間順位",
                            f"昨年の荒玉駅伝の{gender}{leg}区の区間順位は？",
                            f"去年の荒玉駅伝の{gender}の{leg}区の区間順位",
                        ]
                    )
                ans = (
                    f"{year}年荒玉駅伝{gender}{leg}区の区間順位（上位）です。\n"
                    + "\n".join(lines)
                )
                out.append(
                    entry(
                        eid_board,
                        qs,
                        ans,
                        [src, "out/analysis/aragyoku_leg_awards.md"],
                        ["aragyoku", "leg-board", gender, year],
                    )
                )
                if len(out) >= limit:
                    return out
            # individual ranks 1-5
            for r in rows:
                if r["rank"] > 5:
                    continue
                eid = f"aragyoku-{year}-{gender}-leg{leg}-rank{r['rank']}"
                if eid in existing_ids or any(e["id"] == eid for e in out):
                    continue
                # skip if identical to -best for rank1 already answered elsewhere — still useful distinct id
                label = "区間賞" if r["rank"] == 1 else f"区間{r['rank']}位"
                qs = [
                    f"{year}年荒玉{gender}{leg}区の{label}は誰？",
                    f"{year}年荒玉駅伝{gender}{leg}区{r['rank']}位は？",
                ]
                if year == LAST_YEAR:
                    qs.append(f"昨年の荒玉{gender}{leg}区の{label}は誰？")
                if r["rank"] == 1:
                    qs.append(f"{year}年荒玉{gender}{leg}区賞の名前と学年は？")
                gbit = f"{r['grade']}年・" if r["grade"] else ""
                ans = (
                    f"{year}年荒玉駅伝{gender}{leg}区の{label}は"
                    f"{r['name']}（{gbit}{r['team']}・{r['split']}）です。"
                )
                if r["record"]:
                    ans += " 区間新。"
                out.append(
                    entry(
                        eid,
                        qs,
                        ans,
                        [src, "out/analysis/aragyoku_leg_awards.md"],
                        ["aragyoku", "leg-award", gender, year],
                    )
                )
                if len(out) >= limit:
                    return out
    return out


def gen_meet_records(existing_ids: set[str], limit: int) -> list[dict]:
    path = ROOT / "out" / "analysis" / "aragyoku_meet_records.md"
    if not path.exists():
        return []
    out: list[dict] = []
    year = None
    gender = None
    for ln in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(\d{4})年\s+(男子|女子)\s*$", ln)
        if m:
            year, gender = int(m.group(1)), m.group(2)
            continue
        if not year or not gender:
            continue
        # narrative lines already written as Q&A answers
        if not ln.startswith(f"{year}年荒玉"):
            continue
        # parse total vs leg
        if "総合大会記録" in ln:
            eid = f"aragyoku-{year}-{gender}-meet-record-total"
            qs = [
                f"{year}年荒玉{gender}の大会記録は？",
                f"{year}年荒玉駅伝{gender}の総合大会記録",
                f"{year}荒玉{gender}のボード上部の総合記録",
            ]
        else:
            lm = re.search(r"(\d+)区大会区間記録", ln)
            if not lm:
                continue
            leg = lm.group(1)
            eid = f"aragyoku-{year}-{gender}-meet-record-leg{leg}"
            qs = [
                f"{year}年荒玉{gender}{leg}区の大会区間記録は誰？",
                f"荒玉駅伝{gender}の{leg}区大会記録（{year}年ボード）は？",
                f"{year}年荒玉{leg}区の区間記録保持者は？",
            ]
        if eid in existing_ids or any(e["id"] == eid for e in out):
            continue
        ans = ln if ln.endswith("。") else ln + "。"
        ans += " （ボード上部の歴代記録。当日の区間賞とは別です。）"
        out.append(
            entry(
                eid,
                qs,
                ans,
                ["out/analysis/aragyoku_meet_records.md"],
                ["aragyoku", "meet-record", gender, year],
            )
        )
        if len(out) >= limit:
            return out
    return out


def gen_guide_qa(existing_ids: set[str], limit: int) -> list[dict]:
    """Q&A from 荒玉駅伝2026徹底対策 PDF extract."""
    if not GUIDE_TXT.exists():
        return []
    text = GUIDE_TXT.read_text(encoding="utf-8")
    pages = re.split(r"\n===== PAGE\s+(\d+)\s+=====\n", text)
    # pages = [preamble, num1, body1, num2, body2, ...]
    out: list[dict] = []
    srcs = [
        "outputs/荒玉駅伝2026徹底対策.pdf",
        "input/aragyoku/guides/荒玉駅伝2026徹底対策.extracted.txt",
    ]
    # curated section seeds from known TOC
    seeds = [
        (
            "guide-2026-what",
            [
                "荒玉駅伝2026徹底対策とは？",
                "荒玉の完全ガイドは？",
                "徹底対策PDFの内容は？",
            ],
            "『荒玉駅伝2026 徹底対策』（outputs/荒玉駅伝2026徹底対策.pdf）は、"
            "歴代結果×2026走力×区間設計×練習×当日運用をまとめた117ページのガイドです。"
            "予測順位の断定ではなく、到達ラインと走力を分けて意思決定に使う資料です。"
            "データ基準日: 2026年8月29日（作成日2026年9月14日）。",
        ),
        (
            "guide-2026-toc",
            [
                "徹底対策の目次は？",
                "荒玉ガイドの章立ては？",
                "徹底対策PDFに何が載ってる？",
            ],
            "荒玉駅伝2026徹底対策の主な章は次のとおりです。"
            "0.まず読むべき結論 / 1.データ品質 / 2.大会プロファイルとコース設計 / "
            "3.歴代到達ライン / 4.2026走力と戦力 / 5.選考・区間配置 / "
            "6.練習 / 7.レース週・当日運用 / 付録（全年度結果・可視化など）。",
        ),
        (
            "guide-2026-distance",
            [
                "荒玉の区間距離は？（徹底対策）",
                "2026荒玉のコース距離の説明は？",
                "男子コース変更はいつ？",
            ],
            "徹底対策PDF 2章によると、男子は2024年に距離構成が変更されています"
            "（現行: 3 / 2.855 / 3 / 3 / 2.855 / 3 km、合計17.71km）。"
            "女子は 3 / 1.855 / 2 / 2 / 3 km（合計11.855km）で距離構成は一定です。"
            "歴代比較は距離補正したペースで行います。",
        ),
        (
            "guide-2026-disclaimer",
            [
                "荒玉の予想順位は当てになる？",
                "徹底対策の予測の注意点は？",
                "SBから駅伝タイムは換算できる？",
            ],
            "徹底対策PDFの注意: 予測順位を断定する資料ではありません。"
            "SBから駅伝タイムを一意に換算しません。出場確定・故障・当日状態は含まないため、"
            "最新のチーム編成・気象・体調で結果は変わります。",
        ),
        (
            "guide-2026-practice",
            [
                "荒玉に向けた練習の考え方は？",
                "徹底対策の練習章は？",
                "荒玉前の練習で避けることは？",
            ],
            "徹底対策6章では、区間特異性（区間距離に近い分割走・タスキ・風/単独走）、"
            "高負荷は週2回以内、レース週は新しい靴や補給を導入しない、"
            "痛みが増すなら質を中止して評価、などを示しています。",
        ),
        (
            "guide-2026-race-day",
            [
                "荒玉当日のチェックリストは？",
                "徹底対策の当日運用は？",
                "荒玉レース週に気をつけることは？",
            ],
            "徹底対策7章の当日チェック例: オーダーA/B/C、補員順、連絡網、ゼッケン、タスキ、"
            "靴下・予備靴、天気再確認。複数人が別作戦を指示しない。"
            "当日に初めてのサプリや新品シューズ導入は避ける、とあります。",
        ),
        (
            "guide-2026-order-protocol",
            [
                "荒玉の区間配置の考え方は？",
                "オーダー選定のプロトコルは？",
                "徹底対策の選考基準は？",
            ],
            "徹底対策5章: PBだけでなく後半低下・単独走・連続練習の回復を評価し、"
            "区間適性（短区間の立ち上がり、3km巡航、混戦）と選手の強みを一致させます。"
            "秒差シナリオでオーダーを比較し、速い選手を長区間へ機械的に置くのは避けます。",
        ),
    ]
    for eid, qs, ans in seeds:
        if eid in existing_ids:
            continue
        out.append(
            entry(eid, qs, ans, srcs, ["aragyoku", "guide", DEFAULT_YEAR])
        )

    # page-level digests for substantive pages (skip toc/footer-heavy)
    i = 1
    while i + 1 < len(pages):
        try:
            pnum = int(pages[i])
        except ValueError:
            i += 2
            continue
        body = pages[i + 1]
        i += 2
        if pnum < 7 or pnum > 90:
            continue
        # clean
        lines = []
        for ln in body.splitlines():
            t = ln.strip()
            if not t:
                continue
            if "徹底対策  |  根拠に基づく" in t:
                continue
            if re.fullmatch(r"\d+", t):
                continue
            if t.startswith("....") or set(t) <= {".", " ", "·"}:
                continue
            lines.append(t)
        if len(lines) < 4:
            continue
        # find a heading-like first line
        title = lines[0][:40]
        blob = " ".join(lines[:18])
        blob = re.sub(r"\s+", " ", blob)
        if len(blob) < 80:
            continue
        if len(blob) > 420:
            blob = blob[:419] + "…"
        eid = f"guide-2026-p{pnum}"
        if eid in existing_ids or any(e["id"] == eid for e in out):
            continue
        qs = [
            f"徹底対策PDFの{pnum}ページは？",
            f"荒玉ガイドp.{pnum}の内容は？",
            f"荒玉駅伝2026徹底対策「{title}」",
        ]
        ans = (
            f"荒玉駅伝2026徹底対策（p.{pnum}）より: {blob}"
        )
        if not ans.endswith(("。", "…", "？")):
            ans += "。"
        out.append(
            entry(eid, qs, ans, srcs, ["aragyoku", "guide", "page", DEFAULT_YEAR])
        )
        if len(out) >= limit:
            return out
    return out


def gen_formula_2026(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    base = ROOT / "out" / "analysis"
    report = base / "aragyoku_2026_formula_report.md"
    for gender, fname in (
        ("男子", "aragyoku_2026_formula_男子.csv"),
        ("女子", "aragyoku_2026_formula_女子.csv"),
    ):
        path = base / fname
        if not path.exists():
            continue
        by_team: dict[str, list[dict]] = defaultdict(list)
        with path.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                team = (r.get("team") or "").strip()
                if team:
                    by_team[team].append(r)
        for team, rows in sorted(by_team.items()):
            rows = sorted(rows, key=lambda x: int(float(x.get("leg") or 0)))
            eid = f"formula-2026-{gender}-{slug(team)}-order"
            if eid in existing_ids or any(e["id"] == eid for e in out):
                continue
            bits = []
            total_sec = 0.0
            for r in rows:
                name = (r.get("name") or "").replace(" ", "")
                leg = r.get("leg")
                t = r.get("formula_time") or "?"
                bits.append(f"{leg}区{name}（予想{t}）")
                try:
                    total_sec += float(r.get("formula_sec") or 0)
                except ValueError:
                    pass
            mm, ss = divmod(int(round(total_sec)), 60) if total_sec else (0, 0)
            qs = [
                f"2026年荒玉{gender}{team}の数式予想オーダーは？",
                f"今年の荒玉{gender}{team}の戦力予想は？",
                f"{team}の2026荒玉{gender}区間予想",
            ]
            required_legs = set(range(1, 7 if gender == "男子" else 6))
            predicted_legs = {int(r["leg"]) for r in rows if r.get("formula_sec")}
            complete = predicted_legs == required_legs
            total_label = "全区間の合計目安" if complete else f"予想のある{len(predicted_legs)}区間のみの小計"
            incomplete_note = "" if complete else " 未収録区間があるため、総合タイムは算出できません。"
            ans = (
                f"2026年荒玉駅伝{gender}・{team}の数式予想（仮オーダー含む）です。"
                f" {total_label} {mm}:{ss:02d}。" + incomplete_note + " " + "、".join(bits) + "。"
                " 断定順位ではなく、直近レース観測に基づく説明可能な予想です。"
            )
            srcs = [str(path.relative_to(ROOT))]
            if report.exists():
                srcs.append("out/analysis/aragyoku_2026_formula_report.md")
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    srcs,
                    ["aragyoku", "formula", "2026", gender, team],
                )
            )
            if len(out) >= limit:
                return out
            # per-leg
            for r in rows:
                name = (r.get("name") or "").replace(" ", "")
                leg = r.get("leg")
                eid2 = f"formula-2026-{gender}-{slug(team)}-leg{leg}"
                if eid2 in existing_ids or any(e["id"] == eid2 for e in out):
                    continue
                qs = [
                    f"2026年荒玉{gender}{team}{leg}区の予想は？",
                    f"{team}の{leg}区予想タイム（2026荒玉{gender}）",
                ]
                ans = (
                    f"2026年荒玉{gender}・{team}{leg}区の数式予想は"
                    f"{name}・{r.get('formula_time')} です。"
                )
                if r.get("latest_race"):
                    ans += f" 直近レース: {r.get('latest_race')}。"
                if r.get("human_adjustment"):
                    note = str(r["human_adjustment"]).strip()
                    if note:
                        ans += f" 調整注記: {note[:120]}。"
                out.append(
                    entry(
                        eid2,
                        qs,
                        ans,
                        [str(path.relative_to(ROOT))],
                        ["aragyoku", "formula", "2026", gender],
                    )
                )
                if len(out) >= limit:
                    return out
    # meet folder digests
    meet_dir = (
        ROOT
        / "input"
        / "idaten-corpus"
        / "drive-text"
        / "大会"
        / "2026年度"
        / "1014-1015_荒玉中体連駅伝"
    )
    for name, qs0, tag in (
        (
            "概要.md",
            ["2026年の荒玉駅伝はいつ？", "今年の荒玉中体連駅伝の概要は？", "荒玉2026の大会情報"],
            "overview",
        ),
        (
            "校別展開_数式予想.md",
            [
                "2026荒玉の校別展開予想は？",
                "今年の荒玉戦力分析（校別）は？",
                "荒玉2026の数式予想まとめ",
            ],
            "school-expand",
        ),
        (
            "男子区間オーダー_数式予想.md",
            [
                "2026荒玉男子の区間オーダー予想は？",
                "今年の荒玉男子オーダー予想",
            ],
            "men-order",
        ),
        (
            "女子区間オーダー_数式予想.md",
            [
                "2026荒玉女子の区間オーダー予想は？",
                "今年の荒玉女子オーダー予想",
            ],
            "women-order",
        ),
        (
            "岱明_暫定区間オーダー.md",
            [
                "岱明の2026荒玉暫定オーダーは？",
                "今年の岱明荒玉オーダー（暫定）",
            ],
            "daiming-order",
        ),
    ):
        p = meet_dir / name
        if not p.exists():
            continue
        eid = f"meet-2026-aragyoku-{tag}"
        if eid in existing_ids or any(e["id"] == eid for e in out):
            continue
        lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        keep = []
        for ln in lines[:40]:
            if ln.startswith("#") or ln.startswith("```"):
                continue
            if re.search(r"\d|区|位|予想|オーダー|総合|km", ln):
                keep.append(re.sub(r"\s+", " ", ln)[:120])
        summary = " ".join(keep[:10])
        if len(summary) > 360:
            summary = summary[:359] + "…"
        ans = f"2026年荒玉中体連駅伝の「{name}」より。 {summary}"
        if not ans.endswith(("。", "…")):
            ans += "。"
        ans += " 仮置き・予想を含み、確定オーダーではありません。"
        out.append(
            entry(
                eid,
                qs0,
                ans,
                [str(p.relative_to(ROOT))],
                ["aragyoku", "preview", "2026", tag],
            )
        )
        if len(out) >= limit:
            return out
    return out


def gen_recent_and_trial(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    # trial
    trial_md = ROOT / "out" / "analysis" / "2026-09-29_aragyoku_trial_results.md"
    trial_json = ROOT / "out" / "analysis" / "2026-09-29_aragyoku_trial_results.json"
    if trial_json.exists():
        data = json.loads(trial_json.read_text(encoding="utf-8"))
        eid = "trial-2026-daiming-aragyoku"
        if eid not in existing_ids:
            lines = []
            for r in data.get("records") or []:
                name = (r.get("name") or r.get("reported_name") or "").strip()
                if not name or name == "None":
                    continue
                lines.append(
                    f"{r.get('leg')}区{name} {r.get('time')}"
                    + (
                        f"（ラップ {'/'.join(r.get('laps') or [])}）"
                        if r.get("laps")
                        else ""
                    )
                )
            qs = [
                "荒玉の試走結果は？",
                "岱明の荒玉試走タイムは？",
                "2026年9月29日の荒玉試走は？",
                "今年の荒玉コース試走",
            ]
            ans = (
                f"{data.get('event')}（{data.get('date')}）の記録です。\n"
                + "\n".join(lines)
            )
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [
                        "out/analysis/2026-09-29_aragyoku_trial_results.json",
                        "out/analysis/2026-09-29_aragyoku_trial_results.md",
                    ],
                    ["aragyoku", "trial", 2026],
                )
            )
    # recent results
    recent_path = ROOT / "out" / "analysis" / "aragyoku_2026_recent_results.json"
    if recent_path.exists():
        rows = json.loads(recent_path.read_text(encoding="utf-8"))
        # athlete × event
        groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in rows:
            name = (r.get("name") or "").replace(" ", "")
            ev = (r.get("event") or "").strip()
            if not name or not ev:
                continue
            groups[(name, short_event(ev))].append(r)
        for (name, sev), rs in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
            eid = f"recent-2026-{slug(name)}-{slug(sev)}"
            if eid in existing_ids or any(e["id"] == eid for e in out):
                continue
            lines = []
            aff = ""
            for r in rs:
                aff = r.get("team") or r.get("affiliation") or aff
                bit = f"{r.get('date')} {r.get('discipline') or r.get('distance_km')} {r.get('result')}"
                if r.get("note"):
                    bit += f"（{r['note']}）"
                if r.get("url") and str(r["url"]).startswith("http"):
                    bit += f" 大会結果: {r['url']}"
                lines.append(bit)
            qs = [
                f"{name}の{sev}の結果は？",
                f"2026年{name}の{sev}",
                f"{name}のトラック/駅伝シーズン（{sev}）",
            ]
            ans = (
                f"{name}"
                + (f"（{aff}）" if aff else "")
                + f"の2026年度・{sev}の結果です。\n"
                + "\n".join(lines)
            )
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    ["out/analysis/aragyoku_2026_recent_results.json"],
                    ["aragyoku", "recent", "2026", sev],
                )
            )
            if len(out) >= limit:
                return out
    _ = trial_md
    return out


def short_event(ev: str) -> str:
    e = re.sub(r"\s+", " ", ev)
    if "なごみ" in e:
        return "なごみ大会"
    if "ジュニア" in e:
        return "県ジュニア"
    if "長距離記録会" in e:
        return "長距離記録会"
    if "通信" in e:
        return "通信陸上"
    if "ナイター" in e:
        return "玉名郡ナイター"
    if "中体連" in e or "総合体育" in e:
        return "中体連"
    if "選手権" in e:
        return "県中学選手権"
    if "試走" in e:
        return "荒玉試走"
    return e[:18] + ("…" if len(e) > 18 else "")


def gen_focus_and_teams(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    focus = ROOT / "out" / "analysis" / "aragyoku_2024_2025_focus_teams.md"
    if focus.exists():
        text = focus.read_text(encoding="utf-8")
        # narrative lines that look like answers
        for ln in text.splitlines():
            ln = ln.strip()
            if not re.match(r".{2,40}の荒玉駅伝", ln):
                continue
            if len(ln) < 20:
                continue
            # build id from start
            eid = f"focus-{slug(ln[:48])}"
            if eid in existing_ids or any(e["id"] == eid for e in out):
                continue
            # invent questions from content
            m = re.match(
                r"(.+?)の荒玉駅伝(男子|女子)は(\d{4})年",
                ln,
            )
            if m:
                team, gender, y1 = m.group(1), m.group(2), m.group(3)
                qs = [
                    f"{team}の荒玉{gender}（2024-2025）はどうだった？",
                    f"{team}の荒玉駅伝{gender}の前年比は？",
                    f"2024と2025の{team}{gender}",
                ]
            else:
                qs = [ln[:40] + "？", "荒玉2024-2025深掘り: " + ln[:30]]
            ans = ln if ln.endswith("。") else ln + "。"
            out.append(
                entry(
                    eid,
                    qs,
                    ans + " 詳細は2024–2025深掘り分析を参照。",
                    ["out/analysis/aragyoku_2024_2025_focus_teams.md"],
                    ["aragyoku", "focus", "2024", "2025"],
                )
            )
            if len(out) >= limit // 3:
                break

    teams_dir = ROOT / "out" / "analysis" / "aragyoku-teams"
    if teams_dir.exists():
        for p in sorted(teams_dir.glob("*.md")):
            if p.name == "INDEX.md":
                continue
            team = p.stem
            year = None
            gender = None
            buf_rank = buf_total = None
            for ln in p.read_text(encoding="utf-8").splitlines():
                m = re.match(r"^##\s+(\d{4})年\s+(男子|女子)\s*$", ln)
                if m:
                    # flush previous narrative handled below via dedicated lines
                    year, gender = int(m.group(1)), m.group(2)
                    buf_rank = buf_total = None
                    continue
                if year and gender:
                    if ln.startswith("- 順位:"):
                        mm = re.search(r"(\d+)位", ln)
                        if mm:
                            buf_rank = mm.group(1)
                    if ln.startswith("- 総合:"):
                        mm = re.search(r"\*\*([0-9:]+)\*\*", ln)
                        if mm:
                            buf_total = mm.group(1)
                    # ready narrative
                    if ln.startswith(f"{year}年荒玉駅伝{gender}"):
                        eid = f"teamhist-{year}-{gender}-{slug(team)}"
                        if eid in existing_ids or any(e["id"] == eid for e in out):
                            continue
                        qs = [
                            f"{year}年荒玉{gender}の{team}は何位？",
                            f"{team}の{year}年荒玉{gender}の成績は？",
                            f"{year}荒玉{gender}{team}の結果",
                        ]
                        if year == LAST_YEAR:
                            qs.append(f"昨年の荒玉{gender}{team}は何位？")
                        ans = ln if ln.endswith("。") else ln + "。"
                        out.append(
                            entry(
                                eid,
                                qs,
                                ans,
                                [str(p.relative_to(ROOT))],
                                ["aragyoku", "team-history", gender, year, team],
                            )
                        )
                        if len(out) >= limit:
                            return out
                _ = (buf_rank, buf_total)
    return out


def gen_track_rankings(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    files = [
        (
            "out/analysis/2026_aragyoku_men_3000m_sb_ranking.md",
            "男子",
            "3000m",
            [
                "荒玉地区で3000mが一番速いのは？",
                "今年の荒玉男子3000mSBランキングは？",
                "2026年荒玉地区男子3000m順位",
            ],
        ),
        (
            "out/analysis/2026_aragyoku_men_1500m_sb_individual_top20.md",
            "男子",
            "1500m",
            [
                "今年の荒玉地区の男子1500mSBランキングトップ20は？",
                "荒玉男子1500mSB上位は？",
                "2026年荒玉1500mランキング",
            ],
        ),
        (
            "out/analysis/2026_men_1500m_pb_school_ranking.md",
            "男子",
            "1500m校別",
            [
                "荒玉男子1500mの学校別ランキングは？",
                "2026年男子1500m校別PB",
            ],
        ),
        (
            "out/analysis/2026_women_800m_1500m_pb_school_ranking.md",
            "女子",
            "800m/1500m校別",
            [
                "荒玉女子の800m/1500m校別ランキングは？",
                "2026年女子トラック校別PB",
            ],
        ),
        (
            "out/analysis/2026-09-21_arato-tamana_middle_school_sb_updates.md",
            "",
            "SB更新",
            [
                "荒玉の最近のSB更新者は？",
                "2026年9月の荒玉SB更新一覧",
            ],
        ),
    ]
    for rel, gender, dist, qs in files:
        path = ROOT / rel
        if not path.exists():
            continue
        eid = f"track-2026-{slug(gender + dist)}"
        if eid in existing_ids or any(e["id"] == eid for e in out):
            continue
        lines = [
            ln.strip()
            for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")
        ]
        # keep table-ish / ranked lines
        keep = []
        for ln in lines:
            if ln.startswith("|") and "---" not in ln and "順位" not in ln and "選手" not in ln:
                cells = [c.strip() for c in ln.strip("|").split("|")]
                if len(cells) >= 4 and re.match(r"\d+", cells[0]):
                    keep.append(
                        f"{cells[0]}位 {cells[1]}（{cells[2]}） {cells[3]}"
                    )
            elif re.match(r"^\d+\.\s", ln) or "更新" in ln:
                keep.append(ln[:120])
        if not keep:
            keep = [ln[:120] for ln in lines[:12] if not ln.startswith("|")]
        summary = "\n".join(keep[:20])
        ans = f"2026年度・荒玉地区の{gender}{dist}です。\n{summary}"
        out.append(
            entry(
                eid,
                qs,
                ans,
                [rel],
                ["aragyoku", "track", "sb", "2026", dist],
            )
        )
        if len(out) >= limit:
            return out

        # top1 dedicated
        if keep and "位" in keep[0]:
            eid1 = eid + "-top1"
            if eid1 not in existing_ids and not any(e["id"] == eid1 for e in out):
                out.append(
                    entry(
                        eid1,
                        [
                            f"荒玉地区{gender}{dist}の1位は誰？",
                            f"今年{gender}{dist}トップは？",
                        ],
                        f"{keep[0]}。出典: {rel}",
                        [rel],
                        ["aragyoku", "track", "2026"],
                    )
                )
    return out


def gen_analysis_ocr(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    files = [
        (
            "input/external/drive/shared/分析/2026年度荒玉男子.ocr.md",
            "男子",
            [
                "2026年荒玉男子の分析PDFは？",
                "荒玉男子戦力分析（2026）",
                "今年の荒玉男子分析資料",
            ],
        ),
        (
            "input/external/drive/shared/分析/2026年荒玉女子.ocr.md",
            "女子",
            [
                "2026年荒玉女子の分析PDFは？",
                "荒玉女子戦力分析（2026）",
                "今年の荒玉女子分析資料",
            ],
        ),
    ]
    for rel, gender, qs in files:
        path = ROOT / rel
        if not path.exists():
            continue
        eid = f"analysis-ocr-2026-{gender}"
        if eid in existing_ids:
            continue
        lines = [
            ln.strip()
            for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if ln.strip()
        ]
        keep = [
            ln
            for ln in lines[:60]
            if re.search(r"\d|区|位|予想|総合|タイム|SB|km", ln)
        ]
        summary = re.sub(r"\s+", " ", " ".join(keep[:12]))
        if len(summary) > 380:
            summary = summary[:379] + "…"
        ans = (
            f"2026年荒玉{gender}の分析資料（OCR）より。 {summary}"
        )
        if not ans.endswith(("。", "…")):
            ans += "。"
        pdf = rel.replace(".ocr.md", ".pdf")
        out.append(
            entry(
                eid,
                qs,
                ans,
                [rel, pdf],
                ["aragyoku", "analysis", "2026", gender],
            )
        )
        # chunk every ~40 lines into extra Qs
        for i in range(0, min(len(lines), 400), 40):
            chunk = lines[i : i + 40]
            useful = [
                ln
                for ln in chunk
                if re.search(r"区|位|選手|タイム|予想|総合|\d:\d{2}", ln)
            ]
            if len(useful) < 3:
                continue
            eidc = f"analysis-ocr-2026-{gender}-c{i//40}"
            if eidc in existing_ids or any(e["id"] == eidc for e in out):
                continue
            blob = " ".join(useful[:10])
            blob = re.sub(r"\s+", " ", blob)
            if len(blob) > 360:
                blob = blob[:359] + "…"
            out.append(
                entry(
                    eidc,
                    [
                        f"2026荒玉{gender}分析の続き（パート{i//40+1}）",
                        f"荒玉{gender}戦力メモ{i//40+1}",
                    ],
                    f"2026年荒玉{gender}分析OCR（パート{i//40+1}）: {blob}",
                    [rel],
                    ["aragyoku", "analysis", "2026", gender],
                )
            )
            if len(out) >= limit:
                return out
    return out


def gen_pace_and_misc(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    # average pace doc - year×gender summary lines
    path = ROOT / "out" / "analysis" / "aragyoku_all_teams_average_pace.md"
    if path.exists():
        year = gender = None
        for ln in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^##\s+(\d{4})年\s+(男子|女子)", ln)
            if m:
                year, gender = int(m.group(1)), m.group(2)
                continue
            if year and gender and ("平均" in ln or "ペース" in ln) and len(ln) > 15:
                eid = f"pace-{year}-{gender}-{slug(ln[:40])}"
                if eid in existing_ids or any(e["id"] == eid for e in out):
                    continue
                if not re.search(r"\d", ln):
                    continue
                qs = [
                    f"{year}年荒玉{gender}の平均ペースは？",
                    f"{year}荒玉{gender}の区間平均",
                ]
                if year == LAST_YEAR:
                    qs.append(f"昨年の荒玉{gender}平均ペースは？")
                out.append(
                    entry(
                        eid,
                        qs,
                        (ln if ln.endswith("。") else ln + "。"),
                        ["out/analysis/aragyoku_all_teams_average_pace.md"],
                        ["aragyoku", "pace", year, gender],
                    )
                )
                if len(out) >= limit // 2:
                    break

    overview = ROOT / "out" / "analysis" / "aragyoku-overview.md"
    if overview.exists():
        eid = "aragyoku-overview-guide"
        if eid not in existing_ids:
            text = overview.read_text(encoding="utf-8")
            lines = [
                ln.strip()
                for ln in text.splitlines()
                if ln.strip() and not ln.startswith("#")
            ]
            ans = "荒玉駅伝の概要です。 " + " ".join(lines[:12])
            ans = re.sub(r"\s+", " ", ans)
            if len(ans) > 400:
                ans = ans[:399] + "…"
            out.append(
                entry(
                    eid,
                    [
                        "荒玉駅伝の概要は？",
                        "荒玉の基本情報をまとめて",
                        "荒玉駅伝ってどんな大会？（概要ドキュメント）",
                    ],
                    ans,
                    ["out/analysis/aragyoku-overview.md"],
                    ["aragyoku", "overview"],
                )
            )

    # top2 finish counts
    top2 = ROOT / "out" / "analysis" / "aragyoku_top2_finish_counts.md"
    if top2.exists():
        eid = "aragyoku-top2-counts"
        if eid not in existing_ids and not any(e["id"] == eid for e in out):
            lines = [
                ln.strip()
                for ln in top2.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.startswith("#")
            ][:15]
            out.append(
                entry(
                    eid,
                    [
                        "荒玉で表彰台が多い学校は？",
                        "歴代で2位以内が多いのは？",
                        "荒玉の強豪校ランキング",
                    ],
                    "荒玉駅伝の2位以内回数の整理です。 " + " ".join(lines),
                    ["out/analysis/aragyoku_top2_finish_counts.md"],
                    ["aragyoku", "history"],
                )
            )
    return out[:limit]


def build_new_entries(existing_ids: set[str], target: int) -> list[dict]:
    used = set(existing_ids)
    buckets = {
        "split_ranks": gen_split_ranks(existing_ids, 2400),
        "leg_board": gen_leg_rank_board(existing_ids, 900),
        "meet_records": gen_meet_records(existing_ids, 250),
        "guide": gen_guide_qa(existing_ids, 250),
        "formula": gen_formula_2026(existing_ids, 250),
        "recent": gen_recent_and_trial(existing_ids, 250),
        "focus_teams": gen_focus_and_teams(existing_ids, 500),
        "track": gen_track_rankings(existing_ids, 40),
        "ocr": gen_analysis_ocr(existing_ids, 80),
        "pace_misc": gen_pace_and_misc(existing_ids, 80),
    }
    for k, v in buckets.items():
        print(f"  bucket {k}: {len(v)}")

    quotas = [
        ("split_ranks", 1600),
        ("leg_board", 500),
        ("focus_teams", 280),
        ("guide", 180),
        ("formula", 160),
        ("recent", 160),
        ("meet_records", 120),
        ("ocr", 40),
        ("track", 20),
        ("pace_misc", 20),
    ]
    selected: list[dict] = []
    for name, n in quotas:
        got = take(buckets[name], n, used)
        selected.extend(got)
        print(f"  took {name}: {len(got)}/{n}")

    if len(selected) < target:
        for name, _ in quotas:
            if len(selected) >= target:
                break
            selected.extend(take(buckets[name], target - len(selected), used))
    if len(selected) < target:
        for name in (
            "split_ranks",
            "leg_board",
            "focus_teams",
            "guide",
            "formula",
            "recent",
            "meet_records",
        ):
            if len(selected) >= target:
                break
            selected.extend(take(buckets[name], target - len(selected), used))

    print(f"  FINAL new: {len(selected[:target])}")
    return selected[:target]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--target", type=int, default=3000)
    args = parser.parse_args()

    # ensure guide extract exists
    if not GUIDE_TXT.exists() and GUIDE_PDF.exists():
        GUIDE_TXT.parent.mkdir(parents=True, exist_ok=True)
        try:
            from pypdf import PdfReader

            r = PdfReader(str(GUIDE_PDF))
            parts = []
            for i, p in enumerate(r.pages):
                parts.append(f"\n\n===== PAGE {i+1} =====\n" + (p.extract_text() or ""))
            GUIDE_TXT.write_text("".join(parts), encoding="utf-8")
            print(f"extracted guide -> {GUIDE_TXT.relative_to(ROOT)}")
        except Exception as exc:
            print("guide extract failed:", exc)

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = data.get("entries") or []
    existing_ids = {e["id"] for e in entries}
    print(f"existing entries: {len(entries)}")

    new_entries = build_new_entries(existing_ids, args.target)
    if len(new_entries) < args.target:
        raise SystemExit(f"expected {args.target}, got {len(new_entries)}")

    existing_q = {q for e in entries for q in (e.get("questions") or [])}
    cleaned: list[dict] = []
    for e in new_entries:
        qs = [q for q in e["questions"] if q not in existing_q]
        if not qs:
            continue
        e = dict(e)
        e["questions"] = qs
        cleaned.append(e)
        for q in qs:
            existing_q.add(q)

    if len(cleaned) < args.target:
        more = build_new_entries(
            existing_ids | {e["id"] for e in cleaned},
            args.target - len(cleaned) + 300,
        )
        have = {e["id"] for e in cleaned} | existing_ids
        for e in more:
            if e["id"] in have:
                continue
            qs = [q for q in e["questions"] if q not in existing_q]
            if not qs:
                continue
            e = dict(e)
            e["questions"] = qs
            cleaned.append(e)
            have.add(e["id"])
            for q in qs:
                existing_q.add(q)
            if len(cleaned) >= args.target:
                break

    cleaned = cleaned[: args.target]
    if len(cleaned) < args.target:
        raise SystemExit(f"after cleanup expected {args.target}, got {len(cleaned)}")

    merged = list(entries) + cleaned
    seen: set[str] = set()
    uniq = []
    for e in merged:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        uniq.append(e)

    data["entries"] = uniq
    data["total"] = len(uniq)
    note = data.get("note") or ""
    if "荒玉特化+3000" not in note:
        data["note"] = (
            note.rstrip()
            + "\n荒玉特化+3000（区間順位・戦力分析・徹底対策PDF・数式予想・トラック結果）。\n"
        )
    print(f"merged total {len(uniq)} (+{len(cleaned)})")
    for sid in (
        "aragyoku-2025-男子-岱明-leg2-splitrank",
        "guide-2026-what",
        "formula-2026-男子-岱明-order",
        "trial-2026-daiming-aragyoku",
    ):
        e = next((x for x in cleaned if x["id"] == sid), None)
        if e:
            print("SAMPLE", e["id"], e["answer"][:220].replace("\n", " | "))

    if args.dry_run:
        return 0

    FAQ.write_text(
        yaml.dump(
            data,
            allow_unicode=True,
            sort_keys=False,
            width=120,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {FAQ.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
