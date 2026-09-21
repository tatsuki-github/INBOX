#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大会成績を events.YYYY.yaml カレンダーへ反映する。

ナレッジ（成績表）を追加したら、当該日の大会イベントを:
- status: done
- description 先頭に【結果（岱明）】ブロック
へ更新する。開催要項など既存本文は RESULT_MARKER 以降に残す。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

RESULT_MARKER = "【結果（岱明）】"
RESULT_END_MARKER = "【開催要項・運用】"


def _fmt_rank(rank: int | None) -> str:
    if rank is None:
        return "OP"
    return f"{rank}位"


def format_daiming_block(
    *,
    women: list[dict[str, Any]],
    men: list[dict[str, Any]],
    results_paths: list[str],
) -> str:
    """2025 なごみカレンダーと同型の岱明結果ブロックを作る（時刻は M:SS）。"""
    lines: list[str] = [RESULT_MARKER, ""]

    def add_team(label: str, team: dict[str, Any] | None) -> None:
        if not team:
            return
        total = team.get("total") or "—"
        lines.append(label)
        lines.append(f"{_fmt_rank(team.get('rank'))}　{total}")
        for i, leg in enumerate(team.get("legs") or [], start=1):
            if not leg.get("name"):
                continue
            split = leg.get("split") or ""
            sr = leg.get("split_rank")
            sr_s = f" 区間{sr}位" if sr is not None else ""
            lines.append(f"{i}区　{leg['name']}　{split}{sr_s}")
        lines.append("")

    w_a = next((t for t in women if t.get("team") == "岱明A"), None)
    w_b = next((t for t in women if t.get("team") == "岱明B"), None)
    m_a = next((t for t in men if t.get("team") == "岱明A"), None)
    m_b = next((t for t in men if t.get("team") == "岱明B"), None)

    # 2025 は「女子」のみ。A/B がある年は女子 / 女子B
    add_team("女子", w_a)
    add_team("女子B", w_b)
    add_team("男子A", m_a)
    add_team("男子B", m_b)

    if results_paths:
        lines.append("成績表:")
        for p in results_paths:
            lines.append(f"  {p}")
        lines.append("")

    lines.append("---")
    lines.append(RESULT_END_MARKER)
    lines.append("")
    return "\n".join(lines)


def _strip_old_result_prefix(description: str) -> str:
    """既存の【結果（岱明）】〜【開催要項・運用】を除去し、要項本文だけ残す。"""
    text = description.strip("\n")
    if RESULT_MARKER in text and RESULT_END_MARKER in text:
        after = text.split(RESULT_END_MARKER, 1)[1]
        return after.lstrip("\n")
    # 2025 型（結果のみ）やマーカー無しはそのまま
    if text.startswith(RESULT_MARKER):
        # 結果のみで要項が無い場合はそのまま差し替え対象
        return ""
    return text


def merge_result_into_description(description: str, result_block: str) -> str:
    body = _strip_old_result_prefix(description)
    if body:
        return f"{result_block.rstrip()}\n{body}".rstrip() + "\n"
    return result_block.rstrip() + "\n"


def update_event_in_yaml_text(
    yaml_text: str,
    *,
    date: str,
    title_substr: str,
    result_block: str,
    status: str = "done",
) -> tuple[str, bool]:
    """events.YYYY.yaml 本文を外科的に更新。戻り値は (新本文, 更新したか)。"""
    # date 行の直後〜次の同レベル - title までをイベントブロックとみなす
    pattern = re.compile(
        rf"(^- title: ([^\n]*{re.escape(title_substr)}[^\n]*)\n"
        rf"  date: '{re.escape(date)}'\n"
        rf"(?:.*\n)*?)"
        rf"(  status: )(\w+)(\n)"
        rf"(  description: \|(\n))?",
        re.MULTILINE,
    )
    m = pattern.search(yaml_text)
    if not m:
        # description が status より前のケースは稀。簡易フォールバック
        return yaml_text, False

    # より堅牢に: date でイベント開始を探し、次の "- title:" までを切り出す
    start_pat = re.compile(
        rf"^(- title: [^\n]*{re.escape(title_substr)}[^\n]*\n"
        rf"  date: '{re.escape(date)}'\n)",
        re.MULTILINE,
    )
    sm = start_pat.search(yaml_text)
    if not sm:
        return yaml_text, False
    start = sm.start()
    rest = yaml_text[sm.end() :]
    next_ev = re.search(r"\n- title: ", rest)
    end = sm.end() + (next_ev.start() + 1 if next_ev else len(rest))
    block = yaml_text[start:end]

    # status
    new_block, n_status = re.subn(
        r"(^  status: )\w+",
        rf"\g<1>{status}",
        block,
        count=1,
        flags=re.MULTILINE,
    )
    if n_status == 0:
        return yaml_text, False

    # description: |
    desc_m = re.search(r"^  description: \|\n", new_block, re.MULTILINE)
    if not desc_m:
        # description 無し → status の後に挿入
        new_block = re.sub(
            rf"(^  status: {status}\n)",
            rf"\1  description: |\n{ _indent_block(result_block) }",
            new_block,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        desc_start = desc_m.end()
        # description 本体: 先頭がスペース4つ以上の行
        lines = new_block[desc_start:].splitlines(keepends=True)
        body_lines: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("    ") or line.strip() == "":
                # 空行は description 内の可能性。次がタグ等なら終了
                if line.strip() == "":
                    # peek
                    if i + 1 < len(lines) and not lines[i + 1].startswith("    "):
                        break
                body_lines.append(line)
                i += 1
                continue
            break
        old_desc = "".join(body_lines)
        # unindent 4 spaces
        unindented = re.sub(r"^    ", "", old_desc, flags=re.MULTILINE)
        merged = merge_result_into_description(unindented, result_block)
        new_desc = _indent_block(merged)
        tail = "".join(lines[i:])
        new_block = new_block[:desc_start] + new_desc + ("" if new_desc.endswith("\n") else "\n") + tail

    return yaml_text[:start] + new_block + yaml_text[end:], True


def _indent_block(text: str, spaces: int = 4) -> str:
    pad = " " * spaces
    out: list[str] = []
    for line in text.rstrip("\n").split("\n"):
        out.append(f"{pad}{line}\n")
    return "".join(out)


def sync_nagomi_2026_calendar(
    *,
    events_path: Path | None = None,
    women: list[dict[str, Any]],
    men: list[dict[str, Any]],
) -> bool:
    """2026-09-20 なごみイベントへ岱明結果を書き、status=done にする。"""
    path = events_path or (ROOT / "input" / "events.2026.yaml")
    meet_rel = "input/external/drive/shared/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会"
    block = format_daiming_block(
        women=women,
        men=men,
        results_paths=[
            f"{meet_rel}/女子成績表.md",
            f"{meet_rel}/男子成績表.md",
        ],
    )
    text = path.read_text(encoding="utf-8")
    new_text, ok = update_event_in_yaml_text(
        text,
        date="2026-09-20",
        title_substr="なごみ",
        result_block=block,
        status="done",
    )
    if not ok:
        raise RuntimeError(f"なごみイベントが見つかりません: {path}")
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return new_text != text
