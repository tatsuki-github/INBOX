#!/usr/bin/env python3
"""予想通過順位・区間順位の単体テスト。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import generate_nagomi_order_sb_preview as g  # noqa: E402


def _team(no: int, name: str, preds: list[float | None]) -> dict:
    legs = []
    for i, p in enumerate(preds, start=1):
        legs.append(
            {
                "leg": i,
                "name": f"選手{i}",
                "marks": {},
                "pred": p,
                "note": "test",
            }
        )
    return {
        "no": no,
        "team": name,
        "legs": legs,
        "reserves": [],
        "total": sum(p for p in preds if p is not None) if all(p is not None for p in preds) else None,
        "complete": all(p is not None for p in preds),
        "leg_preds": preds,
    }


class PredictedLegRanksTest(unittest.TestCase):
    def test_passing_and_section_ranks(self) -> None:
        a = _team(1, "A", [600.0, 700.0, 650.0, 680.0])  # total 2630
        b = _team(2, "B", [620.0, 640.0, 700.0, 660.0])  # total 2620 — faster overall
        c = _team(3, "C", [580.0, 720.0, 690.0, 700.0])  # total 2690 — fastest 1区
        teams = [a, b, c]
        for t in teams:
            t["total_ref"] = t["total"]
            t["imputed"] = False
        g.attach_predicted_leg_ranks(teams, median=None)

        # 1区 section: C 580, A 600, B 620
        self.assertEqual(c["legs"][0]["pred_sec_rank"], 1)
        self.assertEqual(a["legs"][0]["pred_sec_rank"], 2)
        self.assertEqual(b["legs"][0]["pred_sec_rank"], 3)
        # 1区 cum = section
        self.assertEqual(c["legs"][0]["pred_cum_rank"], 1)
        # 2区 cum: C 1300, A 1300, B 1260 → B first
        self.assertEqual(b["legs"][1]["pred_cum_rank"], 1)
        self.assertEqual(b["legs"][1]["pred_sec_rank"], 1)  # 640 fastest 2区

    def test_fmt_leg_cell(self) -> None:
        det = {
            "pred": 400.0,
            "pred_used": 400.0,
            "pred_cum": 900.0,
            "pred_sec_rank": 2,
            "pred_cum_rank": 1,
            "pred_imputed_leg": False,
        }
        self.assertEqual(g.fmt_leg_pred_cell(det), "(1)15:00.0 / (2)6:40.0")

    def test_imputed_leg_parenthesized(self) -> None:
        det = {
            "pred": None,
            "pred_used": 466.1,
            "pred_cum": 900.0,
            "pred_sec_rank": 3,
            "pred_cum_rank": 2,
            "pred_imputed_leg": True,
        }
        cell = g.fmt_leg_pred_cell(det)
        self.assertIn("(3)(7:46.1)", cell)
        self.assertIn("(2)15:00.0", cell)

    def test_complete_suffix_does_not_overwrite_ref(self) -> None:
        a = _team(1, "A", [600.0, 600.0, 600.0, 600.0])
        b = _team(2, "B", [610.0, 610.0, 610.0, 610.0])
        c = _team(3, "C", [None, 500.0, 500.0, 500.0])  # imputed for ref only
        for t in (a, b):
            t["total_ref"] = t["total"]
        c["total_ref"] = 500 * 3 + 600  # with median fill pretend
        c["legs"][0]["name"] = "欠測"
        ref = [a, b, c]
        g.attach_predicted_leg_ranks(ref, median=600.0, field_suffix="")
        g.attach_predicted_leg_ranks([a, b], None, complete_only=True, field_suffix="_full")
        self.assertEqual(a["legs"][0]["pred_sec_rank_full"], 1)  # among 2 complete
        self.assertEqual(b["legs"][0]["pred_sec_rank"], 3)  # A/C tie at 600 with median
        self.assertEqual(b["legs"][0]["pred_sec_rank_full"], 2)
        self.assertIn("pred_sec_rank", a["legs"][0])
        self.assertIn("pred_sec_rank_full", a["legs"][0])
        self.assertNotEqual(
            a["legs"][0].get("pred_sec_rank"),
            None,
        )


if __name__ == "__main__":
    unittest.main()
