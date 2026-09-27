#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""荒玉 SB 予想の単体テスト（鮮度・距離・シード）。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_aragyoku_ekiden_sb_preview as aragyoku  # noqa: E402
import generate_nagomi_order_sb_preview as nagomi  # noqa: E402


class TestFreshness(unittest.TestCase):
    def test_old_mark_excluded(self) -> None:
        self.assertFalse(
            nagomi.date_within_freshness("2025-01-01", "2026-09-27", 152)
        )

    def test_recent_mark_included(self) -> None:
        self.assertTrue(
            nagomi.date_within_freshness("2026-06-01", "2026-09-27", 152)
        )

    def test_missing_date_excluded_when_freshness(self) -> None:
        self.assertFalse(nagomi.date_within_freshness("", "2026-09-27", 152))

    def test_missing_date_allowed_without_freshness(self) -> None:
        self.assertTrue(
            nagomi.date_within_freshness("", "2026-09-27", None, allow_missing_date=True)
        )


class TestDistances(unittest.TestCase):
    def test_women_five_legs(self) -> None:
        self.assertEqual(len(aragyoku.WOMEN_DISTANCES_KM), 5)
        self.assertEqual(aragyoku.WOMEN_DISTANCES_KM[0], 3.0)
        self.assertEqual(aragyoku.WOMEN_DISTANCES_KM[1], 1.855)

    def test_men_six_legs(self) -> None:
        self.assertEqual(len(aragyoku.MEN_DISTANCES_KM), 6)
        self.assertEqual(aragyoku.MEN_DISTANCES_KM[1], 2.855)


class TestTaimeiSeed(unittest.TestCase):
    def test_women_all_five(self) -> None:
        self.assertEqual(len(aragyoku.TAIMEI_KNOWN_LEGS["女子"]), 5)
        self.assertEqual(aragyoku.TAIMEI_KNOWN_LEGS["女子"][2], "山﨑 莉奈")
        self.assertEqual(aragyoku.TAIMEI_KNOWN_LEGS["女子"][5], "高田 麻由")

    def test_men_four_known(self) -> None:
        self.assertEqual(len(aragyoku.TAIMEI_KNOWN_LEGS["男子"]), 4)
        self.assertNotIn(5, aragyoku.TAIMEI_KNOWN_LEGS["男子"])
        self.assertNotIn(6, aragyoku.TAIMEI_KNOWN_LEGS["男子"])

    def test_build_leaves_men_5_6_empty(self) -> None:
        # 空の SB index でも未決が残ること
        team = aragyoku.build_taimei_team("男子", {})
        self.assertIsNone(team["legs"][4])
        self.assertIsNone(team["legs"][5])
        self.assertEqual(team["details"][4]["note"], "オーダー未決")
        self.assertFalse(team["complete"])


class TestPredict(unittest.TestCase):
    def test_women_1500_scales(self) -> None:
        mark = nagomi.Mark(seconds=300.0, text="5:00.00", date="2026-08-01", source="test")
        ath = nagomi.AthleteSB(name="テスト", marks={"1500m": mark})
        pred, _, note = aragyoku.predict_leg("テスト", "女子", 2.0, {"テスト": ath})
        # 300*(2/1.5)+15 = 415 → ×(2/2)=415
        self.assertIsNotNone(pred)
        self.assertAlmostEqual(pred or 0, 415.0, places=1)
        self.assertIn("1500m", note)


if __name__ == "__main__":
    unittest.main()
