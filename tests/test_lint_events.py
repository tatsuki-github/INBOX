from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lint_events import lint_year  # noqa: E402


class LintEventsTests(unittest.TestCase):
    def test_lint_example_year_runs(self) -> None:
        errors = lint_year(2026)
        self.assertIsInstance(errors, list)


if __name__ == "__main__":
    unittest.main()
