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
    maybe_write_root_calendar,
    month_anchor_id,
    render_markdown_calendar,
    write_markdown_calendar,
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
        self.assertIn("[7月](#month-07)", rendered)
        self.assertIn(f'<a id="{month_anchor_id(7)}"></a>', rendered)
        self.assertIn("## 2026年7月", rendered)
        self.assertIn("| 31 | 金 | 18:00 岱明夕練（各自アップ、600m2本（1500mRP、r=8分）） |", rendered)
        self.assertIn('<a id="memos"></a>', rendered)
        self.assertIn("## 日付なしメモ", rendered)
        self.assertIn("- 買い物リスト — - 牛乳", rendered)


class RootCalendarTests(unittest.TestCase):
    def test_maybe_write_root_calendar_writes_only_for_current_year(self) -> None:
        import tempfile

        events = [
            Event(
                title="テスト予定",
                start_date=date(2026, 8, 1),
                end_date=date(2026, 8, 1),
            )
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            calendar_path = tmp / "calendar.md"
            write_markdown_calendar(calendar_path, events, 2026)

            current_year = date.today().year
            root_path = maybe_write_root_calendar(
                events,
                current_year,
                calendar_path=calendar_path,
                root_path=tmp / "root-calendar.md",
            )
            if current_year == 2026:
                self.assertIsNotNone(root_path)
                self.assertTrue(root_path.exists())
                self.assertEqual(
                    root_path.read_text(encoding="utf-8"),
                    calendar_path.read_text(encoding="utf-8"),
                )
            else:
                self.assertIsNone(root_path)

            self.assertIsNone(
                maybe_write_root_calendar(
                    events,
                    1999,
                    calendar_path=calendar_path,
                    root_path=tmp / "unused.md",
                )
            )


if __name__ == "__main__":
    unittest.main()
