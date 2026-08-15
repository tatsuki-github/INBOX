from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from export_practice import (  # noqa: E402
    practice_records_from_events,
    write_practice_items_csv,
    write_practice_json,
)


class ExportPracticeTests(unittest.TestCase):
    def test_export_json_and_csv(self) -> None:
        events = [
            {
                "title": "岱明夕練",
                "date": "2026-08-14",
                "tags": ["いだてん岱明練習"],
                "practice": {
                    "warmup": "動きづくり",
                    "items": [{"type": "interval", "distance_m": 900, "pace": "k/3:10"}],
                },
            }
        ]
        records = practice_records_from_events(events, 2026)
        self.assertEqual(len(records), 1)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            json_path = tmp / "practice.json"
            csv_path = tmp / "practice_items.csv"
            write_practice_json(json_path, records)
            write_practice_items_csv(csv_path, records)
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data[0]["title"], "岱明夕練")
            csv_text = csv_path.read_text(encoding="utf-8")
            self.assertIn("distance_m", csv_text)
            self.assertIn("900", csv_text)


if __name__ == "__main__":
    unittest.main()
