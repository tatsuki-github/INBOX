#!/usr/bin/env python3
"""Generate prepared FAQ: 岱明中の荒玉ライバル校（ADR 059）.

正本: out/analysis/aragyoku_daiming_rivals.md
（2025隣接順位 + 2026トラック層）

Usage:
  python3 scripts/generate_prepared_qa_daiming_rivals.py
  python3 scripts/generate_prepared_qa_daiming_rivals.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import entry  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
ID_PREFIX = "daiming-rivals-"
SOURCES = [
    "out/analysis/aragyoku_daiming_rivals.md",
    "input/aragyoku/men_full_2012_2025.json",
    "input/aragyoku/women_full_2012_2025.json",
    "out/analysis/2026_men_1500m_pb_school_ranking.md",
    "out/analysis/2026_women_800m_1500m_pb_school_ranking.md",
]

CORE_ANSWER = (
    "荒玉駅伝で岱明中とライバルになりそうな学校は、直近順位の隣と今年度トラック層の近さから見ると次のとおりです。\n"
    "・男子: 荒尾三・南関（2025は岱明6位で前後±10秒）。2026の1500m上位4人平均でも南関・荒尾第四と秒差。"
    " 一歩上〜上位帯は長洲・玉名附（玉高附属）・玉陵・菊水。\n"
    "・女子: 長洲・荒尾三が本命。2025駅伝の前後は荒尾四・荒尾海陽。"
    " 2026の800m/1500m学校別でも長洲・荒尾三・南関が同帯（上位5人平均は岱明首位だが長洲とほぼ同タイム）。\n"
    "玉名付属・天水・有明は比較でよく見る相手ですが、2025男子では玉高附属が3位、有明・天水は岱明より後ろです。"
    " 確定の対戦表ではなく、出場・コンディションで変わります。"
)

MEN_ANSWER = (
    "岱明男子のライバル候補は **荒尾三・南関** です。"
    " 2025荒玉は岱明6位・59:08で、荒尾三（5位58:58）・南関（7位59:18）が±10秒。"
    " 2026男子1500m上位4人平均でも岱明は5位・4:30.05で、南関（4:30.04）・荒尾第四（4:30.18）と秒差。"
    " 上位を狙うなら長洲・玉名附・玉陵・菊水帯も視野です。"
)

WOMEN_ANSWER = (
    "岱明女子のライバル候補は **長洲・荒尾三** が本命です。"
    " 2026の800m/1500m学校別で同帯に並び、上位5人平均は岱明首位ですが長洲とほぼ同タイム。"
    " 2025荒玉では岱明7位・45:22で、前後は荒尾四（6位）・荒尾海陽（8位）、上に荒尾三・長洲がいます。"
    " 南関もトラック層で近い相手です。"
)

NEAR_ANSWER = (
    "2025荒玉駅伝で岱明のすぐ前後にいた学校は次のとおりです。\n"
    "・男子（岱明6位）: 先着 荒尾三、後着 南関（どちらも総合差10秒）。\n"
    "・女子（岱明7位）: 先着 荒尾四、後着 荒尾海陽。\n"
    "今年度トラック層まで含めると、男子は南関・荒尾第四、女子は長洲・荒尾三が特に近いです。"
)


def load_faq() -> dict:
    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise SystemExit("invalid FAQ yaml")
    return data


def save_faq(data: dict) -> None:
    data["total"] = len(data["entries"])
    FAQ.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def upsert(existing: list[dict], new_entries: list[dict]) -> tuple[int, int]:
    by_id = {e["id"]: i for i, e in enumerate(existing)}
    added = updated = 0
    for e in new_entries:
        eid = e["id"]
        if eid in by_id:
            existing[by_id[eid]] = e
            updated += 1
        else:
            existing.append(e)
            by_id[eid] = len(existing) - 1
            added += 1
    return added, updated


def _dedupe(qs: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for q in qs:
        q = " ".join(q.split()).strip()
        if not q or q in seen:
            continue
        seen.add(q)
        out.append(q)
    return out


def core_questions() -> list[str]:
    schools = ["岱明中", "岱明", "いだてん岱明"]
    rivals = ["ライバル", "競合校", "対抗校", "近い学校", "対戦相手"]
    qs: list[str] = []
    for s in schools:
        for r in rivals:
            qs.extend(
                [
                    f"荒玉駅伝で{s}と{r}になりそうな学校は？",
                    f"荒玉で{s}の{r}は？",
                    f"{s}の荒玉{r}はどこ？",
                    f"{s}と荒玉で勝負になりそうな学校は？",
                ]
            )
        qs.extend(
            [
                f"{s}のライバル校は？",
                f"{s}の競合はどの学校？",
                f"{s}とタイムが近い学校は？",
                f"{s}のライバルになりそうな中学は？",
                f"荒玉駅伝の{s}ライバル",
                f"{s}対抗馬は？",
            ]
        )
    qs.extend(
        [
            "荒玉駅伝で岱明中とライバルになりそうな学校は？",
            "岱明中の荒玉ライバル校を教えて",
            "岱明の競合校は？",
            "岱明と競り合いそうな学校は？",
            "荒玉で岱明と並びそうな学校",
            "岱明の敵校は？",
            "いだてん岱明のライバルは？",
            "荒玉競合で岱明の相手は？",
            "岱明中と近い順位の学校は？",
            "岱明の同帯校は？",
        ]
    )
    return _dedupe(qs)


def men_questions() -> list[str]:
    return _dedupe(
        [
            "岱明男子のライバル校は？",
            "荒玉男子で岱明の競合は？",
            "岱明中男子と近い学校は？",
            "荒玉駅伝男子の岱明ライバルは？",
            "岱明男子とタイムが近い学校は？",
            "2025荒玉男子で岱明の前後は？",
            "岱明男子の隣接校は？",
            "男子の岱明対抗はどこ？",
        ]
    )


def women_questions() -> list[str]:
    return _dedupe(
        [
            "岱明女子のライバル校は？",
            "荒玉女子で岱明の競合は？",
            "岱明中女子と近い学校は？",
            "荒玉駅伝女子の岱明ライバルは？",
            "岱明女子とタイムが近い学校は？",
            "2025荒玉女子で岱明の前後は？",
            "岱明女子の隣接校は？",
            "女子の岱明対抗はどこ？",
            "岱明女子のライバルは長洲？",
        ]
    )


def near_questions() -> list[str]:
    return _dedupe(
        [
            "2025年荒玉で岱明の前後の学校は？",
            "岱明の直前直後の学校は？",
            "荒玉2025岱明の隣の順位はどの学校？",
            "岱明6位の前後は？",
            "岱明7位の前後は？（女子）",
            "2025荒玉岱明の隣接順位",
        ]
    )


def build_entries() -> list[dict]:
    tags = ["aragyoku", "岱明", "ライバル", "競合"]
    return [
        entry(f"{ID_PREFIX}core", core_questions(), CORE_ANSWER, SOURCES, tags),
        entry(f"{ID_PREFIX}men", men_questions(), MEN_ANSWER, SOURCES, tags + ["男子"]),
        entry(f"{ID_PREFIX}women", women_questions(), WOMEN_ANSWER, SOURCES, tags + ["女子"]),
        entry(f"{ID_PREFIX}near-2025", near_questions(), NEAR_ANSWER, SOURCES, tags + ["2025"]),
    ]


def patch_competitor_hint(entries: list[dict]) -> bool:
    for e in entries:
        if e.get("id") != "competitor-hint":
            continue
        e["answer"] = (
            "他校・ライバルは学校名を付けると具体的に答えられます。"
            " 例: 「荒玉駅伝で岱明中とライバルになりそうな学校は？」"
            "「2025年荒玉男子の南関は何位？」「菊水の1500m最速は誰？」。\n"
        )
        sources = list(e.get("sources") or [])
        if "out/analysis/aragyoku_daiming_rivals.md" not in sources:
            sources.append("out/analysis/aragyoku_daiming_rivals.md")
        e["sources"] = sources
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    new_entries = build_entries()
    n_q = sum(len(e["questions"]) for e in new_entries)
    print(f"generated {len(new_entries)} entries / {n_q} questions")
    assert any("荒玉駅伝で岱明中とライバルになりそうな学校は？" in e["questions"] for e in new_entries)
    assert "荒尾三" in new_entries[0]["answer"] and "長洲" in new_entries[0]["answer"]

    if args.dry_run:
        for e in new_entries:
            print(f"- {e['id']}: {len(e['questions'])}qs | {e['questions'][0]}")
            print(" ", e["answer"][:120].replace("\n", " / "))
        return 0

    data = load_faq()
    before = len(data["entries"])
    data["entries"] = [
        e for e in data["entries"] if not str(e.get("id", "")).startswith(ID_PREFIX)
    ]
    removed = before - len(data["entries"])
    added, updated = upsert(data["entries"], new_entries)
    patched = patch_competitor_hint(data["entries"])
    save_faq(data)
    print(
        f"removed stale {removed}; added {added}; updated {updated}; "
        f"competitor-hint patched={patched}; total {len(data['entries'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
