"""2019 men: low-resolution original; no interpolated values are canonical."""

from __future__ import annotations

import json
from pathlib import Path

OCR_RAW = """令和元年度 玉名荒尾中体連駅伝競走大会（男子）総合成績表
source: Google Drive 13Mr2rUaOW3hCoYf5FPiA_zHMssTswZ2K (image-23.jpg, 750x910)"""

NOTES = [
    "Unreadable fields are unknown/null because no higher-resolution original exists.",
    "Prior interpolation is preserved only in reconciliations/2019-men-legacy-interpolated.json.",
]


def _load_teams() -> list[dict]:
    path = Path(__file__).resolve().parents[1] / "transcripts" / "2019-男子.json"
    return json.loads(path.read_text(encoding="utf-8"))["teams"]


TEAMS = _load_teams()
