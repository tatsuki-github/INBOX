#!/usr/bin/env python3
"""Add ~1000 knowledge-covering prepared FAQ entries (ADR 059).

Does NOT wipe existing entries. Prefers user-facing answers (dates, results,
Drive/meet links) over repo-path dumps.

Usage:
  python3 scripts/generate_prepared_qa_knowledge_1000.py
  python3 scripts/generate_prepared_qa_knowledge_1000.py --dry-run
  python3 scripts/generate_prepared_qa_knowledge_1000.py --target 1000
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
    FOCUS_TEAMS,
    clean_user_facing_text,
    entry,
    gen_aragyoku_legs,
    gen_aragyoku_team_ranks,
    gen_practice_notes,
    gen_quiz,
    load_drive_meet_folder_map,
    resolve_drive_meet_url,
    slug,
)

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
BY_YEAR = ROOT / "input" / "external" / "sb" / "middle-school" / "by-year"
REPORT = ROOT / "input" / "arato_tamana_report.yaml"
DEFAULT_YEAR = 2026


def take(bucket: list[dict], n: int, used: set[str]) -> list[dict]:
    out: list[dict] = []
    for e in bucket:
        if e["id"] in used:
            continue
        used.add(e["id"])
        out.append(e)
        if len(out) >= n:
            break
    return out


def load_keywords() -> list[str]:
    keys = ["菊水", "三加和", "腹栄", "和水", "南関", "岱明", "玉名", "荒尾", "天水", "有明", "長洲", "玉陵", "ATRC", "金栗", "NJAC"]
    if REPORT.exists():
        data = yaml.safe_load(REPORT.read_text(encoding="utf-8")) or {}
        for k in data.get("affiliation_keywords") or []:
            if k not in keys:
                keys.append(k)
    return keys


def gen_school_sb_best(existing_ids: set[str], limit: int) -> list[dict]:
    """School × distance fastest SB with meet URL."""
    path = BY_YEAR / f"{DEFAULT_YEAR}-sb-adopted.json"
    if not path.exists():
        return []
    keywords = load_keywords()
    rows = json.loads(path.read_text(encoding="utf-8"))
    by: dict[tuple[str, str], dict] = {}
    for r in rows:
        if str(r.get("SB採用", "")).strip().upper() not in {"TRUE", "__YES__", "YES", "1", "○", "採用"}:
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
                "aff": aff,
            }
    out: list[dict] = []
    for (school, dist), rec in sorted(by.items()):
        eid = f"sb-school-{slug(school)}-{slug(dist)}-best"
        if eid in existing_ids:
            continue
        qs = [
            f"{school}の{dist}最速は誰？",
            f"{school}{dist}のトップは？",
            f"{school}で{dist}が一番速い選手は？",
            f"今年の{school}の{dist}最速は？",
        ]
        ans = f"{school}の{dist}最速（{DEFAULT_YEAR}年度・SB採用）は{rec['name']}の {rec['mark']} です。"
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
                ["sb", "school", dist, DEFAULT_YEAR],
            )
        )
        if len(out) >= limit:
            break
    return out


def gen_meet_daiming_results(existing_ids: set[str], limit: int) -> list[dict]:
    root = ROOT / "input" / "idaten-corpus" / "drive-text" / "大会"
    drive = load_drive_meet_folder_map()
    out: list[dict] = []
    if not root.exists():
        return out
    for year_dir in sorted(root.iterdir(), reverse=True):
        if not year_dir.is_dir():
            continue
        year = year_dir.name.replace("年度", "")
        for meet_dir in sorted(year_dir.iterdir()):
            if not meet_dir.is_dir():
                continue
            result = meet_dir / "岱明の結果.md"
            if not result.exists():
                continue
            folder = meet_dir.name
            title = re.sub(r"^\d{4}-\d{2,4}_", "", folder)
            title = re.sub(r"^\d{2,4}_", "", title)
            eid = f"meet-result-{slug(year)}-{slug(title)[:40]}"
            if eid in existing_ids:
                continue
            text = result.read_text(encoding="utf-8", errors="replace")
            # Keep result-looking lines; drop ops metadata
            keep_lines = []
            for ln in text.splitlines():
                s = ln.strip()
                if not s:
                    continue
                if re.match(r"^(大会名|日付|ステータス|状態|場所|タグ|所属|責任者|集合)\b", s):
                    continue
                if re.search(r"\d[:：]\d|\d分|\d位|SB|DNS|DNF|800m|1500m|3000m|男子|女子", s):
                    keep_lines.append(s)
            summary = clean_user_facing_text(" ".join(keep_lines), max_len=260)
            summary = re.sub(r"\b(done|scheduled|cancelled)\b", " ", summary, flags=re.I)
            summary = re.sub(r"\s+", " ", summary).strip(" 。")
            url = resolve_drive_meet_url(folder, title, drive)
            if str(year) == str(DEFAULT_YEAR):
                qs = [
                    f"{title}の結果は？",
                    f"{title}の岱明の結果は？",
                    f"今年の{title}の結果",
                    f"{year}年{title}の結果は？",
                ]
            else:
                qs = [
                    f"{year}年{title}の結果は？",
                    f"{year}年{title}の岱明の結果は？",
                    f"{year}の{title}結果を教えて",
                ]
            ans = f"{title}（{year}）の岱明結果です。"
            if summary:
                ans += " " + (summary if summary.endswith("。") else summary + "。")
            if url:
                ans += f" 資料: {url}"
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [str(result.relative_to(ROOT))]
                    + (["input/external/drive/shared/大会/INDEX.md"] if url else []),
                    ["meet", "result", "daiming", int(year) if year.isdigit() else year],
                )
            )
            if len(out) >= limit:
                return out
    return out


def gen_arato_tamana_teams(existing_ids: set[str], limit: int) -> list[dict]:
    root = ROOT / "out" / "analysis" / "arato-tamana-teams"
    out: list[dict] = []
    if not root.exists():
        return out
    for p in sorted(root.glob("*.md")):
        if p.name.upper() == "INDEX.MD":
            continue
        team = p.stem
        eid = f"records-team-{slug(team)}"
        if eid in existing_ids:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        # Count seasons / sample athlete names for a short blurb
        seasons = re.findall(r"20\d{2}年度", text)
        uniq_seasons = []
        for s in seasons:
            if s not in uniq_seasons:
                uniq_seasons.append(s)
        count_m = re.search(r"件数:\s*(\d+)", text)
        qs = [
            f"{team}の選手の全記録は？",
            f"{team}の記録一覧は？",
            f"{team}所属選手のSBは？",
            f"{team}のトラック記録は？",
        ]
        uniq_qs = list(dict.fromkeys(qs))
        ans = f"{team}の所属選手トラック記録一覧です。"
        if uniq_seasons:
            ans += " 収録年度: " + "、".join(uniq_seasons[:4]) + "。"
        if count_m:
            ans += f" 例: 直近セクション件数 {count_m.group(1)}。"
        ans += " 種目は800m・1500m・3000mなど。個人の自己ベストは選手名＋距離で聞いてください。"
        out.append(
            entry(
                eid,
                uniq_qs,
                ans,
                [str(p.relative_to(ROOT))],
                ["sb", "team", "records"],
            )
        )
        if len(out) >= limit:
            break
    return out


def gen_aragyoku_team_histories(existing_ids: set[str], limit: int) -> list[dict]:
    root = ROOT / "out" / "analysis" / "aragyoku-teams"
    out: list[dict] = []
    if not root.exists():
        return out
    for p in sorted(root.glob("*.md")):
        team = p.stem
        eid = f"aragyoku-history-{slug(team)}"
        if eid in existing_ids:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        # pull a few year rank lines if present
        ranks = []
        for ln in lines:
            m = re.search(r"(20\d{2}).{0,12}?(?:男子|女子).{0,8}?(\d+)\s*位", ln)
            if m:
                ranks.append(f"{m.group(1)}年{m.group(2)}位")
            if len(ranks) >= 6:
                break
        snippet = clean_user_facing_text(" ".join(lines[1:10]), max_len=180)
        qs = [
            f"{team}の荒玉駅伝の過去の順位は？",
            f"{team}の荒玉歴代は？",
            f"{team}中の荒玉駅伝成績は？" if not team.endswith(("中", "附属", "PROJECT")) else f"{team}の荒玉駅伝成績は？",
            f"荒玉駅伝で{team}はどうだった？",
        ]
        ans = f"{team}の荒玉駅伝歴代結果です。"
        if ranks:
            ans += " 例: " + "、".join(ranks) + "。"
        elif snippet:
            ans += " " + (snippet if snippet.endswith("。") else snippet + "。")
        out.append(
            entry(
                eid,
                qs,
                ans,
                [str(p.relative_to(ROOT))],
                ["aragyoku", "team", "history"],
            )
        )
        if len(out) >= limit:
            break
    return out


def gen_athlete_profiles(existing_ids: set[str], limit: int) -> list[dict]:
    path = ROOT / "input" / "athlete-team-profiles.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    athletes = data.get("athletes") or []
    out: list[dict] = []
    for a in athletes:
        name = (a.get("name") or "").strip()
        if not name:
            continue
        eid = f"profile-{slug(name)}"
        if eid in existing_ids:
            continue
        grade = a.get("grade")
        season = a.get("season") or DEFAULT_YEAR
        team = "岱明中"
        qs = [
            f"{name}のプロフィールは？",
            f"{name}は何年生？",
            f"{name}の所属と学年は？",
            f"{name}について教えて",
        ]
        ans = f"{name}は{team}の"
        if grade:
            ans += f"{grade}年"
        ans += f"（{season}年度）です。"
        ans += f" 自己ベストの詳細は「{name}の自己ベストは？」で確認できます。"
        out.append(
            entry(
                eid,
                qs,
                ans,
                ["input/athlete-team-profiles.json"],
                ["profile", "athlete", "daiming", season],
            )
        )
        if len(out) >= limit:
            break
    return out


def gen_knowledge_seeds(existing_ids: set[str]) -> list[dict]:
    """Handcrafted knowledge Q&A covering KG topics / query hints."""
    drive = load_drive_meet_folder_map()
    aragyoku_url = drive.get("1014-1015_荒玉中体連駅伝", "")
    junior_url = drive.get("0926_第４回県ジュニア陸上（第３回県ジュニア駅伝）", "")
    nagomi_url = drive.get("0920_中学駅伝金栗四三生誕の地なごみ大会", "")
    seeds: list[tuple[str, list[str], str, list[str], list]] = [
        (
            "topic-athlete-records",
            ["選手記録はどこで分かる？", "SBや所属記録の見方は？", "選手の記録ナレッジは？"],
            "選手記録は自己ベスト定型（選手名＋距離）と所属別記録一覧で答えます。"
            "例: 「松野凛空の1500mSBは？」「南関中の記録一覧は？」。",
            ["docs/adr/059-prepared-qa-answers.md", "input/external/sb/middle-school/by-year/2026-sb-adopted.json"],
            ["meta", "sb"],
        ),
        (
            "topic-calendar",
            ["予定のナレッジは？", "カレンダーの正本は？", "大会日程はどこを見る？"],
            "大会・練習の日程はカレンダー定型で答えます。大会名や日付を入れて聞いてください。"
            "例: 「荒玉中体連駅伝はいつ？」「2026-10-14の予定は？」。",
            ["input/events.2026.yaml"],
            ["meta", "calendar"],
        ),
        (
            "topic-ekiden",
            ["駅伝・大会ナレッジは？", "荒玉やなごみの結果はどこ？", "大会結果の聞き方は？"],
            "荒玉・なごみ・ジュニアなどの駅伝結果は大会名＋結果/順位/区間で聞いてください。"
            "例: 「2025年荒玉男子の岱明は何位？」「なごみ駅伝の結果は？」「ジュニア駅伝の結果は？」。",
            ["out/analysis/aragyoku-overview.md"],
            ["meta", "ekiden"],
        ),
        (
            "topic-practice",
            ["練習ナレッジは？", "練習メニューの正本は？", "岱明の練習記録は？"],
            "岱明の練習は日付付きで聞いてください。例: 「2026-09-22の練習は？」「今日のメニューは？」。"
            "欠席者は「欠席者は誰？」＋日付が確実です。",
            ["input/events.2026.yaml"],
            ["meta", "practice"],
        ),
        (
            "topic-pace-gz",
            ["ペースやGZのナレッジは？", "閾値ペースの見方は？", "Norwegian Methodは？"],
            "ペースは「荒玉男子1区を3分30秒/kmで走ると何分？」のように区間＋ペースで聞けます。"
            "GZ・閾値・Norwegian Methodの一般論も定型で案内します。個人処方はコーチ確認です。",
            ["docs/aragyoku-ekiden-distance-definitions.md"],
            ["meta", "pace"],
        ),
        (
            "topic-injury",
            ["ケガや障害のナレッジは？", "RRIについて教えて", "怪我の一般論は？"],
            "ケガ・障害（RRI）の一般論はナレッジで案内できます。個人の診断や治療方針は答えられません。"
            "症状がある場合はコーチ・医療機関に確認してください。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["meta", "injury"],
        ),
        (
            "topic-ai-practice",
            ["AI練習生成のナレッジは？", "AIで練習を作る流れは？", "練習生成の使い方は？"],
            "AI練習生成はカレンダー・テンプレ・制約を入力に練習シートを作る流れです。"
            "「AIで練習を作るには？」でも案内します。",
            ["docs/ai-practice-generation.md"],
            ["meta", "ai"],
        ),
        (
            "topic-profile",
            ["選手プロフィールのナレッジは？", "学年やチーム構成は？", "部員のプロフィールは？"],
            "岱明の学年・部員一覧は「いだてん岱明の生徒一覧」や「○○のプロフィールは？」で確認できます。"
            "個人連絡先は扱いません。",
            ["input/athlete-team-profiles.json"],
            ["meta", "profile"],
        ),
        (
            "nagomi-2026-result-friendly",
            ["なごみ駅伝の結果は？", "今年のなごみの結果", "2026年なごみ駅伝の結果は？", "なごみ大会の岱明結果は？"],
            "2026年なごみ駅伝（2026-09-20）の結果です。荒玉地区の全選手結果と岱明の成績が大会フォルダにあります。"
            + (f" 資料: {nagomi_url}" if nagomi_url else ""),
            [
                "input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会",
                "input/external/drive/shared/大会/INDEX.md",
            ],
            ["nagomi", "result", 2026],
        ),
        (
            "nagomi-order-friendly",
            ["なごみ駅伝の区間オーダーは？", "なごみのオーダーは？", "今年のなごみ区間オーダー"],
            "なごみ駅伝の区間オーダーは大会フォルダの区間オーダー資料が正本です（金栗駅伝とは別）。"
            + (f" 資料: {nagomi_url}" if nagomi_url else ""),
            [
                "input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会",
            ],
            ["nagomi", "order", 2026],
        ),
        (
            "junior-2026-result-variants",
            ["県ジュニアの結果は？", "第3回県ジュニア駅伝の結果", "ジュニア陸上の駅伝結果は？"],
            "2026年・第3回県ジュニア駅伝（2026-09-26）の岱明結果は、女子CS 12位36:52、男子CS 14位44:23です。"
            + (f" 大会フォルダ: {junior_url}" if junior_url else ""),
            [
                "input/idaten-corpus/drive-text/大会/2026年度/0926_第４回県ジュニア陸上（第３回県ジュニア駅伝）/岱明の結果.md",
            ],
            ["junior", "result", 2026],
        ),
        (
            "aragyoku-2026-preview-friendly",
            ["荒玉の予想は？", "荒玉駅伝の区間予想は？", "今年の荒玉オーダー予想は？", "荒玉の数式予想は？"],
            "2026年荒玉中体連駅伝（2026-10-14、予備日10-15）の岱明オーダー・数式予想は大会フォルダにあります。"
            + (f" 資料: {aragyoku_url}" if aragyoku_url else ""),
            ["input/events.2026.yaml", "input/external/drive/shared/大会/INDEX.md"],
            ["aragyoku", "preview", 2026],
        ),
        (
            "youkou-generic",
            ["開催要項は？", "大会要項を見せて", "要項はどこ？"],
            "開催要項は大会フォルダ内の要項・概要資料を正本とします。大会名を指定してください。"
            "例: 「荒玉中体連駅伝の資料はどこ？」「ジュニア駅伝の結果PDF」。",
            ["input/external/drive/shared/大会/INDEX.md"],
            ["meet", "youkou"],
        ),
        (
            "today-schedule-hint",
            ["今日の予定は？", "本日の予定を教えて", "今日のカレンダーは？"],
            "今日の予定は日付付きカレンダーから引きます。具体的な日付（例: 2026-10-14）や大会名があると確実です。",
            ["input/events.2026.yaml"],
            ["calendar", "help"],
        ),
        (
            "date-schedule-hint",
            ["〇月〇日の予定は？", "日付の予定の聞き方は？", "何日の予定を聞くには？"],
            "「YYYY-MM-DDの予定は？」や「10月14日の予定は？」のように日付を入れて聞いてください。",
            ["input/events.2026.yaml"],
            ["calendar", "help"],
        ),
        (
            "competitor-hint",
            ["他校の情報は？", "ライバル校の記録は？", "競合校を知りたい"],
            "他校は荒玉の順位・区間、所属別記録一覧、学校別SB最速で確認できます。"
            "例: 「2025年荒玉男子の南関は何位？」「菊水の1500m最速は誰？」。",
            ["out/analysis/aragyoku-overview.md"],
            ["meta", "competitor"],
        ),
        (
            "leg-award-hint",
            ["荒玉駅伝の区間賞は誰？", "区間賞の聞き方は？", "区間新は誰？"],
            "区間賞は年と男女を指定すると答えやすいです。例: 「2025年荒玉駅伝男子の区間賞は？」"
            "「天水中の荒玉駅伝で区間新は誰？」。",
            ["out/analysis/aragyoku-overview.md"],
            ["aragyoku", "help"],
        ),
        (
            "average-pace-hint",
            ["荒玉駅伝の平均ペースは？", "男子1位の平均ペースは？", "全チームの平均ペースは？"],
            "平均ペースは年・男女を指定してください。例: 「2025年荒玉男子1位の平均ペースは？」"
            "「全チームの平均ペースを全て提示して」。",
            ["out/analysis/aragyoku-overview.md"],
            ["aragyoku", "pace", "help"],
        ),
        (
            "course-media-hint",
            ["荒玉駅伝のコース動画は？", "荒玉駅伝のコースの画像は？", "コース図を見せて"],
            "荒玉駅伝のコース動画・コース画像は専用の定型回答があります。"
            "「荒玉駅伝のコース動画は？」「荒玉駅伝のコースの画像は？」とそのまま聞いてください。",
            ["docs/adr/059-prepared-qa-answers.md"],
            ["aragyoku", "course", "help"],
        ),
        (
            "focus-teams-2024-2025",
            [
                "2024年と2025年の荒玉駅伝で岱明・玉名付属・天水・有明はどうだった？",
                "深掘り4校の荒玉比較は？",
                "岱明と玉高附属の2024-2025は？",
            ],
            "2024–2025の深掘り対象は岱明・玉高附属・天水・有明です。"
            "岱明男子は15位→6位、女子は6位→7位。玉高附属男子は2位→3位、女子は5位→10位。"
            "詳細は「有明中の荒玉駅伝2024-2025の分析は？」など校名でも聞けます。",
            ["out/analysis/aragyoku_2024_2025_focus_teams.md"],
            ["aragyoku", "analysis"],
        ),
    ]
    out: list[dict] = []
    for eid, qs, ans, srcs, tags in seeds:
        if eid in existing_ids:
            continue
        out.append(entry(eid, qs, ans, srcs, tags))
    return out


def gen_expanded_legs(existing_ids: set[str], limit: int) -> list[dict]:
    """More leg Q&A including non-focus teams for recent years."""
    from generate_prepared_qa_bulk import MEN_FULL, WOMEN_FULL, load_years

    out: list[dict] = []
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/idaten-corpus/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/idaten-corpus/aragyoku/men_full_2012_2025.json"),
    ):
        years = load_years(path)
        for year in sorted(years.keys(), reverse=True):
            if int(year) < 2020:
                continue
            yd = years[year]
            for team in yd.get("teams") or []:
                name = team.get("team") or ""
                if not name or name in FOCUS_TEAMS:
                    continue  # focus already covered by gen_aragyoku_legs
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


def build_new_entries(existing_ids: set[str], target: int) -> list[dict]:
    used = set(existing_ids)
    buckets = {
        "seeds": gen_knowledge_seeds(existing_ids),
        "meet_results": gen_meet_daiming_results(existing_ids, 80),
        "arato_teams": gen_arato_tamana_teams(existing_ids, 40),
        "aragyoku_hist": gen_aragyoku_team_histories(existing_ids, 30),
        "profiles": gen_athlete_profiles(existing_ids, 30),
        "school_sb": gen_school_sb_best(existing_ids, 220),
        "team_ranks": gen_aragyoku_team_ranks(existing_ids, 400),
        "legs_focus": gen_aragyoku_legs(existing_ids, 500),
        "legs_other": gen_expanded_legs(existing_ids, 400),
        "practice": gen_practice_notes(existing_ids, 120),
        "quiz": gen_quiz(existing_ids, 200),
    }
    for k, v in buckets.items():
        print(f"  bucket {k}: {len(v)}")

    # Diversified quotas (~1000). Knowledge-first, then concrete results.
    quotas = [
        ("seeds", 30),
        ("meet_results", 40),
        ("arato_teams", 24),
        ("aragyoku_hist", 18),
        ("profiles", 15),
        ("school_sb", 180),
        ("team_ranks", 120),
        ("legs_focus", 280),
        ("legs_other", 180),
        ("practice", 60),
        ("quiz", 80),
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
        for name in ("legs_other", "legs_focus", "school_sb", "team_ranks", "quiz", "practice"):
            if len(selected) >= target:
                break
            selected.extend(take(buckets[name], target - len(selected), used))

    selected = selected[:target]
    print(f"  FINAL new: {len(selected)}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--target", type=int, default=1000)
    args = parser.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = data.get("entries") or []
    existing_ids = {e["id"] for e in entries}
    print(f"existing entries: {len(entries)}")

    new_entries = build_new_entries(existing_ids, args.target)
    if len(new_entries) < args.target:
        raise SystemExit(f"expected {args.target} new entries, got {len(new_entries)}")

    # Drop questions from new entries that exact-match existing questions
    existing_q = {q for e in entries for q in (e.get("questions") or [])}
    cleaned_new: list[dict] = []
    trimmed = 0
    for e in new_entries:
        qs = [q for q in e["questions"] if q not in existing_q]
        if len(qs) < 1:
            trimmed += 1
            continue
        e = dict(e)
        e["questions"] = qs
        cleaned_new.append(e)
        for q in qs:
            existing_q.add(q)

    # top up if trimming removed some
    if len(cleaned_new) < args.target:
        more = build_new_entries(
            existing_ids | {e["id"] for e in cleaned_new},
            args.target - len(cleaned_new) + 80,
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
    # unique ids
    seen = set()
    uniq = []
    for e in merged:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        uniq.append(e)

    data["entries"] = uniq
    data["total"] = len(uniq)
    note = str(data.get("note") or "")
    if "知識カバー+1000" not in note:
        data["note"] = (
            "想定質問への定型回答（ADR 059）。年なし＝今年度。"
            "荒玉SB・大会結果・所属記録・プロフィール等のナレッジカバーを拡充（知識カバー+1000）。\n"
            "ヒット時は本文をほぼそのまま返す。未ヒット時のみ RAG/LLM。\n"
        )
    print(f"merged total {len(uniq)} (+{len(cleaned_new)})")

    # samples
    for sid in (
        "meet-result-2026-玉名郡ナイター中-長距離記録会",
        "records-team-南関中",
        "profile-松野凛空",
        "topic-ekiden",
    ):
        e = next((x for x in cleaned_new if x["id"] == sid), None)
        if e:
            print("SAMPLE", e["id"], e["answer"][:160].replace("\n", " | "))

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
