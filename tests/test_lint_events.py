from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lint_events import validate_actuals_mode  # noqa: E402
from practice_schedule_meta import actuals_mode_from, is_actuals_mode_date  # noqa: E402


class ActualsModeTests(unittest.TestCase):
    def test_cutoff_defaults(self) -> None:
        self.assertEqual(actuals_mode_from({}), "2026-09-19")
        self.assertTrue(is_actuals_mode_date("2026-09-19", cutoff="2026-09-19"))
        self.assertFalse(is_actuals_mode_date("2026-09-18", cutoff="2026-09-19"))

    def test_rejects_scheduled_shell_after_cutoff(self) -> None:
        errs = validate_actuals_mode(
            {
                "title": "いだてん岱明夕練",
                "date": "2026-09-20",
                "status": "scheduled",
            },
            "2026-09-19",
        )
        self.assertEqual(len(errs), 1)

    def test_allows_done_actual_after_cutoff(self) -> None:
        errs = validate_actuals_mode(
            {
                "title": "いだてん岱明練習",
                "date": "2026-09-20",
                "status": "done",
                "tags": ["いだてん岱明練習"],
                "practice": {"items": []},
            },
            "2026-09-19",
        )
        self.assertEqual(errs, [])

    def test_allows_race_without_practice_block(self) -> None:
        errs = validate_actuals_mode(
            {
                "title": "第12回　中学駅伝金栗四三生誕の地なごみ大会",
                "date": "2026-09-20",
                "status": "scheduled",
                "tags": ["駅伝", "なごみ駅伝", "practice:daiming"],
            },
            "2026-09-19",
        )
        self.assertEqual(errs, [])


class LintEventsTests(unittest.TestCase):
    def test_lint_example_year_runs(self) -> None:
        from lint_events import lint_year

        errors = lint_year(2026)
        self.assertIsInstance(errors, list)
        # actuals-mode violations must not appear in committed YAML
        actuals_errs = [e for e in errors if "actuals_mode_from" in e]
        self.assertEqual(actuals_errs, [])


if __name__ == "__main__":
    unittest.main()
