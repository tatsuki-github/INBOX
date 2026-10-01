#!/usr/bin/env python3
"""Sync prepared FAQ YAML into backend JSON and idaten-corpus.

Usage:
  python3 scripts/sync_prepared_qa.py
  python3 scripts/sync_prepared_qa.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
OUT_JSON = ROOT / "backend" / "data" / "prepared-qa.json"
CORPUS_DIR = ROOT / "input" / "idaten-corpus" / "faq"
CORPUS_YAML = CORPUS_DIR / "prepared-qa.v1.yaml"


def _load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("PyYAML is required: pip install pyyaml") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"invalid YAML root in {path}")
    return data


def validate(data: dict) -> list[dict]:
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise SystemExit("entries must be a non-empty list")
    ids: set[str] = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise SystemExit(f"entry[{i}] must be object")
        eid = entry.get("id")
        questions = entry.get("questions")
        answer = entry.get("answer")
        sources = entry.get("sources")
        if not isinstance(eid, str) or not eid.strip():
            raise SystemExit(f"entry[{i}].id required")
        if eid in ids:
            raise SystemExit(f"duplicate id: {eid}")
        ids.add(eid)
        if not isinstance(questions, list) or not questions or not all(isinstance(q, str) and q.strip() for q in questions):
            raise SystemExit(f"entry {eid}: questions must be non-empty string list")
        if not isinstance(answer, str) or not answer.strip():
            raise SystemExit(f"entry {eid}: answer required")
        if not isinstance(sources, list) or not sources or not all(isinstance(s, str) for s in sources):
            raise SystemExit(f"entry {eid}: sources required")
    expected = data.get("total")
    if expected is not None and int(expected) != len(entries):
        raise SystemExit(f"total={expected} but entries={len(entries)}")
    return entries


def build_payload(data: dict, entries: list[dict]) -> dict:
    return {
        "version": int(data.get("version") or 1),
        "total": len(entries),
        "source": "input/faq/prepared-qa.v1.yaml",
        "note": data.get("note")
        or "想定質問への定型回答。matchPreparedAnswer がヒットしたら本文をほぼそのまま返す。",
        "entries": [
            {
                "id": e["id"],
                "questions": list(e["questions"]),
                "answer": str(e["answer"]).strip(),
                "sources": list(e["sources"]),
                "tags": list(e.get("tags") or []),
            }
            for e in entries
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not SRC.exists():
        raise SystemExit(f"missing {SRC}")
    data = _load_yaml(SRC)
    entries = validate(data)
    payload = build_payload(data, entries)
    # Keep this large generated catalog within API upload limits.
    text = json.dumps(payload, ensure_ascii=False) + "\n"

    if args.check:
        if not OUT_JSON.exists():
            print(f"MISSING {OUT_JSON}", file=sys.stderr)
            return 1
        current = OUT_JSON.read_text(encoding="utf-8")
        if current != text:
            print("OUT OF DATE: backend/data/prepared-qa.json != input/faq/prepared-qa.v1.yaml", file=sys.stderr)
            return 1
        if not CORPUS_YAML.exists() or CORPUS_YAML.read_text(encoding="utf-8") != SRC.read_text(encoding="utf-8"):
            print("OUT OF DATE: corpus faq copy mismatch", file=sys.stderr)
            return 1
        print(f"OK: prepared-qa {len(entries)} entries in sync")
        return 0

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(text, encoding="utf-8")
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    CORPUS_YAML.write_text(SRC.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"wrote {OUT_JSON.relative_to(ROOT)} ({len(entries)} entries)")
    print(f"wrote {CORPUS_YAML.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
