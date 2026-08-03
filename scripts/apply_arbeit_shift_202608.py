#!/usr/bin/env python3
"""2026年8月のアルバイトシフト画像を events YAML に反映する。

既存エントリのテキストには一切触れず、日付順の正しい位置に新規エントリの
テキストブロックを挿入するだけにする（yaml.dump による全体再ダンプは
既存の description 等のスタイルを壊すため使わない）。
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT / "input" / "events.2026.yaml"

ARBEIT_TAG = "会社"

# {date: [(start, end, name), ...]}
SHIFTS: dict[str, list[tuple[str, str, str]]] = {
    "2026-08-02": [("10:00", "13:00", "荒田")],
    "2026-08-04": [("10:00", "13:00", "小森"), ("10:00", "13:00", "寛田")],
    "2026-08-05": [("10:00", "14:00", "岩倉")],
    "2026-08-06": [("10:00", "13:00", "荒田"), ("10:00", "14:00", "岩倉"), ("10:00", "15:00", "小森")],
    "2026-08-07": [("10:00", "17:00", "川上")],
    "2026-08-10": [("09:00", "12:00", "杉永"), ("10:00", "17:00", "川上"), ("10:00", "13:00", "荒田")],
    "2026-08-14": [("10:00", "17:00", "川上")],
    "2026-08-17": [("10:00", "18:00", "池上")],
    "2026-08-21": [("10:00", "13:00", "荒田"), ("10:00", "18:00", "池上")],
    "2026-08-25": [("09:00", "12:00", "石原"), ("10:00", "15:00", "小森"), ("10:00", "17:00", "川上")],
    "2026-08-26": [
        ("09:00", "12:00", "石原"),
        ("10:00", "13:00", "荒田"),
        ("10:00", "14:00", "岩倉"),
        ("10:00", "15:00", "小森"),
    ],
    "2026-08-27": [("09:00", "12:00", "石原"), ("10:00", "14:00", "岩倉"), ("10:00", "15:00", "小森")],
    "2026-08-28": [("10:00", "13:00", "荒田"), ("10:00", "18:00", "池上")],
    "2026-08-30": [("09:00", "12:00", "石原"), ("10:00", "13:00", "荒田")],
}


def render_block(date: str, start: str, end: str, name: str) -> str:
    return (
        f"- title: {name}\n"
        f"  date: '{date}'\n"
        "  all_day: false\n"
        f"  start_time: '{start}'\n"
        f"  end_time: '{end}'\n"
        "  category: 予定\n"
        "  status: scheduled\n"
        "  tags:\n"
        f"  - {ARBEIT_TAG}\n"
    )


def main() -> None:
    text = YAML_PATH.read_text(encoding="utf-8")

    events_marker = re.search(r"^events:\n", text, re.MULTILINE)
    if not events_marker:
        raise RuntimeError("events: セクションが見つかりません")
    header = text[: events_marker.end()]
    body = text[events_marker.end() :]

    starts = [m.start() for m in re.finditer(r"(?m)^-(?=\s)", body)]
    if not starts:
        raise RuntimeError("イベントブロックが見つかりません")
    blocks = [body[s:e] for s, e in zip(starts, starts[1:] + [len(body)])]

    date_re = re.compile(r"^\s*date:\s*'?(\d{4}-\d{2}-\d{2})'?\s*$", re.MULTILINE)
    title_re = re.compile(r"^-\s*title:\s*(.+)$", re.MULTILINE)

    def block_date(block: str) -> str | None:
        m = date_re.search(block)
        return m.group(1) if m else None

    def block_title(block: str) -> str:
        m = title_re.search(block)
        return m.group(1).strip() if m else ""

    existing_keys: set[tuple[str, str]] = set()
    for block in blocks:
        d = block_date(block)
        if d is None:
            continue
        for m in re.finditer(r"^\s*start_time:\s*'?([0-9:]+)'?\s*$", block, re.MULTILINE):
            existing_keys.add((d, block_title(block) + "@" + m.group(1)))
        if not re.search(r"^\s*start_time:", block, re.MULTILINE):
            existing_keys.add((d, block_title(block) + "@"))

    new_blocks_by_date: dict[str, list[str]] = {}
    added = 0
    for date, shifts in sorted(SHIFTS.items()):
        for start, end, name in sorted(shifts):
            if (date, f"{name}@{start}") in existing_keys:
                continue
            new_blocks_by_date.setdefault(date, []).append(render_block(date, start, end, name))
            added += 1

    pending_dates = sorted(new_blocks_by_date.keys())
    pending_idx = 0
    merged_blocks: list[str] = []
    for block in blocks:
        d = block_date(block)
        if d is not None:
            while pending_idx < len(pending_dates) and pending_dates[pending_idx] < d:
                merged_blocks.extend(new_blocks_by_date[pending_dates[pending_idx]])
                pending_idx += 1
        merged_blocks.append(block)
    while pending_idx < len(pending_dates):
        merged_blocks.extend(new_blocks_by_date[pending_dates[pending_idx]])
        pending_idx += 1

    total_count = len(blocks) + added
    header = re.sub(r"^# 件数: \d+", f"# 件数: {total_count}", header, count=1, flags=re.MULTILINE)

    new_text = header + "".join(merged_blocks)
    YAML_PATH.write_text(new_text, encoding="utf-8")
    print(f"Updated {YAML_PATH}: {total_count} events ({added} new)")


if __name__ == "__main__":
    main()
