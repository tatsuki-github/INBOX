#!/usr/bin/env python3
"""Save Google Drive OCR text to ocr_raw markdown files."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = json.loads((ROOT / "sources/men_result_board_sources.json").read_text(encoding="utf-8"))
OCR_DIR = ROOT / "ocr_raw"

# OCR text captured via Google Drive read_file_content MCP (2026-09-10)
OCR_BY_YEAR: dict[str, str] = {}


def save_year(year: str, ocr_text: str) -> Path:
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    src = SOURCES[year]
    path = OCR_DIR / f"{year}-男子.md"
    body = f"""# 荒玉中体連駅伝 {year} 男子 — OCR raw

> Source: Google Drive `{src['id']}` ({src['title']})
> Captured via Google Drive MCP `read_file_content`

## Raw OCR

```
{ocr_text.strip()}
```
"""
    path.write_text(body, encoding="utf-8")
    return path


if __name__ == "__main__":
    for year, text in OCR_BY_YEAR.items():
        print(save_year(year, text))
