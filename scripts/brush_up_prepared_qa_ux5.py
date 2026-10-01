#!/usr/bin/env python3
"""Round-5 UX brush-up for prepared Q&A (user satisfaction).

Focus:
  - Rewrite 2016 all-unnamed leg-best answers to school+time first
  - Fix career-unknown questions that say「未記入の〜」
  - Soft-polish a few high-traffic help answers

Usage:
  python3 scripts/brush_up_prepared_qa_ux5.py --dry-run
  python3 scripts/brush_up_prepared_qa_ux5.py && python3 scripts/sync_prepared_qa.py
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / "input/faq/prepared-qa.v1.yaml"

FRIENDLY = {
    "aragyoku-career-unknown": (
        "成績表に選手名が載っていない区間記録があります。"
        " 選手名が分かれば、その名前で聞いてください。"
        " 例: 「○○の荒玉出走歴は？」。\n"
    ),
}

CAREER_UNKNOWN_QUESTIONS = [
    "選手名不明の荒玉出走歴は？",
    "名前が載っていない荒玉の区間記録は？",
    "荒玉で選手名が未記入の記録は？",
    "成績表に名前がない荒玉の区間は？",
]


def rewrite_leg_best(ans: str) -> str | None:
    """Turn repeating 選手名未記入 into school+time focused prose."""
    a = ans.strip()
    if "選手名未記入" not in a or "最速（区間賞相当）" not in a:
        return None
    # 2016年荒玉駅伝男子1区の最速（区間賞相当）は選手名未記入（南関・12:32）です。
    m = re.match(
        r"^(?P<head>20\d{2}年荒玉駅伝(?:男子|女子)\d区の最速（区間賞相当）)は"
        r"選手名未記入（(?P<school>[^・）]+)・(?P<time>[^）]+)）です。"
        r"(?:\s*上位:\s*(?P<top>.+))?$",
        a,
    )
    if not m:
        return None
    head = m.group("head")
    school = m.group("school")
    time = m.group("time")
    body = (
        f"{head}は{school}・{time}です（選手名は文字起こし未記入）。"
    )
    top = m.group("top") or ""
    # 1位選手名未記入（南関・12:32）、2位...
    parts = []
    for tm in re.finditer(
        r"(\d)位選手名未記入（([^・）]+)・([^）]+)）", top
    ):
        parts.append(f"{tm.group(1)}位{tm.group(2)} {tm.group(3)}")
    if parts:
        body += " 上位: " + "、".join(parts) + "。"
    return body + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    n = 0
    best_n = 0
    for e in data["entries"]:
        eid = e["id"]
        before = e.get("answer") or ""
        touched = False

        if eid == "aragyoku-career-unknown":
            e["questions"] = list(CAREER_UNKNOWN_QUESTIONS)
            e["answer"] = FRIENDLY[eid]
            n += 1
            continue

        if eid in FRIENDLY:
            e["answer"] = FRIENDLY[eid]
            n += 1
            continue

        if eid.endswith("-best") and "選手名未記入" in before:
            rewritten = rewrite_leg_best(before)
            if rewritten:
                e["answer"] = rewritten
                touched = True
                best_n += 1

        # help tip: add soft recovery line if missing
        if eid in ("help-what-can-ask", "help-examples") and "具体的に" not in before:
            tip = (
                " 分からないときは「使い方」と送ると質問例が出ます。"
            )
            ans = before.rstrip()
            if not ans.endswith("。"):
                ans += "。"
            e["answer"] = ans + tip + "\n"
            touched = True

        if eid == "help-what-can-ask":
            e["answer"] = (
                "いだてん岱明のカレンダー・練習・荒玉/ジュニア/なごみ駅伝の結果・"
                "コース図/動画・自己ベストなどを質問できます。"
                " 雑談や他競技は対象外です。"
                " 曖昧なときは「使い方」と送るか、大会名・選手名・距離を付けて聞いてください。\n"
            )
            touched = True

        if touched:
            n += 1

    print(f"updated={n} leg_best={best_n}")
    if args.dry_run:
        return 0
    data["total"] = len(data["entries"])
    note = data.get("note") or ""
    if "brush-up-prepared-qa-ux5" not in note:
        data["note"] = (
            note.rstrip()
            + "\nbrush-up-prepared-qa-ux5: 区間最速の未記入表記とヘルプ案内を利用者向けに整理\n"
        )
    FAQ.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
