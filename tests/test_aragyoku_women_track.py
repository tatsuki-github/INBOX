#!/usr/bin/env python3
"""荒玉女子駅伝トラック突合のスモークテスト。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from aragyoku_women_track import (  # noqa: E402
    build_joined,
    format_seconds,
    norm_name,
    parse_time_to_seconds,
    pick_recent,
    pick_sb,
    school_overlap,
    seasons_for_ekiden_year,
)


def test_time_helpers() -> None:
    assert parse_time_to_seconds("10:16") == 616
    assert parse_time_to_seconds("2:31.44") == 151.44
    assert format_seconds(616) == "10:16"
    assert norm_name("内田　愛祐") == "内田愛祐"
    assert school_overlap("玉名", "玉名中")
    assert seasons_for_ekiden_year(2025) == ["2025"]


def test_track_records_never_leak_across_years() -> None:
    records = [
        {
            "event": "1500m",
            "season": "2024",
            "seconds": 300.0,
            "mark": "5:00.00",
            "is_sb": True,
            "is_aggregate": False,
            "meet_date": "2024/06/01",
        },
        {
            "event": "1500m",
            "season": "2025",
            "seconds": 310.0,
            "mark": "5:10.00",
            "is_sb": True,
            "is_aggregate": False,
            "meet_date": "2025/06/01",
        },
    ]
    assert pick_sb(records, ["2025"], "1500m")["mark"] == "5:10.00"
    assert pick_recent(records, ["2025"], "1500m")["mark"] == "5:10.00"
    assert pick_sb(records, ["2023"], "1500m") is None
    assert pick_recent(records, ["2023"], "1500m") is None


def test_aggregate_sb_is_not_reported_as_recent_record() -> None:
    records = [
        {
            "event": "800m",
            "season": "2025",
            "seconds": 150.0,
            "mark": "2:30.00",
            "is_sb": True,
            "is_aggregate": True,
            "meet_date": None,
        }
    ]
    assert pick_sb(records, ["2025"], "800m")["mark"] == "2:30.00"
    assert pick_recent(records, ["2025"], "800m") is None


def test_build_joined_has_2025_top4() -> None:
    data = build_joined()
    assert data["meta"]["stats"]["athletes"] == 260
    assert 2014 in data["meta"]["missing_years"]
    assert all(y["source_confidence"] == "verified" for y in data["years"])
    y2025 = next(y for y in data["years"] if y["year"] == 2025)
    assert len(y2025["teams"]) == 4
    first = y2025["teams"][0]
    assert first["school"] == "玉名"
    assert first["total_mark"] == "41:58"
    names = [a["name"] for a in first["athletes"]]
    assert names == ["川原芽吹", "内田愛祐", "辻美空", "内田千惺", "水本星夏"]
    assert y2025["source_confidence"] == "verified"
    # 近年は一定数ヒットし、年度外記録は混入しない
    assert data["meta"]["stats"]["with_any_track"] == 29
    for year_block in data["years"]:
        year = str(year_block["year"])
        for team in year_block["teams"]:
            for athlete in team["athletes"]:
                for event in athlete["track_events"].values():
                    for key in ("sb", "recent"):
                        record = event.get(key)
                        if record and record.get("season"):
                            assert record["season"] == year


def test_corrected_transcriptions_are_preserved() -> None:
    data = build_joined()

    def athlete(year: int, rank: int, leg: int) -> dict:
        year_block = next(y for y in data["years"] if y["year"] == year)
        team = next(t for t in year_block["teams"] if t["rank"] == rank)
        return next(a for a in team["athletes"] if a["leg"] == leg)

    assert athlete(2012, 3, 2)["name"] == "吉本絵理"
    assert athlete(2012, 3, 3)["name"] == "吉岡愛希"
    assert athlete(2012, 4, 2)["grade"] == 3
    assert athlete(2015, 1, 3)["name"] == "笠井菜央"
    assert athlete(2018, 1, 3)["name"] == "濱本麻那"
    assert athlete(2018, 1, 5)["name"] == "坂上未来"
    assert athlete(2019, 1, 4)["grade"] == 2
    assert athlete(2020, 1, 1)["name"] == "片山美璃愛"
    assert athlete(2022, 2, 2)["name"] == "中尾彩朱"


def test_joined_artifact_exists() -> None:
    path = ROOT / "out/analysis/aragyoku_women_track_joined.json"
    assert path.exists(), "run scripts/aragyoku_women_track.py first"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["years"]


if __name__ == "__main__":
    test_time_helpers()
    test_track_records_never_leak_across_years()
    test_aggregate_sb_is_not_reported_as_recent_record()
    test_build_joined_has_2025_top4()
    test_corrected_transcriptions_are_preserved()
    test_joined_artifact_exists()
    print("ok")
