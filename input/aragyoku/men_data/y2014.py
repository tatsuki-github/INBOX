"""2014 men: canonical rows are maintained in the image-verified transcript."""

from __future__ import annotations

import json
from pathlib import Path

OCR_RAW = """平成26年度 玉名荒尾中体連駅伝競走大会（男子）総合成績表
source: Google Drive 1PsRvWmJMYr3BT6BnRkxzsFvJqS2Cc5du (image-20.jpg)"""

NOTES = [
    "Result-board row-by-row transcription; unreadable names are unknown",
    "board canonical; Notion rank disagrees with the result board",
]


def _load_teams() -> list[dict]:
    path = Path(__file__).resolve().parents[1] / "transcripts" / "2014-男子.json"
    return json.loads(path.read_text(encoding="utf-8"))["teams"]


TEAMS = _load_teams()
