#!/usr/bin/env python3
"""Generate exhausted unique repo-grounded question bank from corpus facts."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def time_tokens(t: str) -> list[str]:
    t = (t or "").strip()
    if not t:
        return []
    toks = [t]
    m = re.match(r"(\d+):(\d{2}(?:\.\d+)?)", t)
    if m:
        toks.append(f"{int(m.group(1))}:{m.group(2)}")
    return toks


def main() -> None:
    sb = list(
        csv.DictReader((ROOT / "input/idaten-corpus/sb/中学生SB.csv").open(encoding="utf-8-sig"))
    )
    meets = json.loads((ROOT / "backend/data/meet-result-urls.json").read_text(encoding="utf-8"))[
        "meets"
    ]

    pairs: list[tuple[str, dict]] = []
    seen: set[str] = set()

    def add(q: str, expect: dict) -> bool:
        q = q.strip()
        if not q or q in seen:
            return False
        seen.add(q)
        pairs.append((q, expect))
        return True

    dist_labels = [
        ("800mSB", "800m"),
        ("1500mSB", "1500m"),
        ("3000mSB", "3000m"),
        ("5000mSB", "5000m"),
        ("3kmSB", "3km"),
        ("5kmSB", "5km"),
        ("10kmSB", "10km"),
    ]
    sb_count = 0
    for r in sb:
        name = (r.get("名前") or "").strip()
        aff = (r.get("所属") or "").strip()
        if not name:
            continue
        for key, dist in dist_labels:
            val = (r.get(key) or "").strip()
            if not val:
                continue
            expect = {
                "kinds": ["answered"],
                "any_of": time_tokens(val) + [name],
                "forbid": ["コーチに直接聞いてください"],
                "sources_any": ["sb/"],
            }
            if add(f"{name}の{dist}自己ベストは？", expect):
                sb_count += 1
            if aff and add(f"{name}（{aff}）の{dist} SBは？", expect):
                sb_count += 1

    cal = (ROOT / "input/idaten-corpus/calendar/events.daiming.yaml").read_text(encoding="utf-8")
    events: list[tuple[str, str]] = []
    lines = cal.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^- title:\s*(.+)$", line.strip())
        if not m:
            continue
        title = m.group(1).strip().strip("'\"")
        date = None
        for j in range(i + 1, min(i + 8, len(lines))):
            dm = re.match(r"^date:\s*['\"]?(\d{4}-\d{2}-\d{2})", lines[j].strip())
            if dm:
                date = dm.group(1)
                break
        if date and len(title) >= 2:
            events.append((date, title))

    cal_count = 0
    for date, title in events:
        y, m, d = date.split("-")
        for q, any_of in [
            (f"{title}はいつ？", [date, f"{int(m)}月{int(d)}", title[:6]]),
            (f"{date}は何の予定？", [title[:8], title[:4], date]),
            (f"{y}年{int(m)}月{int(d)}日にある行事は？", [date, title[:6], title[:4]]),
        ]:
            if add(
                q,
                {
                    "kinds": ["answered"],
                    "any_of": any_of,
                    "forbid": ["コーチに直接聞いてください"],
                },
            ):
                cal_count += 1

    meet_count = 0
    for meet in meets:
        title = re.sub(r"\s+", " ", meet["title"]).strip()
        host = re.sub(r"^https?://", "", meet["urls"][0]).split("/")[0]
        year = meet["year"]
        for q in [f"{year}年の{title}の結果URLは？", f"{title}（{year}）の公式結果はどこ？"]:
            if add(q, {"kinds": ["answered"], "any_of": ["http://", "https://", host]}):
                meet_count += 1

    arag_count = 0
    for p in sorted((ROOT / "input/idaten-corpus/aragyoku/transcripts").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        year, gender = d.get("year"), d.get("gender")
        teams = [t for t in (d.get("teams") or []) if isinstance(t, dict)]
        winner = next((t for t in teams if t.get("rank") in (1, "1")), teams[0] if teams else {})
        legs = d.get("legs") or []
        if winner.get("team") and add(
            f"{year}年荒玉駅伝{gender}の優勝チームは？",
            {
                "kinds": ["answered"],
                "any_of": [str(winner["team"]), str(year), "荒玉"],
                "forbid": ["コーチに直接聞いてください"],
            },
        ):
            arag_count += 1
        if winner.get("total") and add(
            f"{year}荒玉{gender}1位の総合タイムは？",
            {
                "kinds": ["answered"],
                "any_of": [str(winner["total"]), str(year)],
                "forbid": ["コーチに直接聞いてください"],
            },
        ):
            arag_count += 1
        dist_toks = [str(L.get("distance_km")) for L in legs if L.get("distance_km") is not None]
        if dist_toks and add(
            f"荒玉駅伝{year}{gender}の距離構成は？",
            {
                "kinds": ["answered"],
                "any_of": dist_toks[:4] + [str(year), "荒玉"],
                "forbid": ["コーチに直接聞いてください"],
            },
        ):
            arag_count += 1
        for t in teams[:3]:
            if t.get("team") and t.get("rank") and add(
                f"{year}年荒玉{gender}の{t['rank']}位はどのチーム？",
                {
                    "kinds": ["answered"],
                    "any_of": [str(t["team"]), str(year)],
                    "forbid": ["コーチに直接聞いてください"],
                },
            ):
                arag_count += 1

    clarify_qs = [
        "自己ベストは？",
        "自分の自己ベスト教えて",
        "PB教えて",
        "ベストタイムは？",
        "SBは？",
        "最新の自己ベストは？",
        "ベスト記録教えて",
        "自分のPBは？",
        "自己記録は？",
        "ベストは？",
        "自己ベスト知りたい",
        "SB教えてください",
        "ベストタイム知りたい",
        "PBは何？",
        "今の自己ベストは？",
        "自己ベストお願い",
        "SBお願い",
        "ベストタイムお願い",
        "PBお願い",
        "記録を調べたい",
        "自己ベスト教えて",
        "SBを教えて",
        "ベストタイムを教えて",
        "PBを知りたい",
        "自己記録教えて",
    ]
    clarify_count = 0
    for q in clarify_qs:
        if add(
            q,
            {
                "kinds": ["answered"],
                "any_of": ["具体的に書いて", "例:"],
                "sources_any": ["clarify:"],
            },
        ):
            clarify_count += 1

    oos = [
        "今日の天気は？",
        "明日の天気は？",
        "株価を教えて",
        "日経平均は？",
        "レシピ教えて",
        "カレーレシピ",
        "プログラミングの宿題手伝って",
        "Python書いて",
        "Rust書いて",
        "トランプ大統領について",
        "内閣について",
        "野球の試合結果は？",
        "サッカーの試合結果は？",
        "ゴルフの試合結果は？",
        "英語翻訳して",
        "中国語翻訳して",
        "占いして",
        "四柱推命して",
        "漫画のおすすめは？",
        "小説おすすめは？",
        "ChatGPTとは？",
        "Geminiとは",
        "今日の夕食のおすすめは？",
        "AIで小説書いて",
        "競馬の予想して",
        "暗号通貨いくら？",
        "仮想通貨いくら",
        "恋の相談乗って",
        "ニュースの要約して",
        "ビットコイン買べき？",
        "宿題の数学解いて",
        "あなたは誰",
        "ドル円は？",
        "アニメのおすすめは？",
        "LLMとは何",
        "Claudeとは",
        "OpenAIとは",
    ]
    oos_count = 0
    for q in oos:
        if add(q, {"kinds": ["refused"]}):
            oos_count += 1

    prac = [
        ("2025-10-20のいだてん岱明練習の内容は？", ["ジョグ", "動きづくり", "練習", "10月20"]),
        ("中体連駅伝明けの練習はどんな感じ？", ["中体連", "練習", "ジョグ"]),
        ("岱明駅伝試走はいつ？", ["試走", "10月", "駅伝"]),
        ("2026-08-20の練習会はどうなった？", ["中止", "8月20", "練習会"]),
        ("いだてん岱明って何？", ["岱明", "いだてん", "陸上"]),
        ("ディズニーのお土産を配った練習はいつ？", ["10月20", "ディズニー", "お土産"]),
        ("校内駅伝大会の日程は？", ["12月15", "校内駅伝"]),
        ("忘年会の開始時刻は？", ["10:00", "10時", "忘年会"]),
        ("なごみ駅伝の距離は？", ["3km", "2km", "なごみ"]),
        ("9/22 BBQの集合時間は？", ["8:00", "8時"]),
        ("荒玉中体連駅伝はいつ？", ["10月14", "2026-10-14", "荒玉"]),
        ("玉名市練習会&BBQはいつ？", ["9月22", "2026-09-22", "BBQ"]),
        ("2026年のなごみ駅伝はいつ？", ["2026-09-20", "9月20", "なごみ"]),
        ("荒玉駅伝の予備日は？", ["10月15", "2026-10-15", "予備"]),
        ("9/22のBBQ会場は？", ["おおはま", "ふれあい", "玉名"]),
        ("なごみ前日の練習方針は？", ["極軽", "調整", "なごみ"]),
        ("9/21は休み？", ["敬老", "休み", "休養", "9月21"]),
        ("玉名市外でも練習会に参加できる？", ["歓迎", "玉名", "市外"]),
        ("寒くなって上着持参と言った日は？", ["上着", "寒", "10月20"]),
        ("欠席者に松岡とある練習は？", ["松岡", "欠席", "10月20"]),
        ("実力テストと練習会が重なった日は？", ["8月28", "実力", "玉名"]),
        ("2025-10-02の試走は？", ["試走", "駅伝", "10月"]),
        ("2025-10-08も試走あった？", ["試走", "10月", "駅伝"]),
        ("県民スポーツ大会中止に伴う練習会は？", ["中止", "8月20", "練習会"]),
        ("駅伝について教えて", ["駅伝", "荒玉", "なごみ"]),
    ]
    prac_count = 0
    for q, a in prac:
        if add(
            q,
            {
                "kinds": ["answered"],
                "any_of": a,
                "forbid": ["コーチに直接聞いてください"],
            },
        ):
            prac_count += 1

    rounds = []
    for i in range(0, len(pairs), 10):
        chunk = pairs[i : i + 10]
        rid = len(rounds) + 1
        qs = [
            {"id": f"r{rid:03d}-q{j+1:02d}", "q": q, "expect": e}
            for j, (q, e) in enumerate(chunk)
        ]
        theme = "sb" if i < sb_count else "mixed"
        rounds.append({"id": rid, "theme": f"{theme}-{rid}", "questions": qs})

    breakdown = dict(
        sb=sb_count,
        cal=cal_count,
        meet=meet_count,
        arag=arag_count,
        clarify=clarify_count,
        oos=oos_count,
        prac=prac_count,
    )
    bank = {
        "version": 1,
        "total": len(pairs),
        "unique": len(pairs),
        "exhausted": True,
        "defaultYear": 2026,
        "breakdown": breakdown,
        "note": "Corpus-fact unique questions exhausted.",
        "rounds": rounds,
    }
    out = ROOT / "backend/data/eval-unique/questions.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8")
    print("TOTAL", len(pairs), "rounds", len(rounds), "breakdown", breakdown)


if __name__ == "__main__":
    main()
