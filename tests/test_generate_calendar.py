from __future__ import annotations

import sys
import unittest
from datetime import date, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from generate_calendar import (  # noqa: E402
    Event,
    escape_markdown_table_cell,
    event_occurrence_dates,
    format_markdown_event_line,
    group_events_by_date,
    render_markdown_calendar,
)


class MarkdownCalendarTests(unittest.TestCase):
    def test_escape_markdown_table_cell(self) -> None:
        self.assertEqual(
            escape_markdown_table_cell("A|B\nC"),
            "A\\|B C",
        )

    def test_event_occurrence_dates_expands_multi_day(self) -> None:
        event = Event(
            title="夏休み",
            start_date=date(2026, 7, 20),
            end_date=date(2026, 7, 22),
        )
        self.assertEqual(
            event_occurrence_dates(event, 2026),
            [date(2026, 7, 20), date(2026, 7, 21), date(2026, 7, 22)],
        )

    def test_format_markdown_event_line_timed_with_description(self) -> None:
        event = Event(
            title="岱明夕練",
            start_date=date(2026, 7, 31),
            end_date=date(2026, 7, 31),
            all_day=False,
            start_time=time(18, 0),
            description="各自アップ、600m2本（1500mRP、r=8分）",
        )
        self.assertEqual(
            format_markdown_event_line(event),
            "18:00 岱明夕練（各自アップ、600m2本（1500mRP、r=8分））",
        )

    def test_group_events_by_date_sorts_timed_before_all_day(self) -> None:
        timed = Event(
            title="朝練",
            start_date=date(2026, 7, 31),
            end_date=date(2026, 7, 31),
            all_day=False,
            start_time=time(8, 0),
        )
        all_day = Event(
            title="祝日",
            start_date=date(2026, 7, 31),
            end_date=date(2026, 7, 31),
            all_day=True,
        )
        grouped = group_events_by_date([all_day, timed], 2026)
        titles = [event.title for event in grouped[date(2026, 7, 31)]]
        self.assertEqual(titles, ["朝練", "祝日"])

    def test_render_markdown_calendar_includes_month_and_memo_section(self) -> None:
        events = [
            Event(
                title="岱明夕練",
                start_date=date(2026, 7, 31),
                end_date=date(2026, 7, 31),
                all_day=False,
                start_time=time(18, 0),
                description="各自アップ、600m2本（1500mRP、r=8分）",
            ),
            Event(
                title="買い物リスト",
                category="メモ",
                status="inbox",
                description="- 牛乳",
            ),
        ]
        rendered = render_markdown_calendar(events, 2026)
        self.assertIn("# 2026年カレンダー", rendered)
        self.assertIn("## 2026年7月", rendered)
        self.assertIn("| 31 | 金 | 18:00 岱明夕練（各自アップ、600m2本（1500mRP、r=8分）） |", rendered)
        self.assertIn("## 日付なしメモ", rendered)
        self.assertIn("- 買い物リスト — - 牛乳", rendered)


if __name__ == "__main__":
    unittest.main()
