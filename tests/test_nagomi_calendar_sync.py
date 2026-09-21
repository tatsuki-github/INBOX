#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import nagomi_2026_results_data as results
from nagomi_calendar_sync import (
    RESULT_MARKER,
    format_daiming_block,
    merge_result_into_description,
    update_event_in_yaml_text,
)


def test_format_includes_daiming_ranks() -> None:
    block = format_daiming_block(
        women=results.WOMEN,
        men=results.MEN,
        results_paths=["path/女子成績表.md"],
    )
    assert RESULT_MARKER in block
    assert "女子" in block and "6位　30:18" in block
    assert "山﨑莉奈" in block and "山本哲瑠" in block
    assert "男子A" in block and "18位　42:39" in block
    assert "男子B" in block and "31位　48:10" in block
    assert "path/女子成績表.md" in block


def test_merge_is_idempotent() -> None:
    block = format_daiming_block(women=results.WOMEN, men=results.MEN, results_paths=[])
    base = "開催要項本文\n1．主催\n"
    once = merge_result_into_description(base, block)
    twice = merge_result_into_description(once, block)
    assert once.count(RESULT_MARKER) == 1
    assert twice.count(RESULT_MARKER) == 1
    assert "開催要項本文" in twice


def test_update_yaml_event() -> None:
    sample = """year: 2026
events:
- title: 他の予定
  date: '2026-09-19'
  status: scheduled
- title: 第12回　中学駅伝金栗四三生誕の地なごみ大会
  date: '2026-09-20'
  all_day: true
  category: 予定
  status: scheduled
  description: |
    開催要項
    1．主催
  tags:
  - なごみ駅伝
- title: 翌日
  date: '2026-09-21'
  status: scheduled
"""
    block = format_daiming_block(women=results.WOMEN, men=results.MEN, results_paths=["a.md"])
    new, ok = update_event_in_yaml_text(
        sample,
        date="2026-09-20",
        title_substr="なごみ",
        result_block=block,
        status="done",
    )
    assert ok
    assert "status: done" in new
    assert RESULT_MARKER in new
    assert "6位　30:18" in new
    assert "開催要項" in new
    assert new.count("status: done") == 1
