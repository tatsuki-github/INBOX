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
    school_overlap,
    seasons_for_ekiden_year,
)


def test_time_helpers() -> None:
    assert parse_time_to_seconds("10:16") == 616
    assert parse_time_to_seconds("2:31.44") == 151.44
    assert format_seconds(616) == "10:16"
    assert norm_name("内田　愛祐") == "内田愛祐"
    assert school_overlap("玉名", "玉名中")
    assert seasons_for_ekiden_year(2025)[0] == "2026"


def test_build_joined_has_2025_top4() -> None:
    data = build_joined()
    assert data["meta"]["stats"]["athletes"] == 260
    assert 2014 in data["meta"]["missing_years"]
    y2025 = next(y for y in data["years"] if y["year"] == 2025)
    assert len(y2025["teams"]) == 4
    first = y2025["teams"][0]
    assert first["school"] == "玉名"
    assert first["total_mark"] == "41:58"
    names = [a["name"] for a in first["athletes"]]
    assert names == ["川原芽吹", "内田愛祐", "辻美空", "内田千惺", "水本星夏"]
    # 近年は一定数ヒットする
    assert data["meta"]["stats"]["with_any_track"] >= 40


def test_joined_artifact_exists() -> None:
    path = ROOT / "out/analysis/aragyoku_women_track_joined.json"
    assert path.exists(), "run scripts/aragyoku_women_track.py first"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["years"]


if __name__ == "__main__":
    test_time_helpers()
    test_build_joined_has_2025_top4()
    test_joined_artifact_exists()
    print("ok")
