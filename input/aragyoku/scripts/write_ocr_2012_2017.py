#!/usr/bin/env python3
"""Write ocr_raw markdown for 2012-2017 from Google Drive MCP captures."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = json.loads((ROOT / "sources/men_result_board_sources.json").read_text(encoding="utf-8"))
OCR_DIR = ROOT / "ocr_raw"

# Full text from Google Drive MCP read_file_content (2026-09-10)
DRIVE_OCR: dict[str, str] = {
    "2012": """平成24年 玉名荒尾中体連駅伝競走大会(男子) 総合成績表
source: Google Drive 15dRgSdWM6dOBkX-batIvOEignRDJ9vTP

玉名 1:03:47 | 荒尾海陽 1:04:32 | 玉南 1:05:53 | 荒尾三 1:06:11
岱明 1:06:34 | 菊水 1:06:41 | 有明 1:06:47 | 腹栄 1:06:59
荒尾四 1:07:11 | 三加和 1:07:29 | 玉東 1:07:34 | 天水 1:07:35
玉高附属 1:07:54 | 長洲 1:08:54 | 南関 1:09:24 | 荒尾 1:09:33""",
    "2013": """平成25年度 玉名荒尾中体連駅伝競走大会(男子) 総合成績表
source: Google Drive 1SxCLZVuz-FeLKzsjsMCfPZhTj4GAtFuR

玉名 1:03:03 | 荒尾海陽 1:03:21 | 菊水 1:03:37 | 荒尾三 1:04:50
荒尾四 1:05:23 | 玉高附属 1:06:52 | 岱明 1:08:00 | 長洲 1:08:28
三加和 1:08:38 | 天水 1:08:56 | 玉南 1:09:01 | 南関 1:09:50
玉陵 1:11:19 | 腹栄 1:12:20 | 玉東 1:12:26 | 有明 1:13:26""",
    "2014": """平成26年度 玉名荒尾中体連駅伝競走大会(男子) 総合成績表
source: Google Drive 1PsRvWmJMYr3BT6BnRkxzsFvJqS2Cc5du

菊水 1:03:38 | 玉名 1:03:48 | 荒尾三 1:04:25 | 荒尾海陽 1:04:44
玉東 1:06:02 | 三加和 1:06:42 | 南関 1:06:43 | 長洲 1:06:58
岱明 1:07:04 | 玉高附属 1:08:14 | 荒尾四 1:08:22 | 玉南 1:09:37
有明 1:09:51 | 玉陵 1:09:57 | 天水 1:10:51 | 腹栄 1:11:04""",
    "2015": """平成27年度 玉名荒尾中体連駅伝競走大会(男子) 総合成績表
source: Google Drive 1cs3-zzGVkVcqWENzjBRK1VUSQ84KV8I2

玉名 1:03:47 | 荒尾海陽 1:04:16 | 南関 1:05:29 | 荒尾三 1:06:08
荒尾四 1:06:33 | 岱明 1:07:06 | 玉皇 1:07:41 | 玉高附属 1:08:19
天水 1:08:31 | 有明 1:09:52 | 玉陵 1:10:13 | 三加和 1:13:08""",
    "2016": """平成28年度 玉名荒尾中体連駅伝競走大会(男子) 総合成績表
source: Google Drive 1yq9bXt48tgdXfAO7GcrGmNGXAGXL1n9G

菊水 1:02:53 | 玉名 1:03:05 | 南関 1:03:29 | 玉東 1:04:19
玉皇 1:04:43 | 岱明 1:04:55 | 荒尾四 1:06:25 | 玉南 1:07:00
玉高附属 1:07:55 | 天水 1:08:50 | 玉陵 1:09:19 | 有明 1:10:21
長洲 1:11:25 | 三加和 1:11:25""",
    "2017": """平成29年 玉名荒尾中体連駅伝競走大会(男子) 総合成績表
source: Google Drive 166D0h_QMSc8__Bp6sti5Y4BpUbRq7jj2

玉名 1:03:07 | 菊水 1:03:17 | 南関 1:05:29 | 荒尾四 1:06:01
玉東 1:06:23 | 荒尾三 1:06:31 | 岱明 1:06:47 | 腹栄 1:07:20
荒尾海陽 1:08:06 | 長洲 1:08:52 | 玉南 1:09:06 | 玉陵 1:09:51
天水 1:10:12 | 玉高附属 1:10:35 | 有明 1:10:41 | 三加和 1:13:06""",
}


def main() -> None:
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    for year, text in DRIVE_OCR.items():
        src = SOURCES[year]
        path = OCR_DIR / f"{year}-男子.md"
        body = (
            f"# 荒玉中体連駅伝 {year} 男子 — OCR raw\n\n"
            f"> Google Drive `{src['id']}` ({src['title']})\n"
            f"> Captured via Google Drive MCP `read_file_content`\n\n"
            f"## Board summary\n\n{text.strip()}\n"
        )
        path.write_text(body, encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
