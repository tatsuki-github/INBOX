#!/usr/bin/env python3
"""Build full women transcript JSON (2020-2025) from board OCR + verified top-6 anchors."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.enrich import apply_board_ranks_from_computed
from lib.school_aliases import school_key
from validate_transcript import validate_year_transcript

TRANSCRIPTS = ROOT / "transcripts"
OCR_DIR = ROOT / "ocr_raw"
TOP6_PATH = ROOT / "women_top6_2012_2025.json"
SOURCES_PATH = ROOT / "sources/women_result_board_sources.json"

OCR_RAW: dict[str, str] = {}
LEG_COUNT = 5


def L(
    leg: int,
    name: str | None,
    grade: int | None,
    split: str | None,
    cumulative: str | None,
    passing_rank: int | None = None,
    split_rank: int | None = None,
    split_record: bool = False,
    status: str = "ok",
    raw_name_grade: str | None = None,
) -> dict:
    raw = raw_name_grade or (f"{name}{grade}" if name and grade else None)
    return {
        "leg": leg,
        "name": name,
        "grade": grade,
        "split": split,
        "cumulative": cumulative,
        "passing_rank": passing_rank,
        "split_rank": split_rank,
        "split_record": split_record,
        "status": status,
        "raw_name_grade": raw,
    }


def T(rank: int, team: str, total: str, legs: list[dict]) -> dict:
    return {"rank": rank, "team": team, "total": total, "legs": legs}


def merge_verified(teams: list[dict], verified: list[dict]) -> list[dict]:
    by_school = {school_key(t["team"]): t for t in verified}
    out: list[dict] = []
    for team in teams:
        key = school_key(team["team"])
        if key in by_school:
            v = by_school[key]
            merged_legs = []
            for i, leg_row in enumerate(team["legs"]):
                vl = v["legs"][i]
                merged = dict(leg_row)
                merged["name"] = vl["name"]
                merged["grade"] = vl["grade"]
                merged["split"] = vl["split"]
                merged["cumulative"] = vl["cumulative"]
                merged["raw_name_grade"] = f"{vl['name']}{vl['grade']}"
                merged_legs.append(merged)
            out.append(
                {
                    "rank": team["rank"],
                    "team": v["team"],
                    "total": v["total"],
                    "legs": merged_legs,
                }
            )
        else:
            out.append(team)
    return out


def save_ocr(year: int, ocr_text: str, drive_id: str, title: str) -> None:
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    path = OCR_DIR / f"{year}-女子.md"
    path.write_text(
        f"# 荒玉中体連駅伝 {year} 女子 — OCR raw\n\n"
        f"> Source: Google Drive `{drive_id}` ({title})\n"
        f"> Captured via Google Drive MCP `read_file_content`\n\n"
        f"## Raw OCR\n\n```\n{ocr_text.strip()}\n```\n",
        encoding="utf-8",
    )


SPLIT_RECORDS: dict[int, list[tuple[str, int]]] = {
    2025: [],  # no confirmed 区間新 on board
    2024: [],
    2023: [],
    2022: [("長洲", 1)],
    2021: [],
    2020: [("三加和", 1)],
}


def _apply_split_records(teams: list[dict], year: int) -> None:
    flags = {(school_key(s), leg) for s, leg in SPLIT_RECORDS.get(year, [])}
    for team in teams:
        key = school_key(team["team"])
        for leg_row in team["legs"]:
            leg_row["split_record"] = (key, leg_row["leg"]) in flags


def build_transcript(
    year: int,
    date: str,
    drive_id: str,
    teams: list[dict],
    ocr_notes: list[str],
    verified: list[dict],
) -> dict:
    merged = merge_verified(teams, verified)
    for team in merged:
        for leg_row in team["legs"]:
            leg_row["passing_rank"] = None
            leg_row["split_rank"] = None
    _apply_split_records(merged, year)
    enriched = apply_board_ranks_from_computed(merged, LEG_COUNT)
    all_notes = list(ocr_notes) + [
        "passing_rank/split_rank computed from times (board circled ranks unreadable in OCR)"
    ]
    entry = {
        "year": year,
        "gender": "女子",
        "date": date,
        "source_drive_id": drive_id,
        "teams": enriched,
        "ocr_notes": all_notes,
    }
    notes = validate_year_transcript(entry, year=year, gender="女子")
    allowed = {
        "total not monotonic: rank 14 (3109s) > rank 15 (2314s)",  # 2023 三加和 leg5 DNF
        "total not monotonic: rank 15 (3069s) > rank 16 (1661s)",  # 2022 三加和 legs 4-5 DNS
    }
    notes = [n for n in notes if n not in allowed]
    if notes:
        raise AssertionError(f"{year} validation failed:\n" + "\n".join(notes))
    return entry


# --- Board data (ranks 1..N); top-6 names/times replaced by verified anchors ---

BOARD_2025 = [
    T(1, "玉名", "41:58", [
        L(1, "川原芽吹", 2, "10:16", "10:16"),
        L(2, "内田愛祐", 3, "6:43", "16:59", 1, 1),
        L(3, "辻美空", 3, "6:59", "23:58", 1, 2),
        L(4, "内田千惺", 3, "6:56", "30:54", 1, 2),
        L(5, "水本星夏", 2, "11:04", "41:58", 1, 1),
    ]),
    T(2, "南関", "43:45", [
        L(1, "稗島葵音", 3, "11:00", "11:00", 2, 3),
        L(2, "米田美空", 2, "7:12", "18:12", 2, 4),
        L(3, "福山結衣", 1, "6:57", "25:09", 2, 1),
        L(4, "堀田稔々", 2, "7:24", "32:33", 2, 3),
        L(5, "平山果朋", 3, "11:12", "43:45", 2, 2),
    ]),
    T(3, "玉東", "44:24", [
        L(1, "坂村優奈", 3, "11:03", "11:03", 3, 4),
        L(2, "榎本佳澄", 2, "7:04", "18:07", 3, 3),
        L(3, "藤野四季", 3, "7:32", "25:39", 3, 5),
        L(4, "伊牟田百香", 3, "7:37", "33:16", 3, 4),
        L(5, "上村百叶", 2, "11:08", "44:24", 3, 3),
    ]),
    T(4, "長洲", "44:33", [
        L(1, "中村羽音", 2, "11:08", "11:08", 4, 5),
        L(2, "山川綾", 1, "7:03", "18:11", 4, 2),
        L(3, "濱北愛", 1, "7:13", "25:24", 4, 3),
        L(4, "村里唯花", 2, "7:53", "33:17", 4, 5),
        L(5, "猿渡愛梨", 2, "11:16", "44:33", 4, 4),
    ]),
    T(5, "荒尾三", "44:56", [
        L(1, "福島志帆", 3, "11:15", "11:15", 5, 6),
        L(2, "山道咲空", 1, "6:56", "18:11", 5, 1),
        L(3, "吉本琉音", 3, "7:33", "25:44", 5, 6),
        L(4, "佐藤妃葵", 3, "7:23", "33:07", 5, 1),
        L(5, "内野花笑", 2, "11:49", "44:56", 5, 5),
    ]),
    T(6, "合津", "45:09", [
        L(1, "松山杏海", 3, "10:33", "10:33", 6, 2),
        L(2, "宮本奈留", 3, "7:17", "17:50", 6, 5),
        L(3, "宮本奈英", 1, "7:46", "25:36", 6, 7),
        L(4, "池田結衣", 3, "7:44", "33:20", 6, 3),
        L(5, "中尾彩朱", 3, "11:49", "45:09", 6, 5),
    ]),
    T(7, "岱明", "45:22", [
        L(1, "村上咲稀", 2, "11:02", "11:02", 7, 7),
        L(2, "増岡里鋼", 1, "7:01", "18:03", 7, 6),
        L(3, "角田亜美", 1, "7:44", "25:47", 7, 4),
        L(4, "高田麻由", 2, "8:03", "33:50", 7, 6),
        L(5, "福島まりん", 2, "11:32", "45:22", 7, 6),
    ]),
    T(8, "荒尾海陽", "46:16", [
        L(1, "片山佳音", 3, "11:14", "11:14", 8, 8),
        L(2, "中西萌唯", 2, "7:11", "18:25", 8, 7),
        L(3, "時任幸菜", 2, "7:33", "25:58", 8, 8),
        L(4, "武重安奈", 3, "8:09", "34:07", 8, 7),
        L(5, "森本愛永", 3, "12:09", "46:16", 8, 7),
    ]),
    T(9, "菊水", "46:40", [
        L(1, "坂井優花", 3, "10:05", "10:05", 9, 1),
        L(2, "池田千絲", 3, "7:38", "17:43", 9, 8),
        L(3, "高集糖花", 3, "7:43", "25:26", 9, 2),
        L(4, "豆塚凛", 2, "7:41", "33:07", 9, 2),
        L(5, "上妻彩虹", 1, "13:33", "46:40", 9, 8),
    ]),
    T(10, "玉高附属", "46:55", [
        L(1, "鹿子木歩", 3, "10:16", "10:16", 10, 3),
        L(2, "三嶋悠里", 3, "8:39", "18:55", 10, 9),
        L(3, "小山にこり", 1, "8:15", "27:10", 10, 9),
        L(4, "佐伯伊織", 3, "9:15", "36:25", 10, 8),
        L(5, "大木莉子", 1, "10:30", "46:55", 10, 2),
    ]),
    T(11, "玉南", "47:13", [
        L(1, "田中小羽", 2, "12:00", "12:00", 11, 10),
        L(2, "倉本莉心", 2, "7:08", "19:08", 11, 10),
        L(3, "上田愛心", 2, "7:49", "26:57", 11, 10),
        L(4, "田原朱莉", 2, "8:04", "35:01", 11, 9),
        L(5, "木下和聯", 2, "12:12", "47:13", 11, 9),
    ]),
    T(12, "有明", "47:24", [
        L(1, "上土井輝", 2, "11:50", "11:50", 12, 9),
        L(2, "浙江杏梨", 2, "7:08", "18:58", 12, 11),
        L(3, "久保瑞花", 3, "7:46", "26:44", 12, 11),
        L(4, "书本琉遙", 2, "8:09", "34:53", 12, 10),
        L(5, "杉本琉遙", 2, "12:31", "47:24", 12, 10),
    ]),
    T(13, "三加和", "48:29", [
        L(1, "金澤朱里", 3, "11:55", "11:55", 13, 11),
        L(2, "居石華音", 1, "7:44", "19:39", 13, 12),
        L(3, "田上千万", 2, "7:53", "27:32", 13, 12),
        L(4, "高田奈和", 2, "8:18", "35:50", 13, 11),
        L(5, "大道優羽", 2, "12:39", "48:29", 13, 11),
    ]),
    T(14, "玉陵", "49:36", [
        L(1, "浦田咲希", 2, "10:18", "10:18", 14, 4),
        L(2, "竹原奈緒美", 2, "7:59", "18:17", 14, 13),
        L(3, "竹原晴美", 3, "8:39", "26:56", 14, 13),
        L(4, "荒木優里", 2, "8:33", "35:29", 14, 12),
        L(5, "花谷明優", 2, "14:07", "49:36", 14, 12),
    ]),
    T(15, "天水", "51:29", [
        L(1, "立川優", 3, "12:41", "12:41", 15, 12),
        L(2, "藤川萌依香", 3, "8:45", "21:26", 15, 14),
        L(3, "中村凛乃", 1, "8:30", "29:56", 15, 14),
        L(4, "池田有芙", 1, "8:57", "38:53", 15, 13),
        L(5, "竹原奈緒美", 2, "12:36", "51:29", 15, 13),
    ]),
]

# Additional years loaded from companion data modules in this directory.
_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))
from women_board_data_2020_2024 import BOARD_2020, BOARD_2021, BOARD_2022, BOARD_2023, BOARD_2024  # noqa: E402
from women_ocr_raw_2020_2025 import OCR_BY_YEAR  # noqa: E402

YEAR_CONFIG = {
    2025: ("2025-10-15", BOARD_2025, ["Names cross-checked with order sheet and verified top-6 anchors"]),
    2024: ("2024-10-18", BOARD_2024, ["Board date 令和6年10月18日; ranks 7-15 from result board OCR"]),
    2023: ("2023-10-18", BOARD_2023, ["全15校; rank15三加和 leg5 DNF (total=leg4累積)"]),
    2022: ("2022-10-19", BOARD_2022, ["長洲1区9:46 区間新; rank16三加和は3区のみ"]),
    2021: ("2021-10-20", BOARD_2021, ["16校参加"]),
    2020: ("2020-10-21", BOARD_2020, ["16校参加; 三加和1区9:55 区間新"]),
}


def main() -> None:
    top6 = json.loads(TOP6_PATH.read_text(encoding="utf-8"))
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    counts: dict[int, int] = {}

    for year, (date, board, notes) in YEAR_CONFIG.items():
        src = sources[str(year)]
        drive_id = src["id"]
        ocr_text = OCR_BY_YEAR[str(year)]
        save_ocr(year, ocr_text, drive_id, src["title"])
        verified = top6["years"][str(year)]["teams"]
        transcript = build_transcript(year, date, drive_id, board, notes, verified)
        out = TRANSCRIPTS / f"{year}-女子.json"
        out.write_text(json.dumps(transcript, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        counts[year] = len(transcript["teams"])
        print(f"wrote {out} ({counts[year]} teams)")

    print("team counts:", counts)


if __name__ == "__main__":
    main()
