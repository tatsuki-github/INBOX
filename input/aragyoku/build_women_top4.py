#!/usr/bin/env python3
"""Build women_top4_2012_2025.json and women_top4_athletes.csv from reconciled OCR."""

from __future__ import annotations

import csv
import json
import unicodedata
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
ROOT = OUT_DIR.parents[1]
CSV_RECONCILIATIONS = OUT_DIR / "women_top4_csv_reconciliations.json"
SCHOOL_ALIASES = {
    "荒尾第三": "荒尾三",
    "荒尾第四": "荒尾四",
}


def school_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").replace(" ", "").replace("　", "")
    for suffix in ("中学校", "中"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return SCHOOL_ALIASES.get(normalized, normalized)


def leg(n: int, name, grade, split: str, cumulative: str) -> dict:
    return {
        "leg": n,
        "name": name,
        "grade": grade,
        "split": split,
        "cumulative": cumulative,
    }


def team(rank: int, name: str, total: str, legs: list[dict]) -> dict:
    assert len(legs) == 5, (rank, name, len(legs))
    for i, L in enumerate(legs, 1):
        assert L["leg"] == i
    return {"rank": rank, "team": name, "total": total, "legs": legs}


def validate_year(year: str, entry: dict) -> list[str]:
    notes: list[str] = []
    teams = entry["teams"]
    assert len(teams) == 4, year
    for t in teams:
        assert len(t["legs"]) == 5
        prev = 0
        for L in t["legs"]:
            parts = L["cumulative"].split(":")
            cum = int(parts[0]) * 60 + int(parts[1])
            sp = L["split"].split(":")
            split_s = int(sp[0]) * 60 + int(sp[1])
            if prev and cum != prev + split_s:
                notes.append(
                    f"{year} {t['team']} leg{L['leg']}: cum {L['cumulative']} != prev+split"
                )
            prev = cum
        total_parts = t["total"].split(":")
        total_s = int(total_parts[0]) * 60 + int(total_parts[1])
        if prev != total_s:
            notes.append(f"{year} {t['team']}: final cum != total {t['total']}")
    return notes


def validate_csv_reconciliations(dataset: dict) -> None:
    audit = json.loads(CSV_RECONCILIATIONS.read_text(encoding="utf-8"))
    items = audit.get("items") or []
    expected = dataset["meta"]["verification"]["csv_reconciled_cells"]
    assert len(items) == expected, (len(items), expected)

    seen: set[tuple[int, int, int, str]] = set()
    rows_by_year: dict[int, list[dict[str, str]]] = {}

    def rows_for(year: int) -> list[dict[str, str]]:
        if year not in rows_by_year:
            source = (
                ROOT
                / "input/external/drive/personal/t-tsuchiyama/sb/by-year"
                / f"{year}-single-table.csv"
            )
            with source.open(encoding="utf-8-sig", newline="") as f:
                rows_by_year[year] = list(csv.DictReader(f))
        return rows_by_year[year]

    for item in items:
        key = (item["year"], item["rank"], item["leg"], item["field"])
        assert key not in seen, key
        seen.add(key)

        year_block = dataset["years"][str(item["year"])]
        selected_team = next(t for t in year_block["teams"] if t["rank"] == item["rank"])
        assert selected_team["team"] == item["team"], key
        athlete = next(L for L in selected_team["legs"] if L["leg"] == item["leg"])
        assert athlete[item["field"]] == item["to"], (key, athlete[item["field"]], item["to"])
        assert item.get("evidence"), key

        evidence_year = item.get("csv_year", item["year"])
        matches = [
            row
            for row in rows_for(evidence_year)
            if row.get("性別") == "女子"
            and row.get("カテゴリー") == "中学生"
            and row.get("名前") == athlete["name"]
            and school_key(item["team"]) == school_key(row.get("所属") or "")
            and row.get("学年") == str(item["csv_grade"])
            and "\ufffd" not in (row.get("名前") or "")
        ]
        assert len(matches) == item["csv_rows"], (key, len(matches), item["csv_rows"])

        if item["field"] == "name":
            old_matches = [
                row
                for row in rows_for(item["year"])
                if row.get("性別") == "女子"
                and row.get("カテゴリー") == "中学生"
                and row.get("名前") == item["from"]
                and school_key(item["team"]) == school_key(row.get("所属") or "")
                and row.get("学年") == str(athlete["grade"])
            ]
            assert not old_matches, (key, item["from"])


SOURCES = {
    "2025": "1-qackGYGwVuX6LikAryfiCLRmwgNVkWK",
    "2024": "1WDoNUHfL23mTudpm_-eUIbyeMn3EGtZg",
    "2023": "1FEhuWOmRsolozWeSkP4KPDTh68-MwpyV",
    "2022": "1LdY-YqIIx-57im7jTSTud5qzEBIm0hkA",
    "2021": "1t4xKLNQph4mcdKzdXj3NqGxmKG-Y8PPo",
    "2020": "1pbX4GwUm7_TebtyZZlMo4U8BHu_OPWmP",
    "2019": "1-m4jAOxnRixZLOkolym7idoBH7S6WBTN",
    "2018": "1SpSxcvlMeVJ_w9sV1D559ki112DVfvII",
    "2017": "1txCmMkoQMiayxCCaH9iUm5LyDcM-zZ5u",
    "2016": "1LhUyOckCQI2Ne3OEOIbQmMq4tZf5KzeR",
    "2015": "17gakFQA2vfltUyFgLkmy0FrWC8NnKdYv",
    "2013": "1YFXOLciLrpuMD8lvGVQ0oImq1uZLg1Ep",
    "2012": "1AONIAmzyv-oVZ8RI1x4gIOtBkQVNgEts",
}

data = {
    "meta": {
        "event": "玉名荒尾中体連駅伝",
        "gender": "女子",
        "legs": [
            {"leg": 1, "distance_km": 3.0},
            {"leg": 2, "distance_km": 1.855},
            {"leg": 3, "distance_km": 2.0},
            {"leg": 4, "distance_km": 2.0},
            {"leg": 5, "distance_km": 3.0},
        ],
        "note": (
            "Google Drive「荒玉駅伝歴代」の各年結果画像を、"
            "順位・校名・総合・選手名・学年・区間・累積の全セルで目視照合"
        ),
        "verification": {
            "method": "原画像との全セル目視照合",
            "verified_years": [
                2012,
                2013,
                2015,
                2016,
                2017,
                2018,
                2019,
                2020,
                2021,
                2022,
                2023,
                2024,
                2025,
            ],
            "cells_per_year": 92,
            "checked_cells": 1196,
            "unreadable_cells": 0,
            "corrected_cells": 9,
            "csv_reconciled_cells": 24,
            "csv_reconciliation_rule": (
                "同年度CSVの女子・中学生を学校・学年・継続年度・走力で照合し、"
                "一意に本人と判断できる表記はCSVを優先"
            ),
            "csv_reconciliation_source": (
                "input/aragyoku/women_top4_csv_reconciliations.json"
            ),
        },
    },
    "years": {},
    "missing_years": [2014],
}

# --- 2025 (order sheet + board; high) ---
data["years"]["2025"] = {
    "date": "2025-10-15",
    "source_drive_id": SOURCES["2025"],
    "teams": [
        team(
            1,
            "玉名",
            "41:58",
            [
                leg(1, "川原芽吹", 2, "10:16", "10:16"),
                leg(2, "内田愛祐", 3, "6:43", "16:59"),
                leg(3, "辻美空", 3, "6:59", "23:58"),
                leg(4, "内田千惺", 3, "6:56", "30:54"),
                leg(5, "水本星夏", 2, "11:04", "41:58"),
            ],
        ),
        team(
            2,
            "南関",
            "43:45",
            [
                leg(1, "稗島葵音", 3, "11:00", "11:00"),
                leg(2, "米田美空", 2, "7:12", "18:12"),
                leg(3, "福山結衣", 1, "6:57", "25:09"),
                leg(4, "堀田稔々", 2, "7:24", "32:33"),
                leg(5, "平山果朋", 3, "11:12", "43:45"),
            ],
        ),
        team(
            3,
            "玉東",
            "44:24",
            [
                leg(1, "坂村優奈", 3, "11:03", "11:03"),
                leg(2, "榎本佳澄", 2, "7:04", "18:07"),
                leg(3, "藤野四季", 3, "7:32", "25:39"),
                leg(4, "伊牟田百香", 3, "7:37", "33:16"),
                leg(5, "上村百叶", 2, "11:08", "44:24"),
            ],
        ),
        team(
            4,
            "長洲",
            "44:33",
            [
                leg(1, "中村羽音", 2, "11:08", "11:08"),
                leg(2, "山川綾", 1, "7:03", "18:11"),
                leg(3, "濱北愛", 1, "7:13", "25:24"),
                leg(4, "村里唯花", 2, "7:53", "33:17"),
                leg(5, "猿渡愛梨", 2, "11:16", "44:33"),
            ],
        ),
    ],
    "confidence": "verified",
    "ocr_notes": [
        "Names cross-checked with order sheet 1LKkiu1FBHQN7ANvHOB0xPWuR5UhT2q1T and totals anchors",
    ],
}

# --- 2024 ---
data["years"]["2024"] = {
    "date": "2024-10-18",
    "source_drive_id": SOURCES["2024"],
    "teams": [
        team(
            1,
            "南関",
            "42:25",
            [
                leg(1, "田畑結愛", 3, "11:01", "11:01"),
                leg(2, "米田美空", 1, "6:49", "17:50"),
                leg(3, "川下結音", 3, "7:02", "24:52"),
                leg(4, "稗島葵音", 2, "6:58", "31:50"),
                leg(5, "平山果朋", 2, "10:35", "42:25"),
            ],
        ),
        team(
            2,
            "荒尾三",
            "42:36",
            [
                leg(1, "内野花笑", 3, "10:55", "10:55"),
                leg(2, "庄山瑠那", 1, "6:25", "17:20"),
                leg(3, "山道咲空", 2, "7:09", "24:29"),
                leg(4, "吉本琉音", 2, "7:25", "31:54"),
                leg(5, "中尾美空", 3, "10:42", "42:36"),
            ],
        ),
        team(
            3,
            "玉名",
            "43:02",
            [
                leg(1, "東果凛", 3, "10:27", "10:27"),
                leg(2, "辻美空", 2, "6:51", "17:18"),
                leg(3, "川原芽吹", 1, "6:53", "24:11"),
                leg(4, "堺菜々美", 3, "7:32", "31:43"),
                leg(5, "内田愛祐", 2, "11:19", "43:02"),
            ],
        ),
        team(
            4,
            "長洲",
            "43:21",
            [
                leg(1, "福田みさ", 3, "10:17", "10:17"),
                leg(2, "中村羽音", 1, "6:43", "17:00"),
                leg(3, "猿渡愛梨", 1, "7:09", "24:09"),
                leg(4, "池田早希", 3, "7:44", "31:53"),
                leg(5, "中島美羽", 3, "11:28", "43:21"),
            ],
        ),
    ],
    "confidence": "verified",
    "ocr_notes": [
        "Board date 令和6年10月18日 (photo filename is 20241016)",
        "全92セルを原画像と目視照合済み",
    ],
}

# --- 2023 ---
data["years"]["2023"] = {
    "date": "2023-10-18",
    "source_drive_id": SOURCES["2023"],
    "teams": [
        team(
            1,
            "荒尾三",
            "42:32",
            [
                leg(1, "内野花笑", 2, "10:30", "10:30"),
                leg(2, "山道咲空", 1, "6:34", "17:04"),
                leg(3, "田尻明", 3, "7:16", "24:20"),
                leg(4, "柿本和花", 3, "7:34", "31:54"),
                leg(5, "中尾美空", 2, "10:38", "42:32"),
            ],
        ),
        team(
            2,
            "荒尾四",
            "42:45",
            [
                leg(1, "松山悠南", 3, "9:59", "9:59"),
                leg(2, "中尾彩朱", 2, "6:49", "16:48"),
                leg(3, "宮本奈英", 1, "7:35", "24:23"),
                leg(4, "髙田春陽", 2, "7:43", "32:06"),
                leg(5, "松山杏海", 1, "10:39", "42:45"),
            ],
        ),
        team(
            3,
            "玉名",
            "43:31",
            [
                leg(1, "東果凛", 2, "11:00", "11:00"),
                leg(2, "高木心菜", 3, "6:38", "17:38"),
                leg(3, "辻美空", 1, "7:15", "24:53"),
                leg(4, "三嶋悠里", 3, "7:20", "32:13"),
                leg(5, "西澤葵", 3, "11:18", "43:31"),
            ],
        ),
        team(
            4,
            "荒尾海陽",
            "43:55",
            [
                leg(1, "本山怜実", 3, "10:54", "10:54"),
                leg(2, "中西萌唯", 2, "7:07", "18:01"),
                leg(3, "片山佳音", 1, "7:11", "25:12"),
                leg(4, "時任幸菜", 2, "7:28", "32:40"),
                leg(5, "武重安奈", 3, "11:15", "43:55"),
            ],
        ),
    ],
    "confidence": "verified",
    "ocr_notes": [
        "全92セルを原画像と目視照合済み",
    ],
}

# --- 2022 ---
data["years"]["2022"] = {
    "date": "2022-10-19",
    "source_drive_id": SOURCES["2022"],
    "teams": [
        team(
            1,
            "長洲",
            "41:58",
            [
                leg(1, "西川侑里", 3, "9:46", "9:46"),
                leg(2, "濱口葵", 2, "7:05", "16:51"),
                leg(3, "藤本千尋", 3, "7:16", "24:07"),
                leg(4, "中島愛那", 1, "6:58", "31:05"),
                leg(5, "福田みさ", 1, "10:53", "41:58"),
            ],
        ),
        team(
            2,
            "荒尾四",
            "43:31",
            [
                leg(1, "松山悠南", 2, "10:09", "10:09"),
                leg(2, "中尾彩朱", 1, "7:14", "17:23"),
                leg(3, "上田歩", 1, "7:27", "24:50"),
                leg(4, "高田春陽", 1, "8:01", "32:51"),
                leg(5, "嘉富雅", 3, "10:40", "43:31"),
            ],
        ),
        team(
            3,
            "荒尾海陽",
            "43:59",
            [
                leg(1, "塚本実彩貴", 3, "11:36", "11:36"),
                leg(2, "杉本幸希", 2, "6:55", "18:31"),
                leg(3, "本山怜実", 2, "7:05", "25:36"),
                leg(4, "時任幸菜", 1, "7:35", "33:11"),
                leg(5, "武重安奈", 2, "10:48", "43:59"),
            ],
        ),
        team(
            4,
            "荒尾三",
            "44:17",
            [
                leg(1, "吉里紗和", 3, "10:32", "10:32"),
                leg(2, "松本りおな", 3, "6:56", "17:28"),
                leg(3, "内野花笑", 1, "7:06", "24:34"),
                leg(4, "柿本和花", 2, "7:29", "32:03"),
                leg(5, "田尻明", 2, "12:14", "44:17"),
            ],
        ),
    ],
    "confidence": "verified",
    "ocr_notes": [
        "長洲 1区 西川侑里 9:46 is also listed as course record on later boards",
        "荒尾四 4区 高田春陽 (OCR sometimes 春璃)",
    ],
}

# --- 2021 ---
data["years"]["2021"] = {
    "date": "2021-10-20",
    "source_drive_id": SOURCES["2021"],
    "teams": [
        team(
            1,
            "荒尾四",
            "43:11",
            [
                leg(1, "松山悠南", 1, "10:18", "10:18"),
                leg(2, "松山美結", 3, "6:23", "16:41"),
                leg(3, "島添真理", 3, "7:33", "24:14"),
                leg(4, "島添真実", 3, "7:55", "32:09"),
                leg(5, "嘉富雅", 2, "11:02", "43:11"),
            ],
        ),
        team(
            2,
            "荒尾三",
            "43:34",
            [
                leg(1, "吉里紗和", 2, "10:51", "10:51"),
                leg(2, "藤好心愛", 2, "6:57", "17:48"),
                leg(3, "松本りおな", 2, "7:12", "25:00"),
                leg(4, "飯川紗良", 3, "7:26", "32:26"),
                leg(5, "一木優咲", 3, "11:08", "43:34"),
            ],
        ),
        team(
            3,
            "荒尾海陽",
            "43:42",
            [
                leg(1, "本山怜実", 1, "10:30", "10:30"),
                leg(2, "杉本幸希", 1, "7:02", "17:32"),
                leg(3, "武重安奈", 1, "6:51", "24:23"),
                leg(4, "前田紗希", 3, "7:44", "32:07"),
                leg(5, "塚本実彩貴", 2, "11:35", "43:42"),
            ],
        ),
        team(
            4,
            "菊水",
            "43:58",
            [
                leg(1, "嶋田晴日", 3, "10:10", "10:10"),
                leg(2, "坂本葉音", 3, "6:22", "16:32"),
                leg(3, "越地優菜", 2, "7:35", "24:07"),
                leg(4, "牧野菜々香", 2, "8:31", "32:38"),
                leg(5, "近藤七海", 2, "11:20", "43:58"),
            ],
        ),
    ],
    "confidence": "verified",
    "ocr_notes": [
        "荒尾四 3–4区 島添 (OCR garbled as 瀦添)",
        "菊水 4区 牧野菜々香: 香/番 OCR variants",
    ],
}

# --- 2020 ---
data["years"]["2020"] = {
    "date": "2020-10-21",
    "source_drive_id": SOURCES["2020"],
    "teams": [
        team(
            1,
            "玉名",
            "42:56",
            [
                leg(1, "片山美璃愛", 2, "10:30", "10:30"),
                leg(2, "平井咲良", 3, "6:22", "16:52"),
                leg(3, "峠美咲希", 3, "7:04", "23:56"),
                leg(4, "徳永理子", 2, "7:31", "31:27"),
                leg(5, "藤戸花菜", 3, "11:29", "42:56"),
            ],
        ),
        team(
            2,
            "荒尾三",
            "43:49",
            [
                leg(1, "藤田菜々美", 3, "10:43", "10:43"),
                leg(2, "吉里紗和", 1, "7:02", "17:45"),
                leg(3, "一木優咲", 2, "6:57", "24:42"),
                leg(4, "安田咲和", 3, "7:41", "32:23"),
                leg(5, "飯川紗良", 2, "11:26", "43:49"),
            ],
        ),
        team(
            3,
            "長洲",
            "44:21",
            [
                leg(1, "西川侑里", 1, "9:58", "9:58"),
                leg(2, "横尾悠", 2, "6:47", "16:45"),
                leg(3, "高松春花", 1, "7:42", "24:27"),
                leg(4, "草野しずく", 3, "7:42", "32:09"),
                leg(5, "近藤楓", 3, "12:12", "44:21"),
            ],
        ),
        team(
            4,
            "菊水",
            "44:54",
            [
                leg(1, "柴尾香澄", 3, "10:22", "10:22"),
                leg(2, "嶋田晴日", 2, "6:24", "16:46"),
                leg(3, "石原杏南", 1, "8:10", "24:56"),
                leg(4, "佐藤杏", 1, "7:52", "32:48"),
                leg(5, "坂本葉音", 2, "12:06", "44:54"),
            ],
        ),
    ],
    "confidence": "verified",
    "ocr_notes": ["全92セルを原画像と目視照合済み"],
}

# --- 2019 ---
data["years"]["2019"] = {
    "date": "2019-11-16",
    "source_drive_id": SOURCES["2019"],
    "teams": [
        team(
            1,
            "玉名",
            "41:31",
            [
                leg(1, "堀愛菜", 3, "10:05", "10:05"),
                leg(2, "松本明城", 3, "6:15", "16:20"),
                leg(3, "田上未来", 3, "6:44", "23:04"),
                leg(4, "山田侑奈", 2, "7:18", "30:22"),
                leg(5, "峠美咲希", 2, "11:09", "41:31"),
            ],
        ),
        team(
            2,
            "菊水",
            "42:09",
            [
                leg(1, "柴尾香澄", 2, "10:43", "10:43"),
                leg(2, "嶋田晴日", 1, "6:34", "17:17"),
                leg(3, "藤本喬子", 3, "7:05", "24:22"),
                leg(4, "坂本葉音", 1, "7:24", "31:46"),
                leg(5, "坂本華", 3, "10:23", "42:09"),
            ],
        ),
        team(
            3,
            "腹栄",
            "43:59",
            [
                leg(1, "植原華望", 2, "10:42", "10:42"),
                leg(2, "田川華妃", 3, "7:05", "17:47"),
                leg(3, "田上遥", 3, "7:03", "24:50"),
                leg(4, "荒木心音", 2, "7:21", "32:11"),
                leg(5, "古賀葵", 3, "11:48", "43:59"),
            ],
        ),
        team(
            4,
            "荒尾三",
            "44:24",
            [
                leg(1, "沖愛凜", 3, "11:15", "11:15"),
                leg(2, "佐藤ちゆら", 2, "6:50", "18:05"),
                leg(3, "一木優咲", 1, "7:07", "25:12"),
                leg(4, "安田咲和", 2, "7:34", "32:46"),
                leg(5, "藤田菜々美", 2, "11:38", "44:24"),
            ],
        ),
    ],
    "confidence": "verified",
    "ocr_notes": [
        "Board date read as 令和元年11月16日 (some OCR said 11/14)",
        "腹栄 is historical school name (not in modern short-name list)",
        "全92セルを原画像と目視照合済み",
    ],
}

# --- 2018 ---
data["years"]["2018"] = {
    "date": "2018-10-17",
    "source_drive_id": SOURCES["2018"],
    "teams": [
        team(
            1,
            "玉名",
            "41:46",
            [
                leg(1, "後藤凜", 2, "10:17", "10:17"),
                leg(2, "松本明城", 2, "6:26", "16:43"),
                leg(3, "濱本麻那", 2, "6:52", "23:35"),
                leg(4, "本田結里", 1, "7:25", "31:00"),
                leg(5, "田上未来", 2, "10:46", "41:46"),
            ],
        ),
        team(
            2,
            "菊水",
            "42:22",
            [
                leg(1, "坂本華", 2, "10:25", "10:25"),
                leg(2, "池田愛海", 2, "6:40", "17:05"),
                leg(3, "柴尾香澄", 1, "7:02", "24:07"),
                leg(4, "前淵あかり", 2, "7:24", "31:31"),
                leg(5, "藤本喬子", 2, "10:51", "42:22"),
            ],
        ),
        team(
            3,
            "腹栄",
            "43:00",
            [
                leg(1, "荒木心音", 1, "11:04", "11:04"),
                leg(2, "前田葵侑", 2, "6:42", "17:46"),
                leg(3, "田上遥", 2, "7:01", "24:47"),
                leg(4, "植原華望", 1, "7:07", "31:54"),
                leg(5, "古賀葵", 2, "11:06", "43:00"),
            ],
        ),
        team(
            4,
            "荒尾四",
            "43:31",
            [
                leg(1, "前田琳香", 2, "10:12", "10:12"),
                leg(2, "大江莉奈", 3, "7:18", "17:30"),
                leg(3, "藤本佑菜", 3, "7:22", "24:52"),
                leg(4, "前田紗歩", 3, "7:56", "32:48"),
                leg(5, "小嶋弥渚", 3, "10:43", "43:31"),
            ],
        ),
    ],
    "confidence": "verified",
    "ocr_notes": [
        "全92セルを原画像と目視照合済み",
        "腹栄 is historical school name",
    ],
}

# --- 2017 ---
data["years"]["2017"] = {
    "date": "2017-10-18",
    "source_drive_id": SOURCES["2017"],
    "teams": [
        team(
            1,
            "玉名",
            "41:21",
            [
                leg(1, "清田真帆", 3, "10:15", "10:15"),
                leg(2, "萩尾花月", 3, "6:15", "16:30"),
                leg(3, "松本明城", 1, "6:58", "23:28"),
                leg(4, "堀愛菜", 1, "7:07", "30:35"),
                leg(5, "中尾比菜", 3, "10:46", "41:21"),
            ],
        ),
        team(
            2,
            "荒尾三",
            "42:02",
            [
                leg(1, "大中千尋", 3, "10:09", "10:09"),
                leg(2, "沖愛凜", 1, "6:25", "16:34"),
                leg(3, "堀秋璃", 3, "7:04", "23:38"),
                leg(4, "荒川夏凜", 3, "7:24", "31:02"),
                leg(5, "浦浜実里", 3, "11:00", "42:02"),
            ],
        ),
        team(
            3,
            "菊水",
            "43:08",
            [
                leg(1, "坂井陽香", 3, "11:00", "11:00"),
                leg(2, "坂本華", 1, "6:29", "17:29"),
                leg(3, "藤本喬子", 1, "7:05", "24:34"),
                leg(4, "坂本あずみ", 3, "7:27", "32:01"),
                leg(5, "柴尾知美", 2, "11:07", "43:08"),
            ],
        ),
        team(
            4,
            "岱明",
            "43:29",
            [
                leg(1, "前田優花", 1, "10:57", "10:57"),
                leg(2, "辻湖羽来", 3, "6:41", "17:38"),
                leg(3, "榎本妃恵", 3, "7:15", "24:53"),
                leg(4, "土山静里佳", 2, "7:27", "32:20"),
                leg(5, "三村奈々", 3, "11:09", "43:29"),
            ],
        ),
    ],
    "confidence": "verified",
    "ocr_notes": [
        "岱明 4位 43:29 matches Notion 岱明 metadata",
        "全92セルを原画像と目視照合済み",
    ],
}

# --- 2016 ---
data["years"]["2016"] = {
    "date": "2016-10-19",
    "source_drive_id": SOURCES["2016"],
    "teams": [
        team(
            1,
            "荒尾三",
            "40:59",
            [
                leg(1, "大中千尋", 2, "10:10", "10:10"),
                leg(2, "堀秋璃", 2, "6:33", "16:43"),
                leg(3, "荒川夏凜", 2, "6:55", "23:38"),
                leg(4, "浦浜実里", 2, "6:42", "30:20"),
                leg(5, "牧野颯姫", 3, "10:39", "40:59"),
            ],
        ),
        team(
            2,
            "玉名",
            "41:10",
            [
                leg(1, "濱崎菜", 3, "10:22", "10:22"),
                leg(2, "宮本花穂", 3, "6:31", "16:53"),
                leg(3, "中尾比菜", 2, "6:46", "23:39"),
                leg(4, "清田真帆", 2, "6:48", "30:27"),
                leg(5, "早野真菜", 3, "10:43", "41:10"),
            ],
        ),
        team(
            3,
            "南関",
            "41:43",
            [
                leg(1, "津留萌花", 3, "10:35", "10:35"),
                leg(2, "門田咲耶", 1, "6:31", "17:06"),
                leg(3, "島﨑乃々佳", 3, "6:55", "24:01"),
                leg(4, "高椋琳菜", 3, "7:08", "31:09"),
                leg(5, "原賀藍実", 3, "10:34", "41:43"),
            ],
        ),
        team(
            4,
            "岱明",
            "43:02",
            [
                leg(1, "田上真愛", 3, "10:29", "10:29"),
                leg(2, "土山静里佳", 1, "6:35", "17:04"),
                leg(3, "東華菜", 3, "7:04", "24:08"),
                leg(4, "辻湖羽来", 2, "7:15", "31:23"),
                leg(5, "三村奈々", 2, "11:39", "43:02"),
            ],
        ),
    ],
    "confidence": "verified",
    "ocr_notes": [
        "荒尾三 4区 浦浜実里 6:42 became later course record",
        "岱明 4位 43:02 matches Notion metadata",
    ],
}

# --- 2015 ---
data["years"]["2015"] = {
    "date": "2015-10-21",
    "source_drive_id": SOURCES["2015"],
    "teams": [
        team(
            1,
            "玉名",
            "41:31",
            [
                leg(1, "關知夏子", 3, "10:14", "10:14"),
                leg(2, "田上綾乃", 3, "6:26", "16:40"),
                leg(3, "笠井菜央", 3, "6:54", "23:34"),
                leg(4, "清田真帆", 1, "7:06", "30:40"),
                leg(5, "塩山桃花", 2, "10:51", "41:31"),
            ],
        ),
        team(
            2,
            "荒尾三",
            "42:39",
            [
                leg(1, "大中千尋", 1, "10:23", "10:23"),
                leg(2, "荒川夏凜", 1, "6:45", "17:08"),
                leg(3, "藤本実百", 2, "6:59", "24:07"),
                leg(4, "石橋美優", 1, "7:20", "31:27"),
                leg(5, "牧野颯姫", 2, "11:12", "42:39"),
            ],
        ),
        team(
            3,
            "南関",
            "43:17",
            [
                leg(1, "原賀藍実", 2, "11:00", "11:00"),
                leg(2, "高椋琳菜", 2, "6:59", "17:59"),
                leg(3, "津留萌花", 2, "6:45", "24:44"),
                leg(4, "川上悠花", 3, "7:33", "32:17"),
                leg(5, "島﨑乃々佳", 2, "11:00", "43:17"),
            ],
        ),
        team(
            4,
            "岱明",
            "43:36",
            [
                leg(1, "東華菜", 2, "10:41", "10:41"),
                leg(2, "田上真愛", 2, "6:51", "17:32"),
                leg(3, "下田紗知", 3, "7:10", "24:42"),
                leg(4, "宮内果歩", 3, "7:36", "32:18"),
                leg(5, "三村奈々", 1, "11:18", "43:36"),
            ],
        ),
    ],
    "confidence": "verified",
    "ocr_notes": [
        "岱明 4位 43:36 matches Notion metadata",
        "玉名 1区 關知夏子: 同年度CSV表記を優先（画像では先頭漢字が一部欠けている）",
    ],
}

# --- 2013 ---
data["years"]["2013"] = {
    "date": None,
    "source_drive_id": SOURCES["2013"],
    "teams": [
        team(
            1,
            "玉名",
            "41:03",
            [
                leg(1, "森澤彩乃", 3, "10:09", "10:09"),
                leg(2, "磧結里", 3, "6:26", "16:35"),
                leg(3, "塩山莉央", 3, "6:53", "23:28"),
                leg(4, "川本和", 3, "7:09", "30:37"),
                leg(5, "上戸真鈴", 3, "10:26", "41:03"),
            ],
        ),
        team(
            2,
            "荒尾海陽",
            "42:42",
            [
                leg(1, "東美瑠希", 3, "10:41", "10:41"),
                leg(2, "吉本絵理", 3, "6:47", "17:28"),
                leg(3, "吉岡愛馨", 2, "6:41", "24:09"),
                leg(4, "伊木田優衣", 3, "7:42", "31:51"),
                leg(5, "西川二千花", 2, "10:51", "42:42"),
            ],
        ),
        team(
            3,
            "南関",
            "42:51",
            [
                leg(1, "嶋永有紗", 3, "10:33", "10:33"),
                leg(2, "原有紀", 3, "6:38", "17:11"),
                leg(3, "武田彩花", 2, "6:53", "24:04"),
                leg(4, "松本佑夏", 2, "7:33", "31:37"),
                leg(5, "嶋村里恩", 2, "11:14", "42:51"),
            ],
        ),
        team(
            4,
            "荒尾三",
            "42:51",
            [
                leg(1, "開琴美", 2, "10:40", "10:40"),
                leg(2, "杉山恵菜", 2, "6:47", "17:27"),
                leg(3, "中村真央", 3, "7:12", "24:39"),
                leg(4, "栗原美瑞希", 3, "7:25", "32:04"),
                leg(5, "森綴美香", 2, "10:47", "42:51"),
            ],
        ),
    ],
    "confidence": "verified",
    "ocr_notes": [
        "Printed date fields blank on board photo",
        "南関 and 荒尾三 both 42:51; board lists 南関 as 3rd",
        "全92セルを原画像と目視照合済み",
    ],
}

# --- 2012 ---
data["years"]["2012"] = {
    "date": None,
    "source_drive_id": SOURCES["2012"],
    "teams": [
        team(
            1,
            "玉名",
            "41:07",
            [
                leg(1, "猿渡睦月", 2, "10:18", "10:18"),
                leg(2, "森澤彩乃", 2, "6:18", "16:36"),
                leg(3, "川本和", 2, "6:46", "23:22"),
                leg(4, "塩山莉央", 2, "7:09", "30:31"),
                leg(5, "上戸真鈴", 2, "10:36", "41:07"),
            ],
        ),
        team(
            2,
            "岱明",
            "42:41",
            [
                leg(1, "大道志歩", 1, "10:17", "10:17"),
                leg(2, "前田明日香", 1, "6:43", "17:00"),
                leg(3, "中川菜月", 1, "7:12", "24:12"),
                leg(4, "鎌田愛貴", 2, "7:22", "31:34"),
                leg(5, "田上愛佳", 3, "11:07", "42:41"),
            ],
        ),
        team(
            3,
            "荒尾海陽",
            "42:59",
            [
                leg(1, "東美瑠希", 2, "10:45", "10:45"),
                leg(2, "吉本絵理", 2, "6:55", "17:40"),
                leg(3, "吉岡愛希", 2, "6:51", "24:31"),
                leg(4, "谷本アンナ", 3, "7:17", "31:48"),
                leg(5, "伊木田優衣", 2, "11:11", "42:59"),
            ],
        ),
        team(
            4,
            "南関",
            "43:24",
            [
                leg(1, "嶋永有紗", 2, "10:21", "10:21"),
                leg(2, "津留有希子", 3, "7:13", "17:34"),
                leg(3, "嶋村里恩", 1, "6:56", "24:30"),
                leg(4, "武田彩花", 1, "7:16", "31:46"),
                leg(5, "原有紀", 2, "11:38", "43:24"),
            ],
        ),
    ],
    "confidence": "verified",
    "ocr_notes": [
        "Printed date fields blank on board photo",
        "岱明 2位 42:41 matches Notion metadata",
        "全92セルを原画像と目視照合済み",
    ],
}


def main() -> None:
    all_notes: list[str] = []
    for year, entry in data["years"].items():
        all_notes.extend(validate_year(year, entry))
    if all_notes:
        raise SystemExit("validation failed:\n" + "\n".join(all_notes))
    validate_csv_reconciliations(data)

    json_path = OUT_DIR / "women_top4_2012_2025.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_path = OUT_DIR / "women_top4_athletes.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(
            [
                "year",
                "rank",
                "team",
                "total",
                "leg",
                "name",
                "grade",
                "split",
                "cumulative",
                "source_drive_id",
            ]
        )
        for year in sorted(data["years"].keys(), reverse=True):
            entry = data["years"][year]
            sid = entry["source_drive_id"]
            for t in entry["teams"]:
                for L in t["legs"]:
                    w.writerow(
                        [
                            year,
                            t["rank"],
                            t["team"],
                            t["total"],
                            L["leg"],
                            "" if L["name"] is None else L["name"],
                            "" if L["grade"] is None else L["grade"],
                            L["split"],
                            L["cumulative"],
                            sid,
                        ]
                    )

    # summary
    conf = {y: data["years"][y]["confidence"] for y in sorted(data["years"])}
    print("wrote", json_path)
    print("wrote", csv_path)
    print("years", len(data["years"]), "missing", data["missing_years"])
    print("confidence", conf)
    print("athletes", sum(20 for _ in data["years"]))


if __name__ == "__main__":
    main()
