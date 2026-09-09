#!/usr/bin/env python3
"""Notion MCP view/rows の JSON 行を arato_tamana キャッシュ形式に変換・フィルタする。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from arato_tamana_records import RecordRow, filter_rows, load_config, save_cache


def row_from_notion_item(item: dict) -> tuple[RecordRow, str]:
    grade = item.get("学年")
    sb = item.get("SB採用")
    return RecordRow(
        name=item.get("名前", "") or "",
        affiliation=item.get("所属", "") or "",
        grade=int(grade) if grade is not None else None,
        gender=item.get("性別", "") or "",
        distance=item.get("距離", "") or "",
        time_text=item.get("記録", "") or "",
        sb_text=item.get("SB", "") or "",
        sb_adopted=sb == "__YES__" or sb is True,
        date=item.get("日付", "") or "",
        url=item.get("参考", "") or "",
        record_seconds=item.get("記録秒"),
    ), item.get("都道府県", "") or ""


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: build_cache_from_notion_rows.py <input.json> <output.json>", file=sys.stderr)
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    config = load_config()

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "results" in payload:
        items = payload["results"]
    elif isinstance(payload, list):
        items = payload
    else:
        print("Unsupported input format", file=sys.stderr)
        return 1

    raw_rows = [row_from_notion_item(item) for item in items]
    filtered = filter_rows(raw_rows, config)
    save_cache(filtered, output_path)
    print(f"入力: {len(items)}件 → フィルタ後: {len(filtered)}件 → {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
