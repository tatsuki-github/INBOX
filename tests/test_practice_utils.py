from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from practice_utils import extract_absentees_from_text, format_absentees, parse_absentees_line  # noqa: E402


class PracticeUtilsTests(unittest.TestCase):
    def test_parse_absentees_line(self) -> None:
        self.assertEqual(parse_absentees_line("欠席者 松岡"), ["松岡"])
        self.assertEqual(parse_absentees_line("欠席者 田上、角田、高田、松本"), ["田上", "角田", "高田", "松本"])
        self.assertEqual(parse_absentees_line("欠席者なし"), [])
        self.assertIsNone(parse_absentees_line("欠席者多めの中、動きづくりは"))

    def test_format_absentees(self) -> None:
        self.assertEqual(format_absentees(["松野", "塚原"]), "欠席者 松野、塚原")
        self.assertEqual(format_absentees([]), "欠席者なし")

    def test_extract_absentees_from_text(self) -> None:
        text = "動きづくり\n\n欠席者 松野、塚原\nコメント"
        self.assertEqual(extract_absentees_from_text(text), ["松野", "塚原"])


if __name__ == "__main__":
    unittest.main()
