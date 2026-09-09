#!/usr/bin/env python3
"""Notion「2026年度中学生記録」から荒尾・玉名地区の全記録 PDF を生成する。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from arato_tamana_pdf import build_pdf
from arato_tamana_records import (
    DEFAULT_CONFIG,
    fetch_filtered_records,
    group_by_affiliation,
    load_cache,
    load_config,
    save_cache,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="荒尾・玉名地区の中学生記録を所属別 PDF に出力します。"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="設定 YAML のパス",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="出力 PDF パス（省略時は config の output.pdf）",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=None,
        help="Notion 取得結果を JSON に保存するパス",
    )
    parser.add_argument(
        "--from-cache",
        type=Path,
        default=None,
        help="キャッシュ JSON から PDF を再生成する",
    )
    parser.add_argument(
        "--font",
        type=Path,
        default=None,
        help="日本語フォント（.otf）のパス",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)

    output_path = args.output or ROOT / config["output"]["pdf"]
    cache_path = args.cache or ROOT / config["output"]["cache"]
    title = config.get("title", "荒尾玉名中学生 記録一覧")

    if args.from_cache:
        records = load_cache(args.from_cache)
        print(f"キャッシュ読込: {args.from_cache} ({len(records)}件)")
    else:
        token = os.environ.get("NOTION_TOKEN", "").strip()
        if not token:
            print(
                "エラー: 環境変数 NOTION_TOKEN が未設定です。\n"
                "Notion Integration Token を設定するか、--from-cache を使用してください。",
                file=sys.stderr,
            )
            return 1
        records = fetch_filtered_records(config, token)
        print(f"Notion 取得: {len(records)}件")
        if args.cache is not None or cache_path:
            save_cache(records, cache_path)
            print(f"キャッシュ保存: {cache_path}")

    sections = group_by_affiliation(records)
    pdf_path = build_pdf(sections, output_path, title, font_path=args.font)
    print(f"PDF 生成: {pdf_path} ({len(sections)}所属 / {len(records)}件)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
