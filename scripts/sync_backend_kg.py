#!/usr/bin/env python3
"""Copy out/knowledge-graph.json into backend/data for Vercel packaging."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "out" / "knowledge-graph.json"
DEST = ROOT / "backend" / "data" / "knowledge-graph.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=SRC)
    parser.add_argument("--dest", type=Path, default=DEST)
    parser.add_argument("--check", action="store_true", help="Exit 1 if dest missing or stale")
    args = parser.parse_args()

    if not args.src.exists():
        print(f"missing KG: {args.src}", file=sys.stderr)
        return 1

    if args.check:
        if not args.dest.exists():
            print(f"missing packaged KG: {args.dest}", file=sys.stderr)
            return 1
        src_data = json.loads(args.src.read_text(encoding="utf-8"))
        dest_data = json.loads(args.dest.read_text(encoding="utf-8"))
        if src_data.get("nodes") != dest_data.get("nodes") or src_data.get("edges") != dest_data.get(
            "edges"
        ):
            print("backend/data/knowledge-graph.json is stale; run scripts/sync_backend_kg.py", file=sys.stderr)
            return 1
        print("OK: packaged KG matches out/knowledge-graph.json")
        return 0

    args.dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.src, args.dest)
    print(f"copied {args.src.relative_to(ROOT)} → {args.dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
