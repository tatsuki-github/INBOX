#!/usr/bin/env python3
"""Brush up prepared Q&A for user satisfaction (ADR 059).

- Fix broken question variants: 「〜のどうだった？」→「〜はどうだった？」
- Strip ops jargon from high-traffic answers (transcript / コーパス / 使い方メモ)
- Soft-trim LINE-hostile mega dumps; keep key facts + Drive link
- Friendly rewrite for overview / alias / generic SB guides

Usage:
  python3 scripts/brush_up_prepared_qa_ux.py --dry-run
  python3 scripts/brush_up_prepared_qa_ux.py && python3 scripts/sync_prepared_qa.py
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / "input/faq/prepared-qa.v1.yaml"
NAGOMI_2026 = "https://drive.google.com/drive/folders/1k-zW0irJ-OjDjqQwUQLZIs4C6PfuR211"

FRIENDLY_ANSWERS: dict[str, str] = {
    "aragyoku-tamana-fuzoku": (
        "玉名付属中は成績表上「玉高附属」と同じチームです。"
        " 男子: 2024年2位58:13 → 2025年3位58:37。"
        " 女子: 2024年5位43:50 → 2025年10位46:55。\n"
    ),
    "sb-middle-generic": (
        "中学生の自己ベストは、選手名と距離を指定すると答えられます。"
        " 例: 「松野凛空の1500m自己ベストは？」「南関の3000m最速は誰？」。\n"
    ),
    "sb-athlete-generic": (
        "選手の記録は「選手名＋距離＋自己ベスト」で聞いてください。"
        " 例: 「村上咲稀の800m自己ベストは？」。\n"
    ),
    "sb-how-to-ask": (
        "自己ベストは「選手名＋距離＋自己ベスト/SB」が確実です。"
        " 例: 「松野の1500mSBは？」「南関の3000m最速は誰？」。\n"
    ),
    "practice-menu": (
        "練習メニューは日付を指定するとその日の内容を案内できます。"
        " 例: 「2025-11-01の練習は？」「今日の練習メニューは？」。\n"
    ),
    "track-lap": (
        "岱明のトラック1周の距離は、練習・ペース計算で使う周長の定義に従います。"
        " 詳しい運用値が必要なときはコーチに確認してください。\n"
    ),
    "aragyoku-overview-guide": (
        "荒玉駅伝は玉名・荒尾地区の中体連駅伝です（通称: 荒玉 / 荒玉中体連駅伝）。"
        " 男子6区・女子5区で、男子の距離は2024年に再編されています。"
        " 区間距離は「荒玉男子2区の距離は？」、結果は「2025年荒玉男子の岱明は何位？」のように聞いてください。\n"
    ),
    "analysis-aragyoku-overview": (
        "荒玉駅伝（荒玉中体連駅伝）は玉名・荒尾地区の中体連駅伝です。"
        " 男子6区・女子5区。男子は2024年以降の現行距離（合計17.71km）が基本です。"
        " 区間距離や順位・選手名は「○区の距離」「○年の岱明の結果」で聞けます。\n"
    ),
    "kg-first": (
        "このボットは、よくある質問の定型回答を優先して返します。"
        " 続いて関連資料をたどり、根拠のある内容だけを案内します。\n"
    ),
    "line-scope": (
        "いだてん岱明の練習・駅伝・記録・名簿・大会予定などに答えます。"
        " 一般の天気予報や雑談など、部活の範囲外は対象外です。\n"
    ),
    "source-paths-meaning": (
        "回答には必要に応じて大会フォルダや結果ページのリンクを付けます。"
        " 公開されている資料から確認できる内容を優先しています。\n"
    ),
    "silver-mat": (
        "銀マット・合同練習・保護者連絡などの運用メモは、日付や件名を指定すると案内しやすくなります。"
        " 例: 「○月○日の合同練習は？」。\n"
    ),
    "arita-practice": (
        "有田先輩の練習・補強の考え方は、関連メモや資料名を指定すると案内できます。"
        " 個人の診断や治療方針はお答えできません。\n"
    ),
    "injury": (
        "ケガ・障害の一般的な注意は資料から案内できますが、個人の診断や治療方針はお答えできません。"
        " 症状がある場合はコーチ・医療機関に確認してください。\n"
    ),
    "tamana-weather": (
        "部活の天気データ更新手順についての質問は案内できます。"
        " 一般の天気予報そのものは対象外です。\n"
    ),
    "data-update": (
        "大会結果やFAQを追加したあとは、成績・予定を更新して定型回答も増やします。"
        " 利用者向けには「○年の○○の結果は？」で最新が返るようにしています。\n"
    ),
}


def fix_awkward_questions(questions: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for q in questions:
        fixed = re.sub(r"のどうだった([？?]?)$", r"はどうだった\1", q)
        fixed = re.sub(r"のどうだった", "はどうだった", fixed)
        if fixed in seen:
            continue
        seen.add(fixed)
        out.append(fixed)
    return out


def soft_trim_area_result(answer: str, *, max_len: int = 520) -> str:
    """Keep lead ranking facts + Drive link; drop runaway full dumps."""
    urls = re.findall(r"https?://[^\s]+", answer)
    # Prefer structured summary: gender sections with team totals only
    women = re.findall(
        r"(\d+位)\s*([^\s　]+)\s*総合\s*([0-9:]+)",
        answer.split("【男子】")[0] if "【男子】" in answer else answer,
    )
    men_part = answer.split("【男子】")[1] if "【男子】" in answer else ""
    men = re.findall(r"(\d+位|オープン)\s*([^\s　]+)\s*総合\s*([0-9:—\-]+)", men_part)
    bits = ["2026年なごみ駅伝（2026-09-20）の荒玉地区の結果です。"]
    if women:
        wbits = [f"{r}{t}（{tot}）" for r, t, tot in women[:6]]
        bits.append("女子上位: " + "、".join(wbits) + "。")
    if men:
        mbits = [f"{r}{t}（{tot}）" for r, t, tot in men[:6]]
        bits.append("男子上位: " + "、".join(mbits) + "。")
    # Ensure 岱明 appears
    if "岱明" in answer and "岱明" not in "".join(bits):
        m = re.search(r"(\d+位)\s*(岱明[AB]?)\s*総合\s*([0-9:]+)", answer)
        if m:
            bits.append(f"{m.group(2)}は{m.group(1)}・{m.group(3)}。")
    body = " ".join(bits)
    doc = next((u for u in urls if "docs.google.com/document" in u), "")
    folder = next((u for u in urls if "drive.google.com/drive/folders" in u), NAGOMI_2026)
    body = body.rstrip("。") + "。 全選手の詳細は結果ドキュメント／大会フォルダで確認できます。"
    if doc:
        body += f" 荒玉地区の結果ドキュメント: {doc.rstrip('。')}"
    body += f" 資料: {folder.rstrip('。')}"
    if len(body) > max_len + 120:
        body = body[: max_len + 119].rstrip() + "…"
    return body + "\n"


def scrub_light_jargon(answer: str) -> str:
    repl = (
        ("transcript 上", "成績表上"),
        ("transcript上", "成績表上"),
        ("文字起こし", "成績表"),
        ("コーパスの", ""),
        ("コーパス内の", ""),
        ("コーパス ", ""),
        ("コーパス", "収録データ"),
        ("ナレッジグラフのルート地図", "関連資料の案内"),
        ("ナレッジ", "資料"),
        ("このドキュメントの使い方（Q&A）", "聞き方の例"),
        ("**この概要を優先**して答える。", "概要として案内します。"),
        ("**この文書を優先**", "この内容を案内します"),
        ("**この文書の区間賞表**", "区間賞の一覧"),
        ("as_of:", "基準日:"),
        ("（SB採用優先）", ""),
    )
    t = answer
    for a, b in repl:
        t = t.replace(a, b)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"。{2,}", "。", t)
    return t.strip() + ("\n" if answer.endswith("\n") or True else "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = data["entries"]
    q_fixed = ans_fixed = 0

    for e in entries:
        qs = list(e.get("questions") or [])
        new_qs = fix_awkward_questions(qs)
        if new_qs != qs:
            e["questions"] = new_qs
            q_fixed += 1

        eid = e["id"]
        before = e.get("answer") or ""
        if eid in FRIENDLY_ANSWERS:
            e["answer"] = FRIENDLY_ANSWERS[eid]
            ans_fixed += 1
            continue
        if eid in (
            "nagomi-2026-aragyoku-area-result",
            "meet-doc-2026-中学駅伝金栗四三生誕の地なごみ大会-荒玉地区の結果",
        ):
            e["answer"] = soft_trim_area_result(before)
            ans_fixed += 1
            continue

        # Only light-scrub clearly user-facing meta/analysis guides that still
        # contain ops jargon — never touch sb-/race-/records- projections.
        if (
            eid.startswith(("analysis-aragyoku", "help-", "topic-"))
            or eid.endswith("-guide")
            or eid in {"practice-menu", "track-lap", "kg-first", "line-scope"}
        ):
            scrubbed = scrub_light_jargon(before)
            scrubbed = re.sub(r"\*\*([^*]+)\*\*", r"\1", scrubbed)
            scrubbed = re.sub(r"\s{2,}", " ", scrubbed).strip() + "\n"
            if scrubbed != before:
                e["answer"] = scrubbed
                ans_fixed += 1

    print(f"entries_with_question_fixes={q_fixed} answer_rewrites={ans_fixed}")
    # remaining awkward
    left = sum(
        1
        for e in entries
        for q in e.get("questions") or []
        if "のどうだった" in q
    )
    print(f"remaining_awkward_どうだった={left}")
    if args.dry_run:
        return 0

    data["total"] = len(entries)
    note = data.get("note") or ""
    if "brush-up-prepared-qa-ux" not in note:
        data["note"] = (note.rstrip() + "\nbrush-up-prepared-qa-ux: ユーザー満足度向けに質問表記と回答を磨いた\n")
    FAQ.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
