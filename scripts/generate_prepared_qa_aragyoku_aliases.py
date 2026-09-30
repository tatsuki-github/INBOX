#!/usr/bin/env python3
"""Generate prepared FAQ: 荒玉駅伝の呼び方・表記揺れ（ADR 059）.

正本: out/analysis/aragyoku-overview.md / backend aragyokuAliases.ts

Usage:
  python3 scripts/generate_prepared_qa_aragyoku_aliases.py
  python3 scripts/generate_prepared_qa_aragyoku_aliases.py --dry-run
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
ID_PREFIX = "aragyoku-alias-"
SOURCES = [
    "out/analysis/aragyoku-overview.md",
    "backend/src/domain/aragyokuAliases.ts",
    "input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝",
]

NAME_ANSWER = (
    "同じ大会です。玉名・荒尾地区の中体連駅伝で、通称は荒玉駅伝 / 荒玉中体連駅伝。"
    " 正式寄りに玉名荒尾中体連駅伝、口語では郡市駅伝と呼ぶこともあります。"
    " 男子6区間・女子5区間。このチャットではどれで聞いても荒玉駅伝として答えます。"
)

WHAT_EXTRA_QUESTIONS = [
    "荒玉駅伝って何？",
    "荒玉中体連駅伝って何？",
    "玉名荒尾中体連駅伝って何？",
    "玉名・荒尾中体連駅伝って何？",
    "郡市駅伝って何？",
    "荒玉郡市駅伝って何？",
    "中体連駅伝って何？（荒玉）",
    "荒玉って何？（駅伝）",
]


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


def patch_aragyoku_what(entries: list[dict]) -> bool:
    for e in entries:
        if e.get("id") != "aragyoku-what":
            continue
        qs = list(e.get("questions") or [])
        for q in WHAT_EXTRA_QUESTIONS:
            if q not in qs:
                qs.append(q)
        e["questions"] = qs
        ans = str(e.get("answer") or "")
        if "郡市駅伝" not in ans:
            e["answer"] = (
                ans.rstrip()
                + " 口語では郡市駅伝、正式寄りでは玉名荒尾中体連駅伝とも呼ばれます。\n"
            )
        sources = list(e.get("sources") or [])
        if "backend/src/domain/aragyokuAliases.ts" not in sources:
            sources.append("backend/src/domain/aragyokuAliases.ts")
        e["sources"] = sources
        return True
    return False


def build_entries() -> list[dict]:
    tags = ["aragyoku", "alias", "呼び方"]
    qs = [
        "荒玉駅伝と荒玉中体連駅伝は同じ？",
        "荒玉と郡市駅伝は同じ？",
        "郡市駅伝は荒玉駅伝のこと？",
        "玉名荒尾中体連駅伝は荒玉？",
        "荒玉中体連と荒玉駅伝は同じ大会？",
        "荒玉の別名は？",
        "荒玉駅伝の呼び方は？",
        "荒玉駅伝の正式名称は？",
        "郡市駅伝って荒玉中体連？",
        "中体連駅伝って荒玉のこと？",
        "荒玉郡市駅伝と荒玉駅伝は同じ？",
        "玉名・荒尾中体連駅伝の通称は？",
    ]
    return [
        entry(f"{ID_PREFIX}same", qs, NAME_ANSWER, SOURCES, tags),
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    new_entries = build_entries()
    print(f"generated {len(new_entries)} entries / {sum(len(e['questions']) for e in new_entries)} questions")

    if args.dry_run:
        for e in new_entries:
            print("-", e["id"], e["questions"][:3])
        return 0

    data = load_faq()
    before = len(data["entries"])
    data["entries"] = [
        e for e in data["entries"] if not str(e.get("id", "")).startswith(ID_PREFIX)
    ]
    removed = before - len(data["entries"])
    added, updated = upsert(data["entries"], new_entries)
    patched = patch_aragyoku_what(data["entries"])
    save_faq(data)
    print(
        f"removed stale {removed}; added {added}; updated {updated}; "
        f"aragyoku-what patched={patched}; total {len(data['entries'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
