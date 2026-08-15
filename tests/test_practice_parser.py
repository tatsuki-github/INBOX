from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from practice_parser import parse_event, parse_html_comment, parse_practice_field  # noqa: E402
from practice_renderer import render_description  # noqa: E402


class PracticeParserTests(unittest.TestCase):
    def test_parse_absentees_from_description(self) -> None:
        ev = {
            "title": "いだてん岱明練習",
            "tags": ["いだてん岱明練習"],
            "description": "動きづくり\n\n欠席者 松野、塚原\n\nジョグ 3.36km (6周) k/4:46",
        }
        result = parse_event(ev)
        self.assertEqual(result.practice.get("absentees"), ["松野", "塚原"])
        self.assertNotIn("欠席者 松野、塚原", result.note_lines)

    def test_parse_absentees_none(self) -> None:
        ev = {
            "title": "いだてん岱明練習",
            "tags": ["いだてん岱明練習"],
            "description": "動きづくり\n\n欠席者なし",
        }
        result = parse_event(ev)
        self.assertEqual(result.practice.get("absentees"), [])

    def test_parse_practice_field_with_absentees(self) -> None:
        raw = {
            "warmup": "動きづくり",
            "absentees": ["松岡"],
            "items": [{"type": "interval", "distance_m": 600, "reps": 2, "intensity": "1500mRP"}],
        }
        practice = parse_practice_field(raw)
        self.assertIsNotNone(practice)
        assert practice is not None
        self.assertEqual(practice["absentees"], ["松岡"])

    def test_parse_practice_field(self) -> None:
        raw = {
            "warmup": "動きづくり",
            "items": [{"type": "interval", "distance_m": 600, "reps": 2, "intensity": "1500mRP"}],
        }
        practice = parse_practice_field(raw)
        self.assertIsNotNone(practice)
        assert practice is not None
        self.assertEqual(practice["warmup"], "動きづくり")
        self.assertEqual(practice["items"][0]["distance_m"], 600)

    def test_parse_html_comment(self) -> None:
        desc = """<!-- practice-menu:v1
warmup: 動きづくり
items:
  - type: interval
    distance_m: 300
    reps: 5
    intensity: RP
-->

欠席者なし"""
        practice = parse_html_comment(desc)
        self.assertIsNotNone(practice)
        assert practice is not None
        self.assertEqual(len(practice["items"]), 1)

    def test_parse_kpace_description(self) -> None:
        ev = {
            "title": "岱明夕練",
            "tags": ["いだてん岱明練習"],
            "description": "動きづくり\n\nジョグ 男子 3.36km (6周) k/4:46\n900m（300m57秒組） 900m k/3:10",
        }
        result = parse_event(ev)
        self.assertGreater(len(result.items), 0)
        self.assertIn(result.confidence, {"full", "partial"})

    def test_parse_rp_interval(self) -> None:
        ev = {
            "title": "岱明夕練",
            "tags": ["いだてん岱明練習"],
            "description": "600m×2（1500mRP、r=8分）",
        }
        result = parse_event(ev)
        self.assertTrue(result.items or result.skipped)


class PracticeRendererTests(unittest.TestCase):
    def test_render_absentees(self) -> None:
        practice = {
            "warmup": "動きづくり",
            "absentees": ["松野", "塚原"],
            "items": [
                {"type": "jog", "group": "男子", "distance_km": 3.36, "laps": 6, "pace": "k/4:46"},
            ],
        }
        desc = render_description(practice)
        self.assertIn("欠席者 松野、塚原", desc)

    def test_render_roundtrip(self) -> None:
        practice = {
            "warmup": "動きづくり",
            "items": [
                {"type": "jog", "group": "男子", "distance_km": 3.36, "laps": 6, "pace": "k/4:46"},
            ],
        }
        desc = render_description(practice)
        self.assertIn("動きづくり", desc)
        self.assertIn("k/4:46", desc)


if __name__ == "__main__":
    unittest.main()
