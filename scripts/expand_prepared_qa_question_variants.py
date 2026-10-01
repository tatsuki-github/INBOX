#!/usr/bin/env python3
"""Expand prepared FAQ question phrasing variants (ADR 059).

Adds surface-form paraphrases whose *normalized* form is new for the entry,
so slight wording differences still hit matchPreparedAnswer without bloating
duplicate norms. Does not invent new answers.

Usage:
  python3 scripts/expand_prepared_qa_question_variants.py --dry-run
  python3 scripts/expand_prepared_qa_question_variants.py
  python3 scripts/expand_prepared_qa_question_variants.py && python3 scripts/sync_prepared_qa.py
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"

SKIP_ID_PREFIXES = (
    "help-examples",
    "out-of-scope",
    "coach-fallback",
    "clarify-",
    "kg-first",
    "line-scope",
    "norwegian",
    "result-board-how",
    "course-video-how",
    "course-image-how",
)

MAX_QUESTIONS_PER_ENTRY = 8
DEFAULT_YEAR = 2026
PREV_YEAR = DEFAULT_YEAR - 1

CORE_EXTRAS: dict[str, list[str]] = {
    "aragyoku-men-distance": [
        "男子の荒玉の距離は？",
        "荒玉の男子距離は？",
        "荒玉男子は何キロ？",
        "荒玉駅伝男子何km？",
    ],
    "aragyoku-women-distance": [
        "女子の荒玉の距離は？",
        "荒玉の女子距離は？",
        "荒玉女子は何キロ？",
    ],
    "aragyoku-2025-daiming-men": [
        "去年岱明男子何位？",
        "昨年の岱明男子は何位？",
        "去年の岱明男子何位？",
        "2025岱明男子の順位は？",
    ],
    "aragyoku-2025-daiming-women": [
        "去年岱明女子何位？",
        "昨年の岱明女子は何位？",
        "去年の岱明女子何位？",
    ],
    "aragyoku-pref-top2-core": [
        "荒玉で2位まで県に出れる？",
        "荒玉で2位まで県に出られる？",
        "荒玉2位まで県に出れる？",
        "荒玉駅伝で2位まで県駅伝に出れる？",
    ],
    "aragyoku-what": [
        "荒玉はどういう大会？",
        "荒玉駅伝ってどんな大会？",
        "荒玉ってどんな大会？",
    ],
    "cal-2026-20260920-第12回中学駅伝金栗四三生誕の地なごみ大会": [
        "なごみはいつ開催？",
        "なごみ駅伝はいつ開催？",
        "なごみの開催日は？",
    ],
    "meet-result-2026-全日本中学校通信陸上競技大会熊本県大会": [
        "通信陸上の結果は？",
        "通信陸上の結果URLは？",
        "通信陸上の結果リンクは？",
        "今年の通信陸上の結果は？",
        "県通信の結果は？",
    ],
    "sb-2026-田上颯人-1500m": [
        "田上颯人の1500のベストは？",
        "田上颯人の1500ベストは？",
        "田上颯人の1500の自己ベストは？",
    ],
}

LEXICAL_SWAPS: list[tuple[str, list[str]]] = [
    ("優勝校", ["優勝チーム", "優勝は誰", "優勝はどこ", "1位はどこ"]),
    ("優勝チーム", ["優勝校", "優勝は誰"]),
    ("の優勝は？", ["の優勝は誰？", "の優勝チームは？", "誰が勝った？"]),
    ("自己ベスト", ["ベストタイム", "自己記録", "SB", "ベスト"]),
    ("のSBは", ["の自己ベストは", "のベストタイムは", "の自己記録は", "のベストは"]),
    ("の結果は", ["の成績は", "はどうだった"]),
    ("結果は？", ["成績は？", "どうだった？"]),
    ("何位？", ["順位は？", "何位だった？"]),
    ("は何位？", ["の順位は？", "は何位だった？"]),
    ("区間距離", ["距離"]),
    ("生徒一覧", ["部員一覧", "名簿", "部員名簿", "陸上部の名簿", "選手一覧"]),
    ("部員名簿", ["生徒一覧", "名簿", "陸上部名簿", "選手一覧"]),
    ("タイム差", ["差", "秒差"]),
    ("出場できる", ["出られる", "出れる"]),
    ("出られる", ["出場できる", "出れる"]),
    ("コースの画像", ["コース図", "コースの地図"]),
    ("コース図", ["コースの画像", "コースの地図"]),
    ("いつ？", ["日程は？", "開催日は？", "いつ開催？"]),
    ("の日程は", ["はいつ", "の開催日は", "はいつ開催"]),
    ("荒玉駅伝", ["荒玉", "荒玉中体連駅伝", "郡市駅伝"]),
    ("荒玉中体連駅伝", ["荒玉駅伝", "荒玉"]),
    ("って何？", ["とは？", "ってどんな大会？", "はどういう大会？"]),
    ("とは？", ["って何？", "ってどんな大会？"]),
]

# Mirror key preparedQa.ts synonym / noise rules (approx) so we only keep
# candidates that change the normalized key.
_SYNONYM_ALTS = [
    ("コース図", "画像"),
    ("図解", "画像"),
    ("地図", "画像"),
    ("写真", "画像"),
    ("成績", "結果"),
    ("どうだった", "結果"),
    ("優勝チーム", "優勝"),
    ("優勝校", "優勝"),
    ("誰が勝った", "優勝"),
    ("ベストタイム", "自己ベスト"),
    ("自己記録", "自己ベスト"),
    ("ベスト記録", "自己ベスト"),
    ("県ジュニア", "ジュニア"),
    ("ジュニア駅伝", "ジュニア"),
    ("なごみ駅伝", "なごみ"),
    ("部員名簿", "名簿"),
    ("部員一覧", "名簿"),
    ("生徒一覧", "名簿"),
    ("陸上部名簿", "名簿"),
    ("陸上部員", "名簿"),
    ("タイム差", "差"),
    ("秒差", "差"),
    ("出場できる", "出場できる"),
    ("出られる", "出場できる"),
    ("出れる", "出場できる"),
    ("開催日", "予定"),
    ("日程", "予定"),
]


def approx_norm(q: str) -> str:
    """Approximate normalizePreparedQuestion for dedupe (not a full port)."""
    s = unicodedata.normalize("NFKC", q).strip()
    s = re.sub(r"前年比|前年度比", "同比", s)
    s = re.sub(r"今年度|今季|今年", f"{DEFAULT_YEAR}年", s)
    s = re.sub(r"一昨年|おととし", f"{DEFAULT_YEAR - 2}年", s)
    s = re.sub(r"昨年度|前年度|前年|去年|昨年", f"{PREV_YEAR}年", s)
    # school / aragyoku long forms (subset)
    for a, b in (
        ("荒尾第四中学校", "荒尾四"),
        ("荒尾第四中", "荒尾四"),
        ("荒尾第四", "荒尾四"),
        ("荒尾四中", "荒尾四"),
        ("玉名付属中", "玉高附属"),
        ("玉名附属中", "玉高附属"),
        ("玉名付属", "玉高附属"),
        ("岱明中学校", "岱明"),
        ("岱明中", "岱明"),
        ("いだてん岱明", "岱明"),
        ("南関中学校", "南関"),
        ("南関中", "南関"),
        ("荒玉中体連駅伝", "荒玉"),
        ("玉名荒尾中体連駅伝", "荒玉"),
        ("郡市駅伝", "荒玉"),
        ("荒玉駅伝", "荒玉"),
    ):
        s = s.replace(a, b)
    s = re.sub(r"[?？!！。．、,，・]", "", s)
    s = re.sub(r"(を)?(教えて|見せて|知りたい|ください|下さい|お願い|ですか|でしょうか)+$", "", s)
    s = re.sub(r"(だった|なの|かな)$", "", s)
    s = re.sub(r"って(どんな|どういう)(大会|もの)?$", "ってなに", s)
    s = re.sub(r"(は|って)?どんな(大会|もの)?$", "ってなに", s)
    s = re.sub(r"(は|って)?どういう(大会|もの)?$", "ってなに", s)
    s = re.sub(r"とは$", "ってなに", s)
    s = re.sub(r"のベスト(?!タイム|記録)", "の自己ベスト", s)
    s = re.sub(r"(は|って)?$", "", s)
    s = s.replace("いつ開催", "いつ")
    if re.search(r"自己ベスト|ベスト|sb|記録", s, re.I):
        s = re.sub(r"(?<![0-9.])(800|1500|3000|5000)(?![0-9.a-zｍmメートル])", r"\1m", s, flags=re.I)
    s = s.lower()
    # longer synonym alts first
    for alt, canon in sorted(_SYNONYM_ALTS, key=lambda x: -len(x[0])):
        s = s.replace(alt.lower(), canon.lower())
    s = s.replace("の", "")
    s = re.sub(r"\s+", "", s)
    return s


def expand_one(q: str, *, entry_year: int | None) -> list[str]:
    out: list[str] = []
    seen = {q}

    def add(cand: str | None) -> None:
        if not cand:
            return
        cand = re.sub(r"\s+", "", cand.strip())
        if not cand or cand in seen or len(cand) < 4 or len(cand) > 72:
            return
        seen.add(cand)
        out.append(cand)

    for src, alts in LEXICAL_SWAPS:
        if src not in q:
            continue
        for alt in alts:
            add(q.replace(src, alt, 1))

    if "荒玉" in q and "荒玉駅伝" not in q and "荒玉中体連" not in q:
        add(q.replace("荒玉", "荒玉駅伝", 1))

    if entry_year == PREV_YEAR or re.search(rf"{PREV_YEAR}年", q):
        if re.search(rf"{PREV_YEAR}年", q):
            for alt in ("去年", "昨年"):
                add(re.sub(rf"{PREV_YEAR}年", alt, q, count=1))
        for rel in ("去年", "昨年"):
            if rel in q:
                add(q.replace(rel, f"{PREV_YEAR}年", 1))

    if entry_year == DEFAULT_YEAR or re.search(rf"{DEFAULT_YEAR}年", q):
        if f"{DEFAULT_YEAR}年" in q:
            add(q.replace(f"{DEFAULT_YEAR}年", "今年", 1))
        if "今年" in q:
            add(q.replace("今年", f"{DEFAULT_YEAR}年", 1))

    m = re.search(r"(20\d{2}年)の", q)
    if m:
        add(q.replace(f"{m.group(1)}の", m.group(1), 1))
    else:
        m2 = re.search(r"(20\d{2}年)(?!の)", q)
        if m2:
            add(q.replace(m2.group(1), f"{m2.group(1)}の", 1))

    if re.search(r"\d+m", q) and ("ベスト" in q or "SB" in q or "記録" in q):
        add(re.sub(r"(\d+)m", r"\1", q, count=1))

    return out


def entry_year(entry: dict) -> int | None:
    eid = str(entry.get("id") or "")
    m = re.search(r"(?:^|-)((?:20)\d{2})(?:-|$)", eid)
    if m:
        return int(m.group(1))
    for tag in entry.get("tags") or []:
        if isinstance(tag, int) and 2000 <= tag <= 2100:
            return tag
        if isinstance(tag, str) and re.fullmatch(r"20\d{2}", tag):
            return int(tag)
    return None


def should_skip(entry: dict) -> bool:
    eid = str(entry.get("id") or "")
    return any(eid == p or eid.startswith(p) for p in SKIP_ID_PREFIXES)


def expand_entries(entries: list[dict], *, max_per: int) -> tuple[int, int, int, int]:
    claimed_raw: set[str] = set()
    for e in entries:
        for q in e.get("questions") or []:
            if isinstance(q, str) and q.strip():
                claimed_raw.add(q.strip())

    touched = added = collisions = skipped_same_norm = 0

    for e in entries:
        if should_skip(e):
            continue
        qs = [q for q in (e.get("questions") or []) if isinstance(q, str) and q.strip()]
        if not qs:
            continue
        ey = entry_year(e)
        new_qs = list(qs)
        local_raw = set(qs)
        local_norms = {approx_norm(q) for q in qs}
        before = len(new_qs)

        def try_add(cand: str, *, force: bool = False) -> None:
            nonlocal added, collisions, skipped_same_norm
            if cand in local_raw:
                return
            if cand in claimed_raw:
                collisions += 1
                return
            n = approx_norm(cand)
            if not n:
                return
            if n in local_norms and not force:
                skipped_same_norm += 1
                return
            if not force and len(new_qs) >= max_per:
                return
            new_qs.append(cand)
            local_raw.add(cand)
            local_norms.add(n)
            claimed_raw.add(cand)
            added += 1

        for cand in CORE_EXTRAS.get(str(e.get("id") or ""), []):
            try_add(cand, force=True)

        if len(qs) < max_per:
            for q in qs:
                if len(new_qs) >= max_per:
                    break
                for cand in expand_one(q, entry_year=ey):
                    if len(new_qs) >= max_per:
                        break
                    try_add(cand)

        if len(new_qs) > before:
            e["questions"] = new_qs
            touched += 1

    return touched, added, collisions, skipped_same_norm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-per-entry", type=int, default=MAX_QUESTIONS_PER_ENTRY)
    args = parser.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise SystemExit("invalid FAQ yaml")
    entries: list[dict] = data["entries"]

    before_qs = sum(len(e.get("questions") or []) for e in entries)
    touched, added, collisions, skipped_same = expand_entries(
        entries, max_per=args.max_per_entry
    )
    after_qs = sum(len(e.get("questions") or []) for e in entries)

    print(f"entries: {len(entries)}")
    print(f"touched entries: {touched}")
    print(f"questions before/after: {before_qs} -> {after_qs} (+{added})")
    print(f"collisions skipped: {collisions}")
    print(f"same-norm skipped: {skipped_same}")
    print(f"mean questions/entry: {after_qs / max(len(entries), 1):.2f}")

    if args.dry_run:
        print("dry-run: not writing")
        return 0

    data["total"] = len(entries)
    FAQ.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    print(f"wrote {FAQ}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
