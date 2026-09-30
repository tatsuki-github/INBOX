#!/usr/bin/env python3
"""Rewrite unfriendly prepared-qa answers (calendar / meet-folder / path dumps).

Usage:
  python3 scripts/rewrite_prepared_qa_friendly.py
  python3 scripts/rewrite_prepared_qa_friendly.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_prepared_qa_bulk import (  # noqa: E402
    clean_user_facing_text,
    drive_url_for_calendar,
    friendly_calendar_answer,
    friendly_meet_folder_answer,
    friendly_status_phrase,
    load_drive_meet_folder_map,
    resolve_drive_meet_url,
)

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
EVENTS = {
    2025: ROOT / "input" / "events.2025.yaml",
    2026: ROOT / "input" / "events.2026.yaml",
}


def load_events() -> dict[tuple[str, str], dict]:
    """Map (date, title) -> event."""
    out: dict[tuple[str, str], dict] = {}
    for year, path in EVENTS.items():
        if not path.exists():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for ev in data.get("events") or []:
            title = (ev.get("title") or "").strip()
            date = str(ev.get("date") or ev.get("start") or "").strip()
            if title and date:
                out[(date[:10], title)] = ev
    return out


def parse_cal_answer_header(answer: str) -> tuple[str, str] | None:
    m = re.match(r"^(.+?)は\s*(20\d{2}-\d{2}-\d{2})\s*です。", answer.strip())
    if not m:
        return None
    return m.group(1).strip(), m.group(2)


def rewrite_calendar_entry(
    entry: dict,
    events: dict[tuple[str, str], dict],
    drive_map: dict[str, str],
) -> bool:
    ans = entry.get("answer") or ""
    parsed = parse_cal_answer_header(ans)
    if not parsed:
        # fallback: strip jargon from existing text
        new = ans
        new = re.sub(r"\s*状態:\s*\w+。", " ", new)
        new = re.sub(r"\s*概要:\s*", " ", new)
        new = clean_user_facing_text(new, max_len=400)
        if new and not new.endswith("。"):
            new += "。"
        if new != ans.strip():
            entry["answer"] = new + "\n"
            return True
        return False
    title, date = parsed
    ev = events.get((date, title))
    if ev:
        desc = str(ev.get("description") or "")
        new = friendly_calendar_answer(
            title,
            date,
            location=str(ev.get("location") or ""),
            status=str(ev.get("status") or ""),
            description=desc,
            drive_url=drive_url_for_calendar(title, desc, drive_map),
        )
    else:
        # keep location if present in old answer
        loc_m = re.search(r"場所:\s*([^。]+)。", ans)
        loc = loc_m.group(1) if loc_m else ""
        status_m = re.search(r"状態:\s*(\w+)。", ans)
        status = status_m.group(1) if status_m else ""
        desc_m = re.search(r"概要:\s*(.+)$", ans, re.S)
        desc = desc_m.group(1) if desc_m else ""
        new = friendly_calendar_answer(
            title,
            date,
            location=loc,
            status=status,
            description=desc,
            drive_url=drive_url_for_calendar(title, desc, drive_map),
        )
    if new.strip() != ans.strip():
        entry["answer"] = new.strip() + "\n"
        return True
    return False


def rewrite_practice_cal_entry(entry: dict) -> bool:
    ans = entry.get("answer") or ""
    new = re.sub(r"\s*状態:\s*\w+。", " ", ans)
    # drop path dumps if any
    new = clean_user_facing_text(new, max_len=360)
    # restore a readable lead if cleaned too hard
    m = re.match(r"(20\d{2}-\d{2}-\d{2}\s*の予定「[^」]+」です。)", ans.strip())
    if m and not new.startswith(m.group(1)[:10]):
        rest = new
        status = ""
        # keep done/cancelled meaning without jargon
        if "状態: done" in ans:
            status = friendly_status_phrase("done")
        elif "状態: cancelled" in ans or "状態: canceled" in ans:
            status = friendly_status_phrase("cancelled")
        pieces = [m.group(1)]
        if status:
            pieces.append(status)
        if rest and rest not in m.group(1):
            # remove duplicated lead from rest
            rest2 = rest.replace(m.group(1), "").strip()
            if rest2:
                pieces.append(rest2 if rest2.endswith("。") else rest2 + "。")
        new = " ".join(pieces)
    if not new.endswith("。"):
        new += "。"
    if new.strip() != ans.strip():
        entry["answer"] = new.strip() + "\n"
        return True
    return False


def rewrite_meet_folder_entry(entry: dict, drive_map: dict[str, str]) -> bool:
    sources = entry.get("sources") or []
    if not sources:
        return False
    rel = sources[0]
    folder_name = Path(rel).name
    year_m = re.search(r"/(20\d{2})年度/", rel.replace("\\", "/"))
    year = year_m.group(1) if year_m else ""
    title = re.sub(r"^\d{4}-\d{2,4}_", "", folder_name)
    title = re.sub(r"^\d{2,4}_", "", title)
    drive_url = resolve_drive_meet_url(folder_name, title, drive_map)
    new = friendly_meet_folder_answer(title, year or "今年度", folder_name, drive_url)
    idx = "input/external/drive/shared/大会/INDEX.md"
    if drive_url and idx not in sources:
        entry["sources"] = list(sources) + [idx]
    if new.strip() != (entry.get("answer") or "").strip():
        entry["answer"] = new.strip() + "\n"
        return True
    return False


HANDCRAFT: dict[str, str] = {
    "aragyoku-sb-preview-where": (
        "2026年荒玉中体連駅伝の岱明オーダー・数式予想は、大会のGoogleドライブフォルダにあります。\n"
        "https://drive.google.com/drive/folders/1G8IlaBp9xVmXUynBAjV9ZZQPfFqzj4Yi\n"
        "開催日は 2026-10-14（予備日 2026-10-15）です。"
    ),
    "junior-2026-pdf": (
        "2026年・第3回県ジュニア駅伝の結果資料です。\n"
        "大会フォルダ: https://drive.google.com/drive/folders/1pUww3wPlyy4IoSNUy58qK9yhCRzeU_-2\n"
        "結果の詳細は「ジュニア駅伝の結果は？」でも確認できます。"
    ),
    "junior-2026-result": (
        "2026年・第3回県ジュニア駅伝（2026-09-26）の岱明結果です。"
        "女子CS 12位36:52、男子CS 14位44:23。\n"
        "大会フォルダ: https://drive.google.com/drive/folders/1pUww3wPlyy4IoSNUy58qK9yhCRzeU_-2"
    ),
    "junior-2026-nankan-tamafz-detail": None,  # patched below
}


def patch_nankan(answer: str) -> str:
    return re.sub(
        r"正本:\s*荒玉地区の結果\.md\s*/\s*",
        "詳細資料: ",
        answer,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = data.get("entries") or []
    events = load_events()
    drive_map = load_drive_meet_folder_map()

    changed = 0
    for entry in entries:
        eid = entry.get("id") or ""
        before = entry.get("answer")
        if eid in HANDCRAFT and HANDCRAFT[eid] is not None:
            entry["answer"] = HANDCRAFT[eid].strip() + "\n"
        elif eid == "junior-2026-nankan-tamafz-detail":
            entry["answer"] = patch_nankan(entry.get("answer") or "")
            if not entry["answer"].endswith("\n"):
                entry["answer"] += "\n"
        elif eid.startswith("cal-"):
            rewrite_calendar_entry(entry, events, drive_map)
        elif eid.startswith("practice-cal-"):
            rewrite_practice_cal_entry(entry)
        elif eid.startswith("meet-folder-"):
            rewrite_meet_folder_entry(entry, drive_map)
        else:
            # generic: strip 「状態: xxx」 and path dumps in answers that still have them
            ans = entry.get("answer") or ""
            if "状態:" in ans or "input/idaten-corpus" in ans:
                new = re.sub(r"\s*状態:\s*\w+。", " ", ans)
                new = re.sub(r"詳細テキスト:\s*input/[^\n]+", "", new)
                new = re.sub(r"input/idaten-corpus/[^\s。]+", "", new)
                new = re.sub(r"\s+", " ", new).strip()
                # preserve multiline drive links if original had them
                if "drive.google.com" in ans and "drive.google.com" not in new:
                    new = ans
                    new = re.sub(r"\s*状態:\s*\w+。", "\n", new)
                    new = re.sub(
                        r"詳細テキスト:\s*input/[^\n]+\n?",
                        "",
                        new,
                    )
                    new = re.sub(r"索引:\s*[^\n]+\n?", "", new)
                if new.strip() != (before or "").strip():
                    entry["answer"] = new.strip() + "\n"
        if entry.get("answer") != before:
            changed += 1

    print(f"rewrote {changed} entries")
    # sanity samples
    for sample_id in (
        "cal-2026-20261014-荒玉中体連駅伝",
        "meet-folder-2026-荒玉中体連駅伝",
        "aragyoku-sb-preview-where",
        "junior-2026-pdf",
    ):
        e = next((x for x in entries if x["id"] == sample_id), None)
        if e:
            print("---", sample_id)
            print(e["answer"][:260].replace("\n", " | "))

    if args.dry_run:
        return 0

    # Keep total in sync
    data["total"] = len(entries)

    # Prefer ruamel round-trip to avoid reformatting the whole catalog when possible.
    try:
        from ruamel.yaml import YAML

        yaml_rt = YAML()
        yaml_rt.preserve_quotes = True
        yaml_rt.width = 1000
        rt_data = yaml_rt.load(FAQ.read_text(encoding="utf-8"))
        by_id = {e["id"]: e for e in entries}
        for e in rt_data["entries"]:
            eid = e.get("id")
            if eid in by_id:
                e["answer"] = by_id[eid]["answer"]
                if eid.startswith("meet-folder-"):
                    e["sources"] = by_id[eid]["sources"]
        rt_data["total"] = len(rt_data["entries"])
        with FAQ.open("w", encoding="utf-8") as fh:
            yaml_rt.dump(rt_data, fh)
    except Exception as exc:  # pragma: no cover
        print(f"ruamel write failed ({exc}); falling back to safe_dump")
        FAQ.write_text(
            yaml.safe_dump(
                data,
                allow_unicode=True,
                sort_keys=False,
                width=1000,
            ),
            encoding="utf-8",
        )
    print(f"wrote {FAQ}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
