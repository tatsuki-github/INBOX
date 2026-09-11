"""2015 men: canonical rows are maintained in the image-verified transcript."""

from __future__ import annotations

import json
from pathlib import Path

OCR_RAW = """平成27年度 玉名荒尾中体連駅伝競走大会（男子）総合成績表
source: Google Drive 1cs3-zzGVkVcqWENzjBRK1VUSQ84KV8I2 (image-28.jpg)"""

NOTES = ["Result-board row-by-row transcription; unreadable names are unknown"]


def _load_teams() -> list[dict]:
    path = Path(__file__).resolve().parents[1] / "transcripts" / "2015-男子.json"
    return json.loads(path.read_text(encoding="utf-8"))["teams"]


TEAMS = _load_teams()
