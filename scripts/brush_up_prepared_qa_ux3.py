#!/usr/bin/env python3
"""Round-3 UX brush-up for prepared Q&A (user satisfaction).

Focus:
  - Rebuild practice-cal / cal practice answers that still embed practice-menu:v1 dumps
  - Fix jammed / ops-y helper answers
  - Strip leftover markdown bold in team-history answers

Usage:
  python3 scripts/brush_up_prepared_qa_ux3.py --dry-run
  python3 scripts/brush_up_prepared_qa_ux3.py && python3 scripts/sync_prepared_qa.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / "input/faq/prepared-qa.v1.yaml"
sys.path.insert(0, str(ROOT / "scripts"))
from practice_renderer import render_description  # noqa: E402

NAGOMI_2026 = "https://drive.google.com/drive/folders/1k-zW0irJ-OjDjqQwUQLZIs4C6PfuR211"
ARAGYOKU_2026 = "https://drive.google.com/drive/folders/1G8IlaBp9xVmXUynBAjV9ZZQPfFqzj4Yi"

FRIENDLY = {
    "aragyoku-order-legs": (
        "荒玉駅伝の区間・オーダーは、学校名と年を指定すると案内できます。"
        " 例: 「2025年荒玉男子の岱明のオーダーは？」「岱明の2026荒玉暫定オーダーは？」。"
        " なごみ駅伝の区間オーダーは金栗駅伝とは別です。\n"
    ),
    "nagomi-order": (
        "なごみ駅伝の区間オーダーは、大会フォルダの男女「区間オーダーリスト」です。"
        " 金栗駅伝のオーダーとは別です。"
        f" 資料: {NAGOMI_2026}\n"
    ),
    "nagomi-order-friendly": (
        "なごみ駅伝の区間オーダーは大会フォルダの区間オーダーリストで確認できます"
        "（金栗駅伝とは別）。"
        f" 資料: {NAGOMI_2026}\n"
    ),
    "topic-repo-ops": (
        "大会結果や予定を追加したあとは、定型回答も更新して最新が返るようにしています。"
        " 利用者向けには「○年の○○の結果は？」「○○はいつ？」で聞いてください。\n"
    ),
}


def load_practice_index() -> dict[tuple[str, str], dict]:
    """Map (date, title) and date-only fallbacks to practice event dicts."""
    idx: dict[tuple[str, str], dict] = {}
    by_date: dict[str, list[dict]] = {}
    for year in (2025, 2026):
        path = ROOT / f"out/{year}/practice.json"
        if not path.exists():
            continue
        for ev in json.loads(path.read_text(encoding="utf-8")):
            date = str(ev.get("date") or "")
            title = str(ev.get("title") or "")
            if not date:
                continue
            idx[(date, title)] = ev
            by_date.setdefault(date, []).append(ev)
    # store date-only under ("date", "")
    for date, evs in by_date.items():
        if len(evs) == 1:
            idx[(date, "")] = evs[0]
    return idx


def parse_eid_date_title(eid: str) -> tuple[str | None, str | None]:
    # practice-cal-20250605-いだてん岱明練習 / cal-2026-20260824-いだてん岱明夕練
    m = re.match(r"^(?:practice-cal|cal-\d{4})-(\d{8})-(.+)$", eid)
    if not m:
        return None, None
    raw, title = m.group(1), m.group(2)
    date = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    # strip am/pm suffix markers used in ids
    title = title.replace("-午前", "").replace("-午後", "")
    return date, title


def friendly_practice_answer(ev: dict, *, ampm: str | None = None) -> str:
    date = ev.get("date")
    title = ev.get("title") or "練習"
    if ampm and ampm not in title:
        title = f"{title}（{ampm}）"
    parts = [f"{date} の予定「{title}」です。"]
    status = str(ev.get("status") or "")
    if status == "done":
        parts.append("実施済みです。")
    elif status in ("cancelled", "canceled"):
        parts.append("中止です。")
    practice = ev.get("practice") or {}
    if practice:
        body = render_description(practice)
        # single-line for LINE readability
        body = re.sub(r"\n+", "、", body).strip("、")
        body = re.sub(r"\s+", " ", body)
        # renderer sometimes glues pace + next distance: k/4:00900m
        body = re.sub(r"(k/\d+:\d{2})(\d+m)", r"\1、\2", body)
        # collapse "男子900m 1本目 900m k/4:00、900m" → "男子 1本目 900m k/4:00"
        body = re.sub(
            r"(?:^|、)((?:男子|女子)?)(\d+m)\s+(\d+本目)\s+\2\s+(k/\d+:\d{2})(?:、\2)?",
            lambda m: f"、{m.group(1) + ' ' if m.group(1) else ''}{m.group(3)} {m.group(2)} {m.group(4)}",
            body,
        )
        body = body.lstrip("、")
        if body:
            parts.append(body if body.endswith("。") else body + "。")
    return " ".join(parts).strip() + "\n"


def match_practice_event(eid: str, idx: dict[tuple[str, str], dict]) -> dict | None:
    date, title = parse_eid_date_title(eid)
    if not date:
        return None
    ampm = None
    if eid.endswith("-午前"):
        ampm = "午前"
    elif eid.endswith("-午後"):
        ampm = "午後"
    candidates: list[str] = []
    if title:
        if ampm:
            candidates.append(f"{title}（{ampm}）")
            candidates.append(f"{title}({ampm})")
        candidates.append(title)
        for (d, t), _ev in idx.items():
            if d != date or not t:
                continue
            if t == title or t.startswith(title) or title.startswith(t[:8]):
                if ampm and ampm not in t and ("午前" in t or "午後" in t):
                    continue
                candidates.append(t)
    for t in candidates:
        ev = idx.get((date, t))
        if ev:
            return ev
    # same-day fallback
    day_evs = []
    seen: set[int] = set()
    for (d, t), ev in idx.items():
        if d != date or not t:
            continue
        i = id(ev)
        if i in seen:
            continue
        seen.add(i)
        day_evs.append(ev)
    if ampm:
        for ev in day_evs:
            if ampm in str(ev.get("title") or ""):
                return ev
    if len(day_evs) == 1:
        return day_evs[0]
    # prefer title match substring for 夕練 / 朝練
    if title:
        for ev in day_evs:
            et = str(ev.get("title") or "")
            if title in et or et in title:
                return ev
    return idx.get((date, ""))


def needs_practice_rebuild(ans: str) -> bool:
    if "practice-menu:v1" in ans or "<!--" in ans:
        return True
    if re.search(r"\b(type|warmup|distance_m|segments):\s", ans):
        return True
    # truncated tails like "ジ。" or "k…"
    if re.search(r"(ジ。|k…|seg。|lab。)$", ans.strip()):
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    idx = load_practice_index()
    n = 0
    practice_n = 0
    for e in data["entries"]:
        eid = e["id"]
        before = e.get("answer") or ""

        if eid in FRIENDLY:
            e["answer"] = FRIENDLY[eid]
            n += 1
            continue

        if eid.startswith(("practice-cal-", "cal-")) and needs_practice_rebuild(before):
            ev = match_practice_event(eid, idx)
            if ev and (ev.get("practice") or {}).get("items") is not None:
                ampm = "午前" if eid.endswith("-午前") else ("午後" if eid.endswith("-午後") else None)
                e["answer"] = friendly_practice_answer(ev, ampm=ampm)
                n += 1
                practice_n += 1
                continue

        if "**" in before and eid.startswith("gap1000-team-hist-"):
            e["answer"] = re.sub(r"\*\*([^*]+)\*\*", r"\1", before)
            e["answer"] = re.sub(r"\s{2,}", " ", e["answer"]).strip()
            if not e["answer"].endswith("\n"):
                e["answer"] += "\n"
            # soften "2025年付近"
            e["answer"] = e["answer"].replace("2025年付近:", "2025年:")
            n += 1

    print(f"updated={n} practice_rebuilt={practice_n}")
    left = [
        e["id"]
        for e in data["entries"]
        if needs_practice_rebuild(e.get("answer") or "")
        and e["id"].startswith(("practice-cal-", "cal-"))
    ]
    print(f"remaining_practice_dumps={len(left)}")
    for i in left[:15]:
        print(" ", i)
    bold_left = sum(
        1
        for e in data["entries"]
        if e["id"].startswith("gap1000-team-hist-") and "**" in (e.get("answer") or "")
    )
    print(f"remaining_team_hist_bold={bold_left}")
    if args.dry_run:
        return 0
    data["total"] = len(data["entries"])
    note = data.get("note") or ""
    if "brush-up-prepared-qa-ux3" not in note:
        data["note"] = (
            note.rstrip()
            + "\nbrush-up-prepared-qa-ux3: 練習メニューダンプと詰まった案内を利用者向けに再構成\n"
        )
    FAQ.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
