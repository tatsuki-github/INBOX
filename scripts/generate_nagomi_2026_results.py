#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-09-20 なごみ駅伝 成績表を MD/JSON に書き出し、コーパスへ dual-write する。"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import nagomi_2026_results_data as results  # noqa: E402
from nagomi_calendar_sync import sync_nagomi_2026_calendar  # noqa: E402

MEET_DIR = ROOT / "input/external/drive/shared/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会"
CORPUS_MEET = ROOT / "input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会"


def _dual_write(text: str, name: str) -> None:
    MEET_DIR.mkdir(parents=True, exist_ok=True)
    CORPUS_MEET.mkdir(parents=True, exist_ok=True)
    (MEET_DIR / name).write_text(text, encoding="utf-8")
    (CORPUS_MEET / name).write_text(text, encoding="utf-8")


def _parse_mmss(s: str | None) -> int | None:
    if not s:
        return None
    parts = s.split(":")
    if len(parts) != 2:
        return None
    return int(parts[0]) * 60 + int(parts[1])


def validate_teams(teams: list[dict[str, Any]], label: str) -> list[str]:
    errs: list[str] = []
    for team in teams:
        prev = 0
        for i, leg in enumerate(team["legs"], start=1):
            split = _parse_mmss(leg.get("split"))
            cum = _parse_mmss(leg.get("cum"))
            if split is None or cum is None:
                continue
            if prev + split != cum:
                errs.append(
                    f"{label} {team['team']} {i}区: cum {leg['cum']} != prev+split "
                    f"({prev}+{split}={prev + split})"
                )
            prev = cum
        total = _parse_mmss(team.get("total"))
        last_cum = None
        for leg in reversed(team["legs"]):
            last_cum = _parse_mmss(leg.get("cum"))
            if last_cum is not None:
                break
        if total is not None and last_cum is not None and total != last_cum:
            errs.append(f"{label} {team['team']}: total {team['total']} != last cum")
    return errs


def render_results_md(gender: str, teams: list[dict[str, Any]], leg_km: int, total_km: int) -> str:
    ev = results.EVENT
    lines = [
        f"# {ev['title']} {gender}成績表",
        "",
        f"- 日付: {ev['date']}",
        f"- 会場: {ev['venue']}",
        f"- 各区 {leg_km}km / 総合 {total_km}km",
        "- 上段: 選手氏名・学年 / 中段: (順位)通過記録 / 下段: (順位)区間記録",
        "- 文字起こし正本（成績表写真）。OCR 後に目視校正し、2026-09-18 区間オーダーと名寄せ。",
        f"- 原本: {', '.join(ev['sources'])}",
        "",
        "| 順位 | No. | チーム | 総合 | 1区 | 2区 | 3区 | 4区 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for team in teams:
        rank = "OP" if team.get("rank") is None else str(team["rank"])
        total = team.get("total") or "—"
        no = str(team.get("no") or "")
        cells = []
        for leg in team["legs"]:
            if not leg.get("name"):
                cells.append("")
                continue
            grade = f"{leg['grade']}" if leg.get("grade") is not None else ""
            split_r = f"({leg['split_rank']})" if leg.get("split_rank") is not None else ""
            cells.append(f"{leg['name']}{grade} {split_r}{leg.get('split') or ''}")
        lines.append("| " + " | ".join([rank, no, team["team"], total, *cells]) + " |")
    lines.append("")
    lines.append("## 区間詳細")
    lines.append("")
    for team in teams:
        rank = "OP" if team.get("rank") is None else f"{team['rank']}位"
        total = team.get("total") or "—"
        no = team.get("no")
        no_s = f"No.{no} " if no is not None else ""
        lines.append(f"### {rank} {no_s}{team['team']}　総合 {total}")
        lines.append("")
        lines.append("| 区間 | 選手 | 学年 | 区間 | 区間順 | 通過 | 通過順 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for i, leg in enumerate(team["legs"], start=1):
            if not leg.get("name") and not leg.get("split"):
                lines.append(f"| {i}区 |  |  |  |  |  |  |")
                continue
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"{i}区",
                        str(leg.get("name") or ""),
                        str(leg.get("grade") or ""),
                        str(leg.get("split") or ""),
                        str(leg.get("split_rank") if leg.get("split_rank") is not None else ""),
                        str(leg.get("cum") or ""),
                        str(leg.get("cum_rank") if leg.get("cum_rank") is not None else ""),
                    ]
                )
                + " |"
            )
        lines.append("")
    lines.append("## 校正メモ")
    lines.append("")
    if gender == "女子":
        lines.extend(
            [
                "- 氏名は成績表を優先し、9/18 区間オーダーと一致する表記へ正規化（居石華音、秀島恋莉、山﨑莉奈、串間聖那 等）。",
                "- 今回受領した女子・男子成績表PDFを全4ページ目視照合し、通過順位・区間順位と氏名を校正。",
                "- 佐敷はオーダー空欄のため、成績表表記の **田中仁菜**・**志水そよ花** を採用。",
                "- No.17 はオーダー・出走メンバーから **南関β**（成績表チーム名の OCR 誤読を校正）。",
                "- 玉名高校附属 No.03 1区は当日 **三吉悠日**（オーダー表記の大木莉子から変更）。",
                "- 佐敷（No.15）はオーダー空欄のため成績表の読みを採用。",
                "- 泗水 3区の通過順位欄は成績表上欠損（区間記録 8:36 / 通過 23:44 のみ）。",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "- 氏名は成績表を優先し、9/18 区間オーダーと一致する表記へ正規化（津口晃誠、松浦眞大、隈部侑成、山本哲瑠 等）。",
                "- 今回受領した男子成績表PDFを全2ページ目視照合し、通過順位・区間順位、区間タイム、氏名を校正。",
                "- 佐敷A 1区は成績表どおり **德永蓮翔**（オーダー空欄）。",
                "- 金栗PROJECT A 2区の学年は成績表の印字どおり **0** を保持。",
                "- オーダー空欄の男子OPは成績表表記を採用（佐敷B 2区 **勝田逢斗**、下益城城南C 3区 **福村綱余**）。",
                "- OP は 3 区まで（4 区欄は黒塗り）。総合成績は 3 区通過を記載。",
                "- 西合志 4区 山田晄雅 は区間1位（9:04）。",
                "",
            ]
        )
    return "\n".join(lines)


def write_results_json() -> None:
    payload = {
        "event": results.EVENT,
        "women": results.WOMEN,
        "men": results.MEN,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _dual_write(text, "成績表.json")


def ensure_photos() -> None:
    CORPUS_MEET.mkdir(parents=True, exist_ok=True)
    for name in results.EVENT["sources"]:
        src = MEET_DIR / name
        if src.is_file():
            shutil.copy2(src, CORPUS_MEET / name)


def main() -> int:
    errs = validate_teams(results.WOMEN, "女子") + validate_teams(results.MEN, "男子")
    if errs:
        print("validation errors:")
        for e in errs:
            print(" ", e)
        return 1
    ensure_photos()
    write_results_json()
    _dual_write(render_results_md("女子", results.WOMEN, 2, 8), "女子成績表.md")
    _dual_write(render_results_md("男子", results.MEN, 3, 12), "男子成績表.md")
    changed = sync_nagomi_2026_calendar(women=results.WOMEN, men=results.MEN)
    print("wrote 女子成績表.md / 男子成績表.md / 成績表.json")
    print(f"calendar events.2026.yaml: {'updated' if changed else 'already up to date'}")
    print(f"women official={sum(1 for t in results.WOMEN if t.get('rank'))} OP={sum(1 for t in results.WOMEN if t.get('rank') is None)}")
    print(f"men official={sum(1 for t in results.MEN if t.get('rank'))} OP={sum(1 for t in results.MEN if t.get('rank') is None)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
