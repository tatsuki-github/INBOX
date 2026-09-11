"""2024 men: canonical rows are maintained in the image-verified transcript."""
from __future__ import annotations
import json
from pathlib import Path
OCR_RAW = "令和6年度 玉名荒尾中体連駅伝競走大会（男子）総合成績表（原画像照合済み）"
NOTES = ["Result-board transcription with same-year SB database name cross-check"]
TEAMS = json.loads((Path(__file__).resolve().parents[1] / "transcripts" / "2024-男子.json").read_text(encoding="utf-8"))["teams"]
