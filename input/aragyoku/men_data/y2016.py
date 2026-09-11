"""2016 men: canonical rows are maintained in the audited transcript."""
from __future__ import annotations
import json
from pathlib import Path
OCR_RAW = "平成28年度 玉名荒尾中体連駅伝競走大会（男子）総合成績表"
NOTES = ["Ranks and totals verified; unreadable athlete cells are unknown"]
TEAMS = json.loads((Path(__file__).resolve().parents[1] / "transcripts" / "2016-男子.json").read_text(encoding="utf-8"))["teams"]
