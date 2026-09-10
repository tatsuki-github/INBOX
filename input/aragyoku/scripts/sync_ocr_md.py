#!/usr/bin/env python3
"""Sync ekiden-history ocr/*.md with full transcript tables from aragyoku JSON."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARAGYOKU = ROOT / "input/aragyoku"
EKIDEN_MEDIA = ROOT / "input/external/notion/media/ekiden-history"
OCR_DIR = EKIDEN_MEDIA / "ocr"
MANIFEST = ROOT / "input/external/media-manifest.json"

FULL_BY_GENDER = {
    "女子": ARAGYOKU / "women_full_2012_2025.json",
    "男子": ARAGYOKU / "men_full_2012_2025.json",
}


def _fmt_rank(value: int | None) -> str:
    return str(value) if value is not None else ""


def _fmt_note(leg: dict) -> str:
    parts: list[str] = []
    if leg.get("split_record"):
        parts.append("区間新")
    status = leg.get("status")
    if status and status != "ok":
        parts.append(status.upper())
    return " / ".join(parts)


def _team_table(team: dict) -> str:
    lines = [
        f"### {team['rank']}位 {team['team']} {team['total']}",
        "",
        "| 区 | 選手 | 学年 | 区間 | 累計 | 通過順位 | 区間順位 | 注釈 |",
        "|---:|:---|:---:|:---:|:---:|:---:|:---:|:---|",
    ]
    for leg in team["legs"]:
        lines.append(
            "| {leg} | {name} | {grade} | {split} | {cumulative} | {passing} | {split_rank} | {note} |".format(
                leg=leg["leg"],
                name=leg.get("name") or "",
                grade=leg.get("grade") if leg.get("grade") is not None else "",
                split=leg.get("split") or "",
                cumulative=leg.get("cumulative") or "",
                passing=_fmt_rank(leg.get("passing_rank")),
                split_rank=_fmt_rank(leg.get("split_rank")),
                note=_fmt_note(leg),
            )
        )
    return "\n".join(lines)


def _load_meta(stem: str) -> dict:
    path = EKIDEN_MEDIA / f"{stem}.meta.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _daimyo_block(year_entry: dict, meta: dict) -> str:
    daimyo = year_entry.get("daimyo") or {}
    structured = meta.get("structured_fields") or {}
    rank = daimyo.get("rank") or structured.get("岱明の順位")
    total = daimyo.get("total") or structured.get("岱明の記録")
    pace = (year_entry.get("pace") or {}).get("second_place_avg") or structured.get("2位の平均ペース")
    temp = (year_entry.get("weather") or {}).get("temperature_c")
    if temp is None:
        temp = structured.get("スタート時間付近の気温")
    lines = ["## 岱明の結果"]
    if rank is not None:
        lines.append(f"- 順位: {rank}")
    if total:
        lines.append(f"- 記録: {total}")
    if pace:
        lines.append(f"- 2位の平均ペース: {pace}")
    if temp is not None:
        lines.append(f"- スタート時間付近の気温: {temp}")
    return "\n".join(lines)


def render_markdown(stem: str, year_entry: dict, meta: dict) -> str:
    year, gender = stem.split("-", 1)
    page = meta.get("notion_page_url") or ""
    attachment = meta.get("source_attachment_id") or ""
    drive_id = year_entry.get("source_drive_id") or meta.get("drive_id") or ""
    date = year_entry.get("date") or ""
    team_count = year_entry.get("team_count") or len(year_entry.get("teams") or [])

    header = [
        f"# 荒玉中体連駅伝 {year} {gender} — 文字起こし/構造化",
        "",
        "> 出典: 結果ボード画像の全セル文字起こし（`input/aragyoku/transcripts/` 正本）。",
    ]
    if page:
        header.append(f"> Notion: {page}")
    if drive_id:
        header.append(f"> Google Drive: `{drive_id}`")
    header.append("")

    event_lines = ["## 大会情報"]
    if date:
        event_lines.append(f"- 開催日: {date}")
    event_lines.append(f"- 参加校数: {team_count}")
    legs = year_entry.get("legs") or []
    if legs:
        course = ", ".join(f"{L['leg']}区 {L['distance_km']}km" for L in legs)
        event_lines.append(f"- コース: {course}")

    body = [
        "\n".join(header),
        "\n".join(event_lines),
        "",
        _daimyo_block(year_entry, meta),
        "",
        "## フル順位表",
        "",
    ]
    for team in year_entry["teams"]:
        body.append(_team_table(team))
        body.append("")

    notes = year_entry.get("ocr_notes") or []
    memo = ["## メモ"]
    if notes:
        memo.extend(f"- {note}" for note in notes)
    if attachment:
        memo.append(f"- attachment: `{attachment}`")
    memo.append(
        "- 正本 JSON: "
        f"`input/aragyoku/transcripts/{year}-{gender}.json`"
    )
    body.append("\n".join(memo))
    return "\n".join(body).rstrip() + "\n"


def _year_entry_for(stem: str) -> dict | None:
    gender = "女子" if stem.endswith("女子") else "男子"
    year = stem.split("-", 1)[0]
    full_path = FULL_BY_GENDER[gender]
    if not full_path.exists():
        return None
    full = json.loads(full_path.read_text(encoding="utf-8"))
    return full.get("years", {}).get(year)


def sync_all() -> list[str]:
    updated: list[str] = []
    for path in sorted(OCR_DIR.glob("*.md")):
        stem = path.stem
        year_entry = _year_entry_for(stem)
        if not year_entry:
            continue
        meta = _load_meta(stem)
        path.write_text(render_markdown(stem, year_entry, meta), encoding="utf-8")
        updated.append(path.name)
    return updated


def update_manifest() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    for item in manifest.get("items") or []:
        if item.get("topic") != "ekiden":
            continue
        stem = item.get("stem")
        if not stem:
            continue
        gender = item.get("gender") or ("女子" if stem.endswith("女子") else "男子")
        year = item.get("year") or int(stem.split("-", 1)[0])
        transcript = ARAGYOKU / "transcripts" / f"{year}-{gender}.json"
        if transcript.exists():
            item["transcript_path"] = str(transcript.relative_to(ROOT))
            item["schema"] = "full-transcript-v1"
            entry = _year_entry_for(stem)
            if entry:
                item["team_count"] = entry.get("team_count") or len(entry.get("teams") or [])
                item["source_drive_id"] = entry.get("source_drive_id")
        ocr_text = (OCR_DIR / f"{stem}.md").read_text(encoding="utf-8")
        item["full_board_ocr"] = "## フル順位表" in ocr_text
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    updated = sync_all()
    update_manifest()
    print(f"updated {len(updated)} ocr markdown files")
    print("updated", MANIFEST)


if __name__ == "__main__":
    main()
