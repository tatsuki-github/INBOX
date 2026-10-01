#!/usr/bin/env python3
"""Add ~3000 knowledge-covering prepared FAQ entries (ADR 059).

Extends coverage beyond generate_prepared_qa_knowledge_1000.py:
  - all aragyoku legs/ranks (all teams/years)
  - school×distance SB by year (2012–2026)
  - meet docs, broader calendar, pace matrix, quiz/practice remainder

Usage:
  python3 scripts/generate_prepared_qa_knowledge_3000.py
  python3 scripts/generate_prepared_qa_knowledge_3000.py --dry-run
  python3 scripts/generate_prepared_qa_knowledge_3000.py --target 3000
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import (  # noqa: E402
    EVENTS_2025,
    EVENTS_2026,
    FOCUS_TEAMS,
    MEN_FULL,
    WOMEN_FULL,
    clean_user_facing_text,
    drive_url_for_calendar,
    entry,
    friendly_calendar_answer,
    gen_practice_notes,
    gen_quiz,
    load_drive_meet_folder_map,
    load_years,
    resolve_drive_meet_url,
    slug,
)
from generate_prepared_qa_knowledge_1000 import (  # noqa: E402
    load_keywords,
    take,
)

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
BY_YEAR = ROOT / "input" / "external" / "sb" / "middle-school" / "by-year"
DEFAULT_YEAR = 2026


def gen_all_aragyoku_legs(existing_ids: set[str], limit: int) -> list[dict]:
    """Every team × year × leg not already covered."""
    out: list[dict] = []
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        years = load_years(path)
        for year in sorted(years.keys(), reverse=True):
            for team in years[year].get("teams") or []:
                name = team.get("team") or ""
                if not name:
                    continue
                for lg in team.get("legs") or []:
                    runner = (lg.get("name") or "").replace(" ", "")
                    leg_no = lg.get("leg")
                    split = lg.get("split") or "?"
                    if not runner or not leg_no:
                        continue
                    eid = f"aragyoku-{year}-{gender}-{slug(name)}-leg{leg_no}"
                    if eid in existing_ids:
                        continue
                    qs = [
                        f"{year}年荒玉駅伝{gender}の{name}{leg_no}区は誰？",
                        f"{year}年荒玉{gender}{name}の{leg_no}区走者は？",
                        f"{year}年の{name}{gender}{leg_no}区は？",
                    ]
                    ans = (
                        f"{year}年荒玉駅伝{gender}の{name}{leg_no}区は{runner}"
                        f"（区間タイム{split}）です。"
                    )
                    out.append(
                        entry(
                            eid,
                            qs,
                            ans,
                            [src],
                            ["aragyoku", "leg", gender, int(year), name],
                        )
                    )
                    if len(out) >= limit:
                        return out
    return out


def gen_all_aragyoku_ranks(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        years = load_years(path)
        for year in sorted(years.keys(), reverse=True):
            for team in years[year].get("teams") or []:
                name = team.get("team") or ""
                rank = team.get("rank")
                if not name or not rank:
                    continue
                eid = f"aragyoku-{year}-{gender}-team-{slug(name)}-rank"
                if eid in existing_ids:
                    continue
                total = team.get("total") or "?"
                leg_bits = []
                for lg in team.get("legs") or []:
                    if lg.get("name"):
                        leg_bits.append(f"{lg.get('leg')}区{lg['name']}")
                legs = "、".join(leg_bits[:6])
                qs = [
                    f"{year}年荒玉駅伝{gender}の{name}は何位？",
                    f"{year}年荒玉{gender}{name}の順位は？",
                    f"{year}年の荒玉{gender}で{name}の成績は？",
                ]
                ans = f"{year}年荒玉駅伝{gender}の{name}は{rank}位（{total}）です。"
                if legs:
                    ans += f" 区間: {legs}。"
                out.append(
                    entry(
                        eid,
                        qs,
                        ans,
                        [src],
                        ["aragyoku", "team", gender, int(year)],
                    )
                )
                if len(out) >= limit:
                    return out
    return out


def gen_school_sb_all_years(existing_ids: set[str], limit: int) -> list[dict]:
    keywords = load_keywords()
    out: list[dict] = []
    # Prefer recent years first
    for year in range(DEFAULT_YEAR, 2011, -1):
        path = BY_YEAR / f"{year}-sb-adopted.json"
        if not path.exists():
            continue
        by: dict[tuple[str, str], dict] = {}
        for r in json.loads(path.read_text(encoding="utf-8")):
            if str(r.get("SB採用", "")).strip().upper() not in {
                "TRUE",
                "__YES__",
                "YES",
                "1",
                "○",
                "採用",
            }:
                continue
            aff = (r.get("所属") or "").strip()
            name = (r.get("名前") or "").strip()
            dist = (r.get("距離") or "").strip()
            mark = (r.get("SB") or r.get("記録") or "").strip()
            if not name or not dist or not mark:
                continue
            if not any(k in aff for k in keywords):
                continue
            school = re.sub(r"(中学校|中学|中)$", "", aff) or aff
            try:
                sec = float(r.get("SB秒") or r.get("記録秒") or 1e12)
            except (TypeError, ValueError):
                continue
            key = (school, dist)
            prev = by.get(key)
            if prev is None or sec < prev["sec"]:
                by[key] = {
                    "sec": sec,
                    "name": name,
                    "mark": mark,
                    "meet": (r.get("大会名") or "").strip(),
                    "date": (r.get("日付") or "").strip(),
                    "url": (r.get("参考") or "").strip(),
                }
        for (school, dist), rec in sorted(by.items()):
            if year == DEFAULT_YEAR:
                eid = f"sb-school-{slug(school)}-{slug(dist)}-best"
            else:
                eid = f"sb-school-{year}-{slug(school)}-{slug(dist)}-best"
            if eid in existing_ids:
                continue
            if year == DEFAULT_YEAR:
                qs = [
                    f"{school}の{dist}最速は誰？",
                    f"{school}{dist}のトップは？",
                    f"今年の{school}の{dist}最速は？",
                    f"{year}年{school}の{dist}最速は誰？",
                ]
            else:
                qs = [
                    f"{year}年{school}の{dist}最速は誰？",
                    f"{year}年の{school}{dist}トップは？",
                    f"{year}年{school}で{dist}が一番速いのは？",
                ]
            ans = f"{year}年度・{school}の{dist}最速（SB採用）は{rec['name']}の {rec['mark']} です。"
            if rec["meet"] or rec["date"]:
                ans += f" 大会: {rec['meet']}（{rec['date']}）。"
            if rec["url"].startswith("http"):
                ans += f" 大会結果: {rec['url']}"
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [str(path.relative_to(ROOT))],
                    ["sb", "school", dist, year],
                )
            )
            if len(out) >= limit:
                return out
    return out


def gen_meet_docs(existing_ids: set[str], limit: int) -> list[dict]:
    """Q&A for notable docs inside meet folders (概要/結果/オーダー等)."""
    root = ROOT / "input" / "idaten-corpus" / "drive-text" / "大会"
    drive = load_drive_meet_folder_map()
    out: list[dict] = []
    interesting = re.compile(r"結果|概要|要項|オーダー|成績|スタートリスト|予実|予想")
    if not root.exists():
        return out
    for year_dir in sorted(root.iterdir(), reverse=True):
        if not year_dir.is_dir():
            continue
        year = year_dir.name.replace("年度", "")
        for meet_dir in sorted(year_dir.iterdir()):
            if not meet_dir.is_dir():
                continue
            folder = meet_dir.name
            title = re.sub(r"^\d{4}-\d{2,4}_", "", folder)
            title = re.sub(r"^\d{2,4}_", "", title)
            url = resolve_drive_meet_url(folder, title, drive)
            for p in sorted(meet_dir.iterdir()):
                if not p.is_file() or p.name.endswith(".meta.json"):
                    continue
                stem = p.stem.replace(".pdf", "").replace(".md", "")
                if not interesting.search(stem) and p.suffix not in {".md", ".txt"}:
                    continue
                if not interesting.search(stem) and p.name != "岱明の結果.md":
                    # still allow short overview-like md
                    if p.suffix != ".md":
                        continue
                eid = f"meet-doc-{slug(year)}-{slug(title)[:28]}-{slug(stem)[:24]}"
                if eid in existing_ids:
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                keep = []
                meta_line = re.compile(
                    r"(?:mimeType|fileSize|viewUrl|parentId|modifiedTime|\*\*id\*\*)",
                    re.I,
                )
                for ln in lines[:40]:
                    if re.match(r"^(大会名|日付|ステータス|状態|場所|タグ|所属|責任者|集合)\b", ln):
                        continue
                    if meta_line.search(ln):
                        continue
                    if re.search(r"\d|:|位|区|結果|優勝|順位|タイム|SB|DNS", ln):
                        keep.append(ln)
                summary = clean_user_facing_text(" ".join(keep[:12]), max_len=220)
                # Prefer a Drive link over a metadata-only dump.
                if not summary or meta_line.search(summary):
                    summary = ""
                if year == str(DEFAULT_YEAR):
                    qs = [
                        f"{title}の{stem}は？",
                        f"{title}「{stem}」の内容は？",
                        f"今年の{title}の{stem}",
                    ]
                else:
                    qs = [
                        f"{year}年{title}の{stem}は？",
                        f"{year}年{title}「{stem}」の内容は？",
                    ]
                ans = f"{title}（{year}）の「{stem}」です。"
                if summary:
                    ans += " " + (summary if summary.endswith("。") else summary + "。")
                if url:
                    ans += f" 大会フォルダ: {url}"
                out.append(
                    entry(
                        eid,
                        qs,
                        ans,
                        [str(p.relative_to(ROOT))]
                        + (["input/external/drive/shared/大会/INDEX.md"] if url else []),
                        ["meet", "doc", int(year) if year.isdigit() else year],
                    )
                )
                if len(out) >= limit:
                    return out
    return out


def gen_calendar_remaining(existing_ids: set[str], limit: int) -> list[dict]:
    """Broader calendar coverage including titled practice and remaining events."""
    out: list[dict] = []
    # Cover remaining calendar events broadly so knowledge stays in prepared Q&A.
    skip = re.compile(r"^(TODO|仮|未定|テスト)$")
    drive_map = load_drive_meet_folder_map()
    for year, path in ((2026, EVENTS_2026), (2025, EVENTS_2025)):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for ev in data.get("events") or []:
            title = (ev.get("title") or "").strip()
            date = ev.get("date") or ev.get("start")
            if not title or not date:
                continue
            if skip.search(title):
                continue
            eid = f"cal-{year}-{str(date).replace('-', '')}-{slug(title)[:28]}"
            if eid in existing_ids:
                continue
            # alternate id for collisions with overly similar slugs
            if any(e["id"] == eid for e in out):
                eid = f"calx-{year}-{str(date).replace('-', '')}-{slug(title)[:28]}"
                if eid in existing_ids:
                    continue
            loc = ev.get("location") or ""
            desc = (ev.get("description") or "").strip()
            status = ev.get("status") or ""
            if int(year) == DEFAULT_YEAR:
                qs = [
                    f"{title}はいつ？",
                    f"{year}年の{title}の日程は？",
                    f"{date}の{title}は？",
                    f"今年の{title}について",
                ]
            else:
                qs = [
                    f"{year}年の{title}はいつ？",
                    f"{year}年の{title}の日程は？",
                    f"{year}-{str(date)[5:]}の{title}は？",
                ]
            ans = friendly_calendar_answer(
                title,
                str(date)[:10],
                location=str(loc or ""),
                status=str(status) if status else None,
                description=desc,
                drive_url=drive_url_for_calendar(title, desc, drive_map),
            )
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [f"input/events.{year}.yaml"],
                    ["calendar", "schedule", year],
                )
            )
            if len(out) >= limit:
                return out
    return out


def gen_pace_matrix(existing_ids: set[str], limit: int) -> list[dict]:
    men_legs = [(1, 3.00), (2, 2.855), (3, 3.00), (4, 3.00), (5, 2.855), (6, 3.00)]
    women_legs = [(1, 3.00), (2, 1.855), (3, 2.00), (4, 2.00), (5, 3.00)]
    paces = [
        ("2分50秒", 170),
        ("2分55秒", 175),
        ("3分00秒", 180),
        ("3分05秒", 185),
        ("3分10秒", 190),
        ("3分15秒", 195),
        ("3分20秒", 200),
        ("3分25秒", 205),
        ("3分30秒", 210),
        ("3分35秒", 215),
        ("3分40秒", 220),
        ("3分45秒", 225),
        ("3分50秒", 230),
        ("3分55秒", 235),
        ("4分00秒", 240),
        ("4分05秒", 245),
        ("4分10秒", 250),
        ("4分20秒", 260),
        ("4分30秒", 270),
        ("4分45秒", 285),
        ("5分00秒", 300),
        ("5分30秒", 330),
    ]
    out: list[dict] = []
    for gender, legs in (("男子", men_legs), ("女子", women_legs)):
        for leg, km in legs:
            for pace_label, sec_per_km in paces:
                eid = f"aragyoku-pace-{gender}-leg{leg}-{slug(pace_label)}"
                if eid in existing_ids:
                    continue
                total_sec = int(round(km * sec_per_km))
                mm, ss = divmod(total_sec, 60)
                qs = [
                    f"荒玉{gender}{leg}区を{pace_label}/kmで走ると何分？",
                    f"{gender}{leg}区{pace_label}ペースのタイムは？",
                    f"荒玉駅伝{gender}{leg}区 {pace_label}毎キロは？",
                ]
                ans = (
                    f"荒玉{gender}{leg}区（{km}km）を{pace_label}/kmで走ると、"
                    f"およそ {mm}:{ss:02d} です。"
                )
                out.append(
                    entry(
                        eid,
                        qs,
                        ans,
                        ["docs/aragyoku-ekiden-distance-definitions.md"],
                        ["aragyoku", "pace", gender],
                    )
                )
                if len(out) >= limit:
                    return out
    return out


def gen_winners_paraphrases(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        years = load_years(path)
        for year in sorted(years.keys(), reverse=True):
            teams = years[year].get("teams") or []
            if len(teams) < 2:
                continue
            w, r = teams[0], teams[1]
            for kind, team, other, label in (
                ("winner", w, r, "優勝"),
                ("runnerup", r, w, "準優勝"),
            ):
                name = team.get("team") or ""
                total = team.get("total") or "?"
                other_name = other.get("team") or ""
                eid = f"aragyoku-{year}-{gender}-{kind}-ask"
                if eid in existing_ids:
                    continue
                # base winner entries may already exist as aragyoku-YYYY-gender-winner
                base_id = f"aragyoku-{year}-{gender}-{kind}"
                qs = [
                    f"{year}年荒玉{gender}の{label}校は？",
                    f"{year}年の荒玉駅伝{gender}{label}は誰？",
                    f"{year}荒玉{gender}{label}タイムは？",
                ]
                ans = (
                    f"{year}年荒玉駅伝{gender}の{label}は{name}（{total}）です。"
                    f" 対して{'優勝' if kind=='runnerup' else '準優勝'}は"
                    f"{other_name}（{other.get('total') or '?'}）です。"
                )
                out.append(
                    entry(
                        eid,
                        qs,
                        ans,
                        [src],
                        ["aragyoku", "winner", gender, int(year)],
                    )
                )
                # also top3 if present
                if len(teams) >= 3:
                    third = teams[2]
                    eid3 = f"aragyoku-{year}-{gender}-top3"
                    if eid3 not in existing_ids and not any(e["id"] == eid3 for e in out):
                        tnames = [
                            f"{t.get('rank')}位{t.get('team')}（{t.get('total') or '?'}）"
                            for t in teams[:3]
                        ]
                        out.append(
                            entry(
                                eid3,
                                [
                                    f"{year}年荒玉{gender}の上位3校は？",
                                    f"{year}年荒玉駅伝{gender}トップ3は？",
                                    f"{year}荒玉{gender}の3位まで教えて",
                                ],
                                f"{year}年荒玉駅伝{gender}の上位は "
                                + "、".join(tnames)
                                + " です。",
                                [src],
                                ["aragyoku", "ranking", gender, int(year)],
                            )
                        )
                if len(out) >= limit:
                    return out
                _ = base_id  # kept for readability / future conflict checks
    return out


def gen_topic_extras(existing_ids: set[str]) -> list[dict]:
    seeds = [
        (
            "topic-schema",
            ["データモデルは？", "スキーマの正本は？", "JSON Schemaはどこ？"],
            "データモデルとJSON Schemaはリポジトリのスキーマ／データモデル文書が正本です。"
            "イベント・練習・選手プロフィールの形を定義しています。",
            ["docs/data-model.md"],
            ["meta", "schema"],
        ),
        (
            "topic-repo-ops",
            ["リポジトリ運用は？", "生成パイプラインは？", "コーパスの更新手順は？"],
            "カレンダー生成・KG再生成・想定Q&A同期などの運用は README / ADR を正本とします。"
            "ソースを変えたら generate / sync / KG を更新してコミットしてください。",
            ["README.md", "docs/adr/059-prepared-qa-answers.md"],
            ["meta", "ops"],
        ),
        (
            "topic-norwegian",
            ["Norwegian Methodとは？", "ノルウェージャンメソッドは？", "GZ閾値の考え方は？"],
            "Norwegian Method / GZ・閾値ペースの一般論はナレッジで案内できます。"
            "個人の処方や強度設定はコーチ確認してください。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["meta", "pace"],
        ),
        (
            "help-ask-results",
            ["結果の聞き方は？", "大会結果を聞くには？", "成績の質問例は？"],
            "「大会名＋結果/順位/区間」が確実です。例: 「ジュニア駅伝の結果は？」"
            "「2025年荒玉男子の岱明は何位？」「玉名郡ナイターの結果」。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["help", "result"],
        ),
        (
            "help-ask-sb",
            ["自己ベストの質問例は？", "SBの聞き方をもっと教えて", "記録質問のコツは？"],
            "「選手名＋距離＋自己ベスト/SB」が確実です。学校最速は「岱明の1500m最速は誰？」。"
            "回答には大会結果リンクが付きます。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["help", "sb"],
        ),
        (
            "help-ask-order",
            ["オーダーの聞き方は？", "区間メンバーを聞くには？", "誰が何区か聞く例は？"],
            "「年＋荒玉＋男女＋学校＋何区」が確実です。例: 「2025年荒玉男子の岱明5区は誰？」。"
            "なごみのオーダーはなごみ大会フォルダが正本です。",
            ["out/analysis/aragyoku-overview.md"],
            ["help", "aragyoku"],
        ),
        (
            "help-ask-calendar",
            ["予定の聞き方は？", "カレンダー質問の例は？", "日程を聞くコツは？"],
            "「大会名＋いつ/日程」か「今月の大会」が確実です。例: 「ジュニア駅伝はいつ？」"
            "「今週の練習は？」。年を省略すると今年度として答えます。",
            ["input/events.2026.yaml", "docs/adr/059-prepared-qa-answers.md"],
            ["help", "calendar"],
        ),
        (
            "help-ask-meet-folder",
            ["大会フォルダの見方は？", "Driveの結果はどこ？", "要項の場所は？"],
            "大会名で聞くと Drive の大会フォルダURLが付きます。"
            "結果・要項・オーダーは各大会フォルダ内が正本です。",
            ["input/external/drive/shared/大会/INDEX.md"],
            ["help", "meet"],
        ),
        (
            "topic-kg",
            ["ナレッジグラフは？", "KGの正本は？", "knowledge-graphはどこ？"],
            "検索ルート地図は out/knowledge-graph.json です。"
            "まず KG の refs を開き、必要ならカレンダー生成後に再生成します。",
            ["out/knowledge-graph.json", "docs/adr/059-prepared-qa-answers.md"],
            ["meta", "kg"],
        ),
        (
            "topic-external-index",
            ["外部データの入口は？", "Driveスナップショットはどこ？", "external INDEXは？"],
            "Notion・Drive 由来は input/external/ です。探索は input/external/INDEX.md から。",
            ["input/external/INDEX.md", "docs/adr/010-external-idaten-import.md"],
            ["meta", "external"],
        ),
        (
            "topic-media-ocr",
            ["駅伝の画像OCRは？", "media-manifestは？", "コース写真のナレッジは？"],
            "画像・OCRは media-manifest と KG の MediaAsset（topic:ekiden）を辿ります。",
            ["docs/adr/011-idaten-media-ocr-kg.md"],
            ["meta", "media"],
        ),
        (
            "help-yearless",
            ["年を省略したらどうなる？", "年なし質問の解釈は？", "今年扱いは？"],
            "年を省略した質問は今年度（現行年度）として解釈します。"
            "過去年は「2024年…」のように年を付けてください。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["help", "year"],
        ),
        (
            "help-ask-pace",
            ["ペース換算の聞き方は？", "区間タイムの計算例は？", "毎キロから区間は？"],
            "「荒玉男子○区を3分20秒/kmで」のように聞くと区間タイム目安が返ります。"
            "距離定義は荒玉の距離定義ドキュメントが正本です。",
            ["docs/aragyoku-ekiden-distance-definitions.md"],
            ["help", "pace"],
        ),
    ]
    out = []
    for eid, qs, ans, srcs, tags in seeds:
        if eid in existing_ids:
            continue
        out.append(entry(eid, qs, ans, srcs, tags))
    return out


def build_new_entries(existing_ids: set[str], target: int) -> list[dict]:
    used = set(existing_ids)
    buckets = {
        "legs_all": gen_all_aragyoku_legs(existing_ids, 2000),
        "ranks_all": gen_all_aragyoku_ranks(existing_ids, 400),
        "school_sb_years": gen_school_sb_all_years(existing_ids, 900),
        "meet_docs": gen_meet_docs(existing_ids, 250),
        "calendar": gen_calendar_remaining(existing_ids, 500),
        "pace": gen_pace_matrix(existing_ids, 300),
        "winners": gen_winners_paraphrases(existing_ids, 200),
        "quiz": gen_quiz(existing_ids, 250),
        "practice": gen_practice_notes(existing_ids, 80),
        "topics": gen_topic_extras(existing_ids),
    }
    for k, v in buckets.items():
        print(f"  bucket {k}: {len(v)}")

    quotas = [
        ("topics", 30),
        ("legs_all", 1400),
        ("ranks_all", 80),
        ("school_sb_years", 700),
        ("meet_docs", 200),
        ("calendar", 350),
        ("pace", 220),
        ("winners", 120),
        ("quiz", 120),
        ("practice", 40),
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
            "legs_all",
            "school_sb_years",
            "meet_docs",
            "calendar",
            "pace",
            "winners",
            "quiz",
            "ranks_all",
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

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = data.get("entries") or []
    existing_ids = {e["id"] for e in entries}
    print(f"existing entries: {len(entries)}")

    new_entries = build_new_entries(existing_ids, args.target)
    if len(new_entries) < args.target:
        raise SystemExit(f"expected {args.target} new entries, got {len(new_entries)}")

    existing_q = {q for e in entries for q in (e.get("questions") or [])}
    cleaned_new: list[dict] = []
    trimmed = 0
    for e in new_entries:
        qs = [q for q in e["questions"] if q not in existing_q]
        if not qs:
            trimmed += 1
            continue
        e = dict(e)
        e["questions"] = qs
        cleaned_new.append(e)
        for q in qs:
            existing_q.add(q)

    if len(cleaned_new) < args.target:
        more = build_new_entries(
            existing_ids | {e["id"] for e in cleaned_new},
            args.target - len(cleaned_new) + 200,
        )
        for e in more:
            if e["id"] in existing_ids or e["id"] in {x["id"] for x in cleaned_new}:
                continue
            qs = [q for q in e["questions"] if q not in existing_q]
            if not qs:
                continue
            e = dict(e)
            e["questions"] = qs
            cleaned_new.append(e)
            for q in qs:
                existing_q.add(q)
            if len(cleaned_new) >= args.target:
                break

    cleaned_new = cleaned_new[: args.target]
    if len(cleaned_new) < args.target:
        raise SystemExit(
            f"after cleanup expected {args.target}, got {len(cleaned_new)} (trimmed {trimmed})"
        )

    merged = list(entries) + cleaned_new
    seen: set[str] = set()
    uniq = []
    for e in merged:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        uniq.append(e)

    data["entries"] = uniq
    data["total"] = len(uniq)
    data["note"] = (
        "想定質問への定型回答（ADR 059）。年なし＝今年度。"
        "ナレッジカバーを拡充（知識カバー+1000/+3000: 荒玉全区間・年度別学校SB・大会資料・カレンダー等）。\n"
        "ヒット時は本文をほぼそのまま返す。未ヒット時のみ RAG/LLM。\n"
    )
    print(f"merged total {len(uniq)} (+{len(cleaned_new)})")
    for sid in (
        "aragyoku-2015-男子-荒尾三-leg1",
        "sb-school-2024-岱明-1500m-best",
        "help-ask-sb",
    ):
        e = next((x for x in cleaned_new if x["id"] == sid), None)
        if e:
            print("SAMPLE", e["id"], e["answer"][:180].replace("\n", " | "))

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
