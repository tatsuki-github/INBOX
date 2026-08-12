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
    event_anchor_id,
    event_occurrence_dates,
    format_back_to_top_link,
    format_markdown_event_details_block,
    format_markdown_event_details_body,
    format_markdown_event_line,
    format_markdown_event_link,
    format_markdown_event_summary,
    group_events_by_date,
    load_custom_events,
    maybe_write_root_calendar,
    memo_anchor_id,
    month_anchor_id,
    page_top_anchor_id,
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
            format_markdown_event_summary(event),
            "18:00 岱明夕練",
        )
        self.assertEqual(
            format_markdown_event_line(event),
            "18:00 岱明夕練",
        )

    def test_format_markdown_event_link_and_details(self) -> None:
        event = Event(
            title="岱明夕練",
            start_date=date(2026, 7, 31),
            end_date=date(2026, 7, 31),
            all_day=False,
            start_time=time(18, 0),
            end_time=time(21, 0),
            status="scheduled",
            tags=["ランニング"],
            description="各自アップ、600m2本（1500mRP、r=8分）",
        )
        day = date(2026, 7, 31)
        self.assertEqual(
            format_markdown_event_link(event, day, 0),
            f"[18:00 岱明夕練](#{event_anchor_id(day, 0)})",
        )
        details = format_markdown_event_details_block(event, day, 0)
        self.assertIn(f'<a id="{event_anchor_id(day, 0)}"></a>', details)
        self.assertIn("<details>", details)
        self.assertIn("<summary>18:00 岱明夕練</summary>", details)
        self.assertIn("- **件名**: 岱明夕練", details)
        self.assertIn("- **開始時刻**: 18:00", details)
        self.assertIn("- **終了時刻**: 21:00", details)
        self.assertIn("- **ステータス**: scheduled", details)
        self.assertIn("- **タグ**: ランニング", details)
        self.assertIn("各自アップ、600m2本（1500mRP、r=8分）", details)

    def test_format_markdown_event_details_shows_all_fields_even_when_empty(self) -> None:
        event = Event(
            title="シンプル予定",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
        )
        body = format_markdown_event_details_body(event, date(2026, 1, 1))
        self.assertIn("- **件名**: シンプル予定", body)
        self.assertIn("- **ステータス**: （なし）", body)
        self.assertIn("- **タグ**: （なし）", body)
        self.assertIn("- **場所**: （なし）", body)
        self.assertIn("- **URL**: （なし）", body)
        self.assertIn("**説明**", body)
        self.assertIn("（なし）", body)

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
        self.assertIn(f'<a id="{page_top_anchor_id()}"></a>', rendered)
        self.assertIn("# 2026年カレンダー", rendered)
        self.assertIn("[7月](#month-07)", rendered)
        self.assertIn(f'<a id="{month_anchor_id(7)}"></a>', rendered)
        self.assertIn("## 2026年7月", rendered)
        self.assertIn(
            f"| 31 | 金 | [18:00 岱明夕練](#{event_anchor_id(date(2026, 7, 31), 0)}) |",
            rendered,
        )
        self.assertIn("### 予定詳細", rendered)
        self.assertIn("- **件名**: 岱明夕練", rendered)
        self.assertIn(f"[↑2026年7月](#{month_anchor_id(7)})", rendered)
        self.assertIn(format_back_to_top_link(), rendered)
        self.assertIn("各自アップ、600m2本（1500mRP、r=8分）", rendered)
        self.assertIn('<a id="memos"></a>', rendered)
        self.assertIn("## 日付なしメモ", rendered)
        self.assertIn(f"- [買い物リスト](#{memo_anchor_id(0)})", rendered)
        self.assertIn("### メモ詳細", rendered)
        self.assertIn("<details>", rendered.split("### メモ詳細", 1)[1])
        self.assertIn("- **件名**: 買い物リスト", rendered)
        self.assertIn("- 牛乳", rendered)


class DescriptionFileTests(unittest.TestCase):
    def test_load_custom_events_reads_description_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            memo_path = tmp / "memo.txt"
            memo_path.write_text("外部ファイル本文", encoding="utf-8")
            input_path = tmp / "events.yaml"
            input_path.write_text(
                f"""\
year: 2026
events:
  - title: 長文メモ
    category: メモ
    description: 先頭説明
    description_file: {memo_path}
""",
                encoding="utf-8",
            )

            events = load_custom_events(input_path, 2026)
            self.assertEqual(len(events), 1)
            self.assertEqual(
                events[0].description,
                "先頭説明\n\n外部ファイル本文",
            )


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
