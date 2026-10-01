#!/usr/bin/env python3
"""Round-2 UX brush-up for prepared Q&A (user satisfaction).

Focus:
  - Replace CSV/JSON/as_of dumps in meet-doc answers with short human summaries + Drive link
  - Fix thin / broken / hollow helper answers (欠席・県駅伝・コーチ案内・パス欠落)
  - Rewrite analysis / ops stubs that still read like internal runbooks
  - Remove None/? placeholders that leak into user-facing text
  - Soft-clean calendar-date / jargon leftovers

Usage:
  python3 scripts/brush_up_prepared_qa_ux2.py --dry-run
  python3 scripts/brush_up_prepared_qa_ux2.py && python3 scripts/sync_prepared_qa.py
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / "input/faq/prepared-qa.v1.yaml"

FOLDER_URLS = {
    "なごみ大会": {
        "2026": "https://drive.google.com/drive/folders/1k-zW0irJ-OjDjqQwUQLZIs4C6PfuR211",
        "2025": "https://drive.google.com/drive/folders/1NSx1uYMt2_N9ezohsnyZ4BPXIw-rfUb6",
    },
    "ジュニア": {
        "2026": "https://drive.google.com/drive/folders/1pUww3wPlyy4IoSNUy58qK9yhCRzeU_-2",
    },
    "荒玉": {
        "2026": "https://drive.google.com/drive/folders/1G8IlaBp9xVmXUynBAjV9ZZQPfFqzj4Yi",
    },
}

NAGOMI_2026 = FOLDER_URLS["なごみ大会"]["2026"]
ARAGYOKU_2026 = FOLDER_URLS["荒玉"]["2026"]

FRIENDLY = {
    "practice-absentees": (
        "欠席者は日付付きで聞くと案内できます。"
        " 例: 「2026-09-05の欠席者は？」「9月5日の練習の欠席は？」。"
        " 「今日の欠席」だけだと特定しづらいので、日付を付けてください。\n"
    ),
    "schedule-kumamoto-ekiden": (
        "熊本県駅伝など県大会の日程は、大会名を具体的に指定すると案内できます。"
        " 例: 「ジュニア駅伝はいつ？」「荒玉駅伝はいつ？」「なごみ駅伝の日程は？」。\n"
    ),
    "coach-fallback-meaning": (
        "資料に無い内容や、個人の医療・連絡先などは「コーチに直接聞いてください」と案内します。"
        " 大会結果・記録・予定など、用意済みの質問にはその回答を返します。\n"
    ),
    "analysis-aragyoku_sb_calibration": (
        "荒玉駅伝のSB区間予想を実績で補正するための目安（2024–2025）です。"
        " 正の値は予想が速すぎた（遅め補正）を意味します。"
        " 女子の区間バイアス例: 約+21 / +2 / -11 / +8 / +37秒。"
        " 男子例: 約-6 / +14 / +10 / +36 / +18 / +15秒。"
        " 詳しくは「2026荒玉男子の区間オーダー予想は？」で聞けます。\n"
    ),
    "analysis-aragyoku_sb_gap_analysis": (
        "2026年荒玉駅伝（2026-10-14予定）の数式予想・旧SB予想と実績の差をまとめる分析枠です。"
        " 大会後に実績が入ると、予実差の表として使えます。"
        " いま聞ける予想は「今年の荒玉戦力分析（校別）は？」が分かりやすいです。\n"
    ),
    "analysis-aragyoku_leg_awards": (
        "荒玉駅伝の区間賞・区間上位の一覧です。"
        " 「2025年荒玉駅伝の区間賞は誰？」「2025年荒玉男子2区の区間順位は？」のように"
        " 年・男女・区間を指定すると答えやすいです。\n"
    ),
    "analysis-aragyoku_meet_records": (
        "荒玉駅伝ボード上部の大会記録・区間記録の案内です。"
        " 「男子2区の大会区間記録は誰？」「2025年の大会記録は？」のように指定してください。"
        " 男子は2024年以降のコース再編で記録が分かれます。\n"
    ),
    "nagomi-gap": (
        "なごみ駅伝のSB予想と実績の差は、大会フォルダの成績・ギャップ分析で確認できます。"
        f" 2026年資料: {NAGOMI_2026}"
        " 岱明の結果は「なごみ駅伝の結果は？」でも聞けます。\n"
    ),
    "youkou-generic": (
        "開催要項は大会名を指定すると案内しやすいです。"
        " 例: 「なごみ駅伝の開催要項は？」「ジュニア駅伝の要項は？」「荒玉駅伝の要項は？」。\n"
    ),
    "sb-takada-mana": (
        "高田麻那（文徳高）の記録は、SBデータベースで選手名指定すると案内できます。"
        " 岱明の高田麻由とは別人です。例: 「高田麻那の1500m自己ベストは？」。\n"
    ),
    "sb-nankan": (
        "南関中の所属選手の記録は、選手名＋距離で聞くのが確実です。"
        " 例: 「南関の3000m最速は誰？」「稗島葵音の1500mSBは？」。\n"
    ),
    "sb-kanaguri-project": (
        "金栗PROJECT所属選手の記録は、選手名＋距離で聞いてください。"
        " 駅伝の開催要項フォルダとは別資料です。例: 「○○の1500m自己ベストは？」。\n"
    ),
    "ai-practice": (
        "AI練習生成は、カレンダー・テンプレ・制約をもとに練習シートを作る仕組みです。"
        " 「○月○日の練習は？」「今日の練習メニューは？」のように日付で聞くと案内しやすいです。\n"
    ),
    "topic-kg": (
        "よくある質問は定型回答を優先し、必要なら関連資料のパスをたどって答えます。"
        " 大会結果や予定は「○年の○○の結果は？」「○○はいつ？」が分かりやすいです。\n"
    ),
    "topic-external-index": (
        "Notion・Googleドライブ由来の資料は、大会名・日付を指定すると案内できます。"
        " 例: 「なごみ駅伝の成績表は？」「荒玉のコース画像は？」。\n"
    ),
    "topic-media-ocr": (
        "駅伝のコース図・結果ボード画像は、大会名や地点名で聞けます。"
        " 例: 「荒玉のコース画像は？」「荒玉の橋の上のポイントは？」。\n"
    ),
    "calendar-date": (
        "日付の予定例です。2026-09-20はなごみ駅伝、2026-09-26は県ジュニア駅伝、"
        " 2026-10-14は荒玉中体連駅伝です。"
        " 「○月○日の予定は？」「なごみ駅伝はいつ？」のように聞いてください。\n"
    ),
    "daiming-club-schools": (
        "荒玉クラブ所属生徒の中学校振分は、メモ「荒玉クラブ所属生徒の中学校」に基づきます。"
        " 不明な場合は不明分類とします。学校名を指定すると個別に案内しやすいです。\n"
    ),
    "competitor-analysis": (
        "荒玉の競合・戦力は学校名を指定すると案内できます。"
        " 例: 「今年の荒玉戦力分析（校別）は？」「南関の荒玉予想は？」「岱明のライバル校は？」。\n"
    ),
    "aragyoku-2019-男子-winner": (
        "2019年荒玉駅伝男子の優勝は玉名、準優勝は玉東です。"
        " （文字起こし上、総合タイム欄は未記入のためタイムは省略）\n"
    ),
    "aragyoku-2019-男子-runnerup": (
        "2019年荒玉駅伝男子の準優勝は玉東です。優勝は玉名です。"
        " （文字起こし上、総合タイム欄は未記入のためタイムは省略）\n"
    ),
    "aragyoku-2019-男子-winner-ask": (
        "2019年荒玉駅伝男子の優勝は玉名です。対して準優勝は玉東です。"
        " （総合タイムは文字起こし未記入のため省略）\n"
    ),
    "aragyoku-2019-男子-runnerup-ask": (
        "2019年荒玉駅伝男子の準優勝は玉東です。対して優勝は玉名です。"
        " （総合タイムは文字起こし未記入のため省略）\n"
    ),
    "recent-2026-藤井祐吏-なごみ大会": (
        "藤井祐吏（荒尾第四中）の2026年度・なごみ大会の結果です。"
        " 2026-09-20 男子オープン・1区 10:15（区間19位）。"
        " 荒尾第四オープン総合 37:25（1区藤井祐吏、2区松岡颯希、3区浦本崇彦）。\n"
    ),
    "meet-doc-2026-荒玉中体連駅伝-予実比較": (
        "2026年荒玉駅伝の予実比較（数式予想・旧SB予想と実績の差）用の枠です。"
        " 開催は2026-10-14予定で、大会後に実績が入ると使えます。"
        f" 予想の確認は「今年の荒玉戦力分析（校別）は？」が分かりやすいです。 資料: {ARAGYOKU_2026}\n"
    ),
    "meet-doc-2026-荒玉中体連駅伝-公式オーダー待ち": (
        "2026年荒玉駅伝は公式の全チームオーダー待ちです。"
        " 岱明は暫定オーダーあり（男子5–6区は仮置き）。"
        f" 「岱明の2026荒玉暫定オーダーは？」で確認できます。 資料: {ARAGYOKU_2026}\n"
    ),
    "meet-doc-2026-中学駅伝金栗四三生誕の地なごみ大会-プログラム": (
        "2026年なごみ駅伝（第12回、2026-09-20）のプログラム概要です。"
        " 会場: 和水町三加和公民館。男子1周3km・女子1周2kmの周回。"
        f" 主催: 和水町陸上競技協会・K-PROJECT。 資料: {NAGOMI_2026}\n"
    ),
}


def meet_kind(eid: str) -> tuple[str, str]:
    year = "2026" if "-2026-" in eid or eid.startswith("meet-doc-2026") else "2025"
    if "なごみ" in eid:
        return "なごみ大会", year
    if "ジュニア" in eid:
        return "ジュニア", year
    if "荒玉" in eid:
        return "荒玉", year
    return "大会", year


def doc_label(eid: str) -> str:
    m = re.search(
        r"(エントリーリスト|成績表|プログラム|公式オーダー待ち|校別展開予想|"
        r"予実比較|区間オーダー[^/]*|女子区間オーダー[^/]*|男子区間オーダー[^/]*|"
        r"スタートリスト|区間オーダー変更|coverage)$",
        eid,
    )
    if m:
        return m.group(1).replace("_", " ")
    return eid.split("-")[-1].replace("_", " ")


def friendly_meet_doc(eid: str) -> str:
    kind, year = meet_kind(eid)
    label = doc_label(eid)
    url = FOLDER_URLS.get(kind, {}).get(year, "")
    meet_name = {
        "なごみ大会": "なごみ駅伝",
        "ジュニア": "県ジュニア駅伝",
        "荒玉": "荒玉駅伝",
    }.get(kind, "大会")

    if "coverage" in eid or eid.endswith("_coverage"):
        body = (
            f"{year}年{meet_name}の「{label}」は集計用データです。"
            f" 利用者向けにはオーダー予想や結果の質問の方が分かりやすいです。"
            f" 例: 「{year}年{meet_name}の区間オーダー予想は？」「{meet_name}の結果は？」。"
        )
    elif "SB予想" in eid or "数式予想" in eid:
        body = (
            f"{year}年{meet_name}の区間オーダー予想（{label}）です。"
            f" 自己ベストなどから算出した目安で、確定オーダーではありません。"
        )
        if kind == "荒玉":
            body += " 「今年の荒玉戦力分析（校別）は？」や「岱明の2026荒玉暫定オーダーは？」も便利です。"
        elif kind == "なごみ":
            body += " 結果は「なごみ駅伝の結果は？」で聞けます。"
    elif "オーダーリスト" in eid or "エントリーリスト" in eid or "スタートリスト" in eid:
        body = (
            f"{year}年{meet_name}の{label}です。"
            f" チーム・区間メンバーの一覧は大会フォルダで確認できます。"
        )
    elif "公式オーダー待ち" in eid:
        body = (
            "2026年荒玉駅伝は公式の全チームオーダー待ちです。"
            " 岱明は暫定オーダーあり（男子5–6区は仮置き）。"
            " 「岱明の2026荒玉暫定オーダーは？」で確認できます。"
        )
    elif "校別展開予想" in eid:
        body = (
            "2026年荒玉駅伝の校別展開予想です（更新2026-09-27、開催2026-10-14）。"
            " 公式オーダー前の目安です。「今年の荒玉戦力分析（校別）は？」でも聞けます。"
        )
    elif "予実比較" in eid:
        body = (
            f"{year}年{meet_name}の予実比較用の枠です。"
            " 大会後に実績が入ると、予想との差を確認できます。"
        )
    elif "成績表" in eid:
        if kind == "なごみ大会":
            body = (
                f"{year}年{meet_name}の成績表です。"
                f" 岱明の結果は「{year}年のなごみ駅伝の結果は？」が分かりやすいです。"
            )
        else:
            body = (
                f"{year}年{meet_name}の成績表です。"
                " 大会名・順位・学校名で聞くと答えやすいです。"
            )
    elif "プログラム" in eid:
        body = f"{year}年{meet_name}のプログラム・要項の案内です。開催日・会場は大会名で聞けます。"
    elif "区間オーダー変更" in eid:
        body = (
            f"{year}年{meet_name}の区間オーダー変更メモです。"
            f" 確定メンバーは「{meet_name}の結果は？」や大会フォルダで確認できます。"
        )
    else:
        body = f"{year}年{meet_name}の「{label}」です。"

    if url:
        body += f" 資料: {url}"
    return body.strip() + "\n"


def is_dump_answer(ans: str) -> bool:
    if re.search(r"\bas_of\b|gender,team|pred_cum|\"event\":|source:", ans):
        return True
    if "表構造MD化" in ans or "本スクリプト" in ans or "予定ワークフロー" in ans:
        return True
    if ans.count(",") >= 8 and re.search(r"[a-z]{3,},[a-z]{3,}", ans):
        return True
    return False


def scrub_placeholders(ans: str) -> str:
    out = ans
    out = out.replace("（None）", "").replace("(None)", "")
    out = out.replace("チームNone位", "オープン参加")
    out = out.replace("None位", "")
    out = re.sub(r"（\?）", "", out)
    out = re.sub(r"\(\?\)", "", out)
    out = re.sub(r"None年", "", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"（\s*）", "", out)
    return out


def fix_media_none(entry: dict) -> bool:
    eid = entry["id"]
    if not eid.startswith("media-ekiden-"):
        return False
    changed = False
    qs = entry.get("questions") or []
    new_qs = []
    for q in qs:
        nq = q.replace("None年", "").replace("None荒玉", "荒玉")
        nq = re.sub(r"\s{2,}", " ", nq).strip()
        if nq != q:
            changed = True
        new_qs.append(nq)
    if changed:
        entry["questions"] = new_qs
    ans = entry.get("answer") or ""
    if "None年" in ans or ans.startswith("年荒玉"):
        # course-point style media
        if "コース" in eid or "ポイント" in eid or "橋" in eid:
            entry["answer"] = (
                "荒玉駅伝のコース共通ポイント（橋の上）の図解です。"
                " 女子1〜5区・男子1〜6区が共有する地点の案内。"
                + (" " + ans.split("。", 1)[-1].lstrip() if "。" in ans else "")
            )
            if not entry["answer"].endswith("\n"):
                entry["answer"] += "\n"
        else:
            entry["answer"] = scrub_placeholders(ans)
            if entry["answer"].startswith("荒玉") is False and entry["answer"].startswith("年"):
                entry["answer"] = "荒玉駅伝" + entry["answer"][1:]
        changed = True
    return changed


def polish_gap1000_status(ans: str) -> str:
    """Drop ops-y ステータス: done noise; keep race facts."""
    if "ステータス:" not in ans:
        return ans
    out = re.sub(r"\s*ステータス:\s*\S+", "", ans)
    out = re.sub(r"\s{2,}", " ", out).strip()
    if not out.endswith("\n"):
        out += "\n"
    return out


def friendly_practice_doc(eid: str, ans: str) -> str | None:
    if not eid.startswith("practice-doc-"):
        return None
    if not is_dump_answer(ans) and "source:" not in ans and "fetched:" not in ans:
        return None
    # Keep human overview; drop machine metadata
    out = re.sub(r"source:\s*\S+", "", ans)
    out = re.sub(r"site:\s*[^。\n]+", "", out)
    out = re.sub(r"fetched:\s*\S+", "", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    if not out.endswith("。") and not out.endswith("です"):
        if not out.endswith("。"):
            out = out.rstrip("。") + "。"
    return out + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    n = 0
    for e in data["entries"]:
        eid = e["id"]
        before = e.get("answer") or ""
        touched = False

        if eid in FRIENDLY:
            e["answer"] = FRIENDLY[eid]
            n += 1
            continue

        if eid.startswith("meet-doc-") and (
            is_dump_answer(before)
            or "coverage" in eid
            or "SB予想" in eid
            or "数式予想" in eid
            or "オーダーリスト" in eid
            or "公式オーダー待ち" in eid
            or "エントリーリスト" in eid
            or "スタートリスト" in eid
            or "校別展開予想" in eid
            or "予実比較" in eid
            or "プログラム" in eid
            or "区間オーダー変更" in eid
            or eid.endswith("-成績表")
        ):
            e["answer"] = friendly_meet_doc(eid)
            n += 1
            continue

        pd = friendly_practice_doc(eid, before)
        if pd is not None:
            e["answer"] = pd
            n += 1
            continue

        if fix_media_none(e):
            touched = True

        ans = e.get("answer") or before
        if eid.startswith("gap1000-meet-") and "ステータス:" in ans:
            ans2 = polish_gap1000_status(ans)
            if ans2 != ans:
                e["answer"] = ans2
                ans = ans2
                touched = True

        if "None" in ans or "（?）" in ans or "(?)" in ans:
            ans2 = scrub_placeholders(ans)
            if ans2 != ans:
                e["answer"] = ans2
                ans = ans2
                touched = True

        # strip leftover bold in rivals / meet-doc leftovers
        if "**" in ans and (
            eid.startswith(("daiming-rivals", "gap1000-rivals", "meet-doc-"))
        ):
            e["answer"] = re.sub(r"\*\*([^*]+)\*\*", r"\1", ans)
            if not e["answer"].endswith("\n"):
                e["answer"] += "\n"
            touched = True

        if touched:
            n += 1

    print(f"updated={n}")
    left = [
        e["id"]
        for e in data["entries"]
        if e["id"].startswith("meet-doc-") and is_dump_answer(e.get("answer") or "")
    ]
    print(f"remaining_dumpish={len(left)}")
    for i in left[:10]:
        print(" ", i)
    none_left = [
        e["id"]
        for e in data["entries"]
        if "None" in (e.get("answer") or "")
        or any("None" in q for q in (e.get("questions") or []))
    ]
    print(f"remaining_none={len(none_left)}")
    for i in none_left[:15]:
        print(" ", i)
    if args.dry_run:
        return 0
    data["total"] = len(data["entries"])
    note = data.get("note") or ""
    if "brush-up-prepared-qa-ux2" not in note:
        data["note"] = (
            note.rstrip()
            + "\nbrush-up-prepared-qa-ux2: meet-docダンプ・薄い案内・None漏れをユーザー向けに整理\n"
        )
    FAQ.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
