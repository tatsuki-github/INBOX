#!/usr/bin/env python3
"""Strip non-link bibliographic references from ALL prepared-qa answers.

Policy (user):
  - If it is not a clickable link, do not cite references in the answer body.
  - Keep https?:// URLs (and labels immediately before them like 資料: / 大会結果:).

Usage:
  python3 scripts/strip_prepared_qa_nonlink_refs.py --dry-run
  python3 scripts/strip_prepared_qa_nonlink_refs.py
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
REPORT = ROOT / "backend" / "data" / "eval-gaps" / "strip-nonlink-refs.jsonl"

URL_RE = re.compile(r"https?://[^\s）)\]]+")

# Protect URLs while editing
_URL_TOKEN = "<<<URL{}>>>"


def protect_urls(text: str) -> tuple[str, list[str]]:
    urls: list[str] = []

    def repl(m: re.Match[str]) -> str:
        urls.append(m.group(0).rstrip("。、,"))
        return _URL_TOKEN.format(len(urls) - 1)

    return URL_RE.sub(repl, text), urls


def restore_urls(text: str, urls: list[str]) -> str:
    out = text
    for i, u in enumerate(urls):
        out = out.replace(_URL_TOKEN.format(i), u)
    return out


def strip_nonlink_refs(answer: str) -> str:
    text, urls = protect_urls(answer)

    # Citation prefixes like 「荒玉駅伝2026徹底対策（p.27）より:」
    text = re.sub(
        r"^[^。\n]{0,40}徹底対策[^。\n]{0,40}より\s*[:：]\s*",
        "",
        text,
        flags=re.M,
    )
    text = re.sub(r"^[^。\n]{0,40}（p\.\d+）より\s*[:：]\s*", "", text, flags=re.M)

    # Parenthetical citations (guide / ADR / page) — not school-name parens
    text = re.sub(
        r"（[^）]*(?:徹底対策|ガイド\s*\d|ADR\s*\d|p\.\d+)[^）]*）",
        "",
        text,
    )

    # Bare bibliographic pointers only (do not wipe content that explains 徹底対策N章)
    text = re.sub(r"詳しくは[^。\n]*(?:ガイド|徹底対策|p\.\d+)[^。\n]*。", "", text)
    text = re.sub(
        r"徹底対策ガイドでは[^。\n]*。",
        "",
        text,
    )
    text = re.sub(
        r"徹底対策ガイド\s*[\d.]+\s*[。]?",
        "",
        text,
    )

    # 要項 / 再確認 meta references (no link) — avoid eating prior sentences
    text = re.sub(r"（要項で再確認）", "", text)
    text = re.sub(
        r"(?:出場枠は|ただし出場枠は)[^。\n]*(?:大会要項|要項)[^。\n]*。",
        "",
        text,
    )
    text = re.sub(
        r"必ず要項を確認してください。",
        "",
        text,
    )
    text = re.sub(
        r"正式な出場枠は年度ごとの大会要項が正です。",
        "",
        text,
    )
    text = re.sub(
        r"迷ったら要項[^。\n]*。",
        "",
        text,
    )
    text = re.sub(
        r"運用上もその前提で目標を置きますが、\s*",
        "",
        text,
    )

    # 「詳細資料: 大会フォルダ: URL」 → keep URL (before generic 詳細/資料 strip)
    text = re.sub(r"詳細資料\s*[:：]\s*", "", text)
    text = re.sub(r"大会フォルダ\s*[:：]\s*(<<<URL\d+>>>)", r"資料: \1", text)

    # 出典/詳細/資料/正本 labels without URL token (and without URL later in segment)
    text = re.sub(
        r"(?:出典|詳細テキスト|索引|正本)\s*[:：]\s*(?!<<<URL)(?![^\n。]*<<<URL)[^\n。]*",
        "",
        text,
    )
    # 「詳細:」 / 「資料:」 only keep when URL token follows (avoid matching inside 詳細資料)
    text = re.sub(
        r"(?<![一-龥])(?:詳細|資料)\s*[:：]\s*(?!<<<URL)(?![^\n。]*<<<URL)[^\n。]*",
        "",
        text,
    )

    # Repo / pdf path crumbs that aren't URLs
    text = re.sub(r"`?outputs/[^`\s。]+`?", "", text)
    text = re.sub(r"`?(?:input|out|docs|scripts)/[^`\s。]+`?", "", text)
    text = re.sub(r"\b[\w./\-一-龥]+\.(?:md|yaml|yml|json|csv|txt|pdf)\b", "", text)

    # "を見てください / を参照" dangling sentences without URL
    text = re.sub(r"[^。\n]*(?:を見てください|を参照(?:してください)?)。", "", text)

    # Cleanup whitespace / empty parens / double periods
    text = re.sub(r"[（(]\s*[）)]", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"。{2,}", "。", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = text.strip()

    text = restore_urls(text, urls)
    if text and not text.endswith(("。", "…", "!", "！", "?", "？")) and "http" not in text[-48:]:
        text += "。"
    return text + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = list(data.get("entries") or [])
    changed = 0
    rows: list[dict] = []
    for e in entries:
        before = e.get("answer") or ""
        after = strip_nonlink_refs(before)
        if after != before:
            changed += 1
            rows.append(
                {
                    "id": e.get("id"),
                    "before_len": len(before),
                    "after_len": len(after),
                    "had_url": bool(URL_RE.search(before)),
                }
            )
            e["answer"] = after

    print(f"entries={len(entries)} changed={changed}")
    # sample
    for eid in (
        "aragyoku-pref-top2-core",
        "aragyoku-pref-top2-confirm",
        "aragyoku-pref-top2-line",
        "gap1000-pref-top2-short",
        "junior-2026-nankan-tamafz-detail",
        "guide-2026-p27",
        "sb-2026-松野凛空",
    ):
        e = next((x for x in entries if x["id"] == eid), None)
        if e:
            print("---", eid)
            print(e["answer"][:240].replace("\n", " | "))

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {REPORT.relative_to(ROOT)}")

    if args.dry_run:
        return 0

    data["entries"] = entries
    data["total"] = len(entries)
    note = data.get("note") or ""
    if "strip-nonlink-refs" not in note:
        data["note"] = (
            note.rstrip()
            + "\nstrip-nonlink-refs: リンクでない参考文献・要項/ガイド引用を回答本文から除去。URLは残す。\n"
        )
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
