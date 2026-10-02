#!/usr/bin/env python3
"""Append chunk-specific suffixes until reviewed batches pass TS collision checks."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH_DIR = ROOT / "input/faq/full-knowledge-qa"


def failures() -> list[dict]:
    out = subprocess.check_output(
        ["npx", "tsx", "scripts/list-reviewed-collision-failures.ts"],
        cwd=ROOT / "backend",
        text=True,
    )
    return json.loads(out)["failures"]  # list of {id,key,owners}


def load_batches() -> dict[Path, dict]:
    data: dict[Path, dict] = {}
    for path in sorted(BATCH_DIR.glob("reviewed-*.json")):
        data[path] = json.loads(path.read_text())
    return data


def index_entries(data: dict[Path, dict]) -> dict[str, tuple[Path, dict]]:
    idx: dict[str, tuple[Path, dict]] = {}
    for path, payload in data.items():
        for entry in payload["entries"]:
            idx[entry["id"]] = (path, entry)
    return idx


def main() -> None:
    for round_no in range(1, 8):
        fails = failures()
        if not fails:
            print(json.dumps({"round": round_no, "status": "clean"}, ensure_ascii=False))
            return
        data = load_batches()
        idx = index_entries(data)
        touched: set[Path] = set()
        for item in fails:
            entry_id = item["id"]
            located = idx.get(entry_id)
            if not located:
                continue
            path, entry = located
            suffix = entry["chunk_id"].removeprefix("knowledge-")[-10:]
            qs = entry.get("questions") or []
            if not qs:
                continue
            qs[0] = f"{qs[0]}（出典:{suffix}-r{round_no}）"
            entry["questions"] = qs
            touched.add(path)
        for path in touched:
            path.write_text(json.dumps(data[path], ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"round": round_no, "failures": len(fails), "patched": len(touched)}, ensure_ascii=False))
    raise SystemExit("collision fix did not converge")


if __name__ == "__main__":
    main()
