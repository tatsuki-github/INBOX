#!/usr/bin/env python3
"""荒玉女子駅伝トラック突合のスモークテスト。"""

from __future__ import annotations

import json
import runpy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from aragyoku_women_track import (  # noqa: E402
    TRACK_EVENTS,
    build_joined,
    fact_check_joined,
    filter_records_for_athlete,
    format_seconds,
    is_club_affiliation,
    load_by_year_json,
    load_notion_rows,
    load_wide_like_csv,
    norm_name,
    norm_school,
    parse_time_to_seconds,
    parse_truthy,
    pick_recent,
    pick_sb,
    school_overlap,
    seasons_for_ekiden_year,
    validate_record_seconds,
)
from aragyoku_women_pdf import (  # noqa: E402
    athlete_rows,
    build_pdf,
    build_styles,
    link_para,
    mark_with_link,
    register_font,
    shorten_url,
)


def test_time_helpers() -> None:
    assert parse_time_to_seconds("10:16") == 616
    assert parse_time_to_seconds("2:31.44") == 151.44
    assert parse_time_to_seconds("1:60") is None
    assert parse_time_to_seconds("1:02:99") is None
    assert parse_time_to_seconds("0") is None
    assert parse_time_to_seconds("999999999999999999999999999") is None
    assert format_seconds(616) == "10:16"
    assert format_seconds(-1) is None
    assert format_seconds(float("nan")) is None
    assert format_seconds(float("inf")) is None
    assert norm_name("内田　愛祐") == "内田愛祐"
    assert school_overlap("玉名", "玉名中")
    assert school_overlap("玉名", "玉名(玉)")
    assert school_overlap("玉名", "ﾀﾏﾅﾁｭｳ玉名中")
    assert norm_school("ﾀﾏﾅﾁｭｳ玉名中") == "玉名"
    assert school_overlap("荒尾海陽", "荒尾海陽(玉)")
    assert is_club_affiliation("ＮＪＡＣ", "長洲")
    assert school_overlap("荒尾四", "荒尾第四中")
    assert not school_overlap("荒尾三", "荒尾四")
    assert not school_overlap("玉東", "玉東クラブ")
    assert not school_overlap("長洲", "長洲JRC")
    assert is_club_affiliation("ATRC", "長洲")
    assert is_club_affiliation("NJAC", "長洲")
    assert is_club_affiliation("長洲JRC", "長洲")
    assert is_club_affiliation("金栗PROJECT", "玉名")
    assert not is_club_affiliation("菊水", "玉名")
    assert not is_club_affiliation("玉名", "玉名")
    assert not school_overlap("玉名", "")
    assert seasons_for_ekiden_year(2025) == ["2025"]
    assert parse_truthy("__YES__")
    assert not parse_truthy("__NO__")
    assert validate_record_seconds("2:30.00", 150, "test") == 150
    try:
        validate_record_seconds("1:99", 150, "test")
    except ValueError as exc:
        assert "invalid track mark" in str(exc)
    else:
        raise AssertionError("invalid textual mark must fail")
    try:
        validate_record_seconds("2:30.00", 151, "test")
    except ValueError as exc:
        assert "mismatch" in str(exc)
    else:
        raise AssertionError("mark/seconds mismatch must fail")


def test_invalid_track_source_row_fails_fast() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.csv"
        path.write_text(
            "性別,名前,所属,800mSB\n女子,不正記録,玉名中,1:99\n",
            encoding="utf-8",
        )
        try:
            load_wide_like_csv(path, "test", "2025")
        except ValueError as exc:
            assert "不正記録" in str(exc)
        else:
            raise AssertionError("invalid source row must fail")

        empty_dir = Path(tmp) / "empty"
        empty_dir.mkdir()
        try:
            load_by_year_json(empty_dir)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("missing yearly sources must fail")

        yearly_dir = Path(tmp) / "yearly"
        yearly_dir.mkdir()
        for year in range(2012, 2027):
            (yearly_dir / f"{year}-sb-adopted.json").write_text("[]", encoding="utf-8")
        (yearly_dir / "2025-sb-adopted.json").write_text("{", encoding="utf-8")
        try:
            load_by_year_json(yearly_dir)
        except ValueError as exc:
            assert "invalid track JSON" in str(exc)
        else:
            raise AssertionError("invalid yearly JSON must fail")

        notion_path = Path(tmp) / "notion.json"
        notion_path.write_text(
            json.dumps(
                [
                    {
                        "性別": "女子",
                        "距離": "800m",
                        "名前": "不一致記録",
                        "記録": "2:30.00",
                        "記録秒": 151,
                        "SB採用": "__YES__",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        try:
            load_notion_rows([(notion_path, "2025", "legacy")])
        except ValueError as exc:
            assert "mismatch" in str(exc)
        else:
            raise AssertionError("Notion mark/seconds mismatch must fail")


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


def test_non_adopted_record_is_not_reported_as_sb() -> None:
    records = [
        {
            "event": "800m",
            "season": "2025",
            "seconds": 140.0,
            "mark": "2:20.00",
            "is_sb": False,
            "is_aggregate": False,
            "meet_date": "2025/12/01",
        },
        {
            "event": "800m",
            "season": "2025",
            "seconds": 150.0,
            "mark": "2:30.00",
            "is_sb": True,
            "is_aggregate": False,
            "meet_date": "2025/06/01",
        },
    ]
    assert pick_sb(records, ["2025"], "800m")["mark"] == "2:30.00"
    assert pick_recent(records, ["2025"], "800m")["mark"] == "2:20.00"


def test_same_year_csv_is_preferred_over_legacy_aggregate() -> None:
    records = [
        {
            "source": "wide_sb",
            "event": "1500m",
            "season": "2025",
            "seconds": 300.0,
            "mark": "5:00.00",
            "school": "玉名中",
            "grade": "",
            "is_sb": True,
        },
        {
            "source": "by_year_2025",
            "event": "1500m",
            "season": "2025",
            "seconds": 301.0,
            "mark": "5:01.00",
            "school": "玉名中",
            "grade": "3",
            "is_sb": True,
        },
    ]
    selected = pick_sb(records, ["2025"], "1500m")
    assert selected is not None
    assert selected["source"] == "by_year_2025"
    assert selected["grade"] == "3"


def test_grade_evidence_excludes_same_name_different_athlete() -> None:
    records = [
        {
            "season": "2024",
            "school": "玉名中",
            "grade": "2",
            "event": "800m",
        },
        {
            "season": "2025",
            "school": "玉名中",
            "grade": "",
            "event": "800m",
        },
    ]
    assert filter_records_for_athlete(records, 2024, "玉名", 1) == []
    assert filter_records_for_athlete(records, 2025, "玉名", 2) == []
    assert len(filter_records_for_athlete(records, 2025, "玉名", 3)) == 1

    club_only = [
        {
            "season": "2025",
            "school": "玉名クラブ",
            "grade": "3",
            "event": "800m",
        }
    ]
    assert len(filter_records_for_athlete(club_only, 2025, "玉名", 3)) == 1

    other_school = [
        {
            "season": "2025",
            "school": "菊水",
            "grade": "3",
            "event": "800m",
        }
    ]
    assert filter_records_for_athlete(other_school, 2025, "玉名", 3) == []


def test_club_affiliation_records_are_linked_for_same_name() -> None:
    atrc = [
        {
            "season": "2025",
            "school": "ATRC",
            "grade": "2",
            "event": "800m",
            "mark": "2:37.17",
        },
        {
            "season": "2025",
            "school": "ATRC",
            "grade": "2",
            "event": "1500m",
            "mark": "5:16.18",
        },
    ]
    assert len(filter_records_for_athlete(atrc, 2025, "長洲", 2)) == 2

    njac = [
        {
            "season": "2025",
            "school": "NJAC",
            "grade": "1",
            "event": "800m",
            "mark": "2:30.87",
        }
    ]
    assert len(filter_records_for_athlete(njac, 2025, "長洲", 1)) == 1

    data = build_joined()
    athlete = next(
        a
        for y in data["years"]
        if y["year"] == 2025
        for t in y["teams"]
        if t["school"] == "長洲"
        for a in t["athletes"]
        if a["name"] == "猿渡愛梨"
    )
    assert athlete["track_events"]["800m"]["sb"]["school"] == "ATRC"
    assert athlete["track_events"]["1500m"]["sb"]["school"] == "ATRC"


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
    verification = data["meta"]["verification"]
    assert verification["checked_cells"] == 1196
    assert verification["unreadable_cells"] == 0
    assert verification["corrected_cells"] == 9
    assert data["meta"]["stats"]["with_any_track"] > 0
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

    assert athlete(2012, 1, 2)["name"] == "森澤彩乃"
    assert athlete(2012, 2, 1)["name"] == "大道志歩"
    assert athlete(2012, 2, 2)["name"] == "前田明佳里"
    assert athlete(2012, 2, 3)["name"] == "中川葉月"
    assert athlete(2012, 2, 4)["name"] == "植田愛美"
    assert athlete(2012, 2, 5)["name"] == "田上愛佳"
    assert athlete(2012, 4, 3)["name"] == "嶋村里恩"
    assert athlete(2012, 4, 2)["grade"] == 3
    assert athlete(2013, 1, 1)["name"] == "森澤彩乃"
    assert athlete(2013, 1, 2)["name"] == "磧結里"
    assert athlete(2013, 3, 5)["name"] == "嶋村里恩"
    assert athlete(2013, 4, 1)["name"] == "開琴美"
    assert athlete(2015, 1, 1)["name"] == "關知夏子"
    assert athlete(2015, 2, 2)["name"] == "荒川夏凜"
    assert athlete(2015, 3, 5)["name"] == "島﨑乃々佳"
    assert athlete(2016, 1, 3)["name"] == "荒川夏凜"
    assert athlete(2016, 3, 3)["name"] == "島﨑乃々佳"
    assert athlete(2017, 2, 2)["name"] == "沖愛凜"
    assert athlete(2017, 2, 4)["name"] == "荒川夏凜"
    assert athlete(2018, 1, 3)["name"] == "濱本麻那"
    assert athlete(2018, 1, 5)["name"] == "田上未来"
    assert athlete(2018, 2, 4)["name"] == "前淵あかり"
    assert athlete(2019, 4, 1)["name"] == "沖愛凜"
    assert athlete(2023, 2, 2)["name"] == "中尾彩朱"
    assert athlete(2023, 2, 4)["name"] == "髙田春陽"

    assert athlete(2016, 3, 3)["grade"] == 3
    assert athlete(2016, 4, 2)["grade"] == 1
    assert athlete(2019, 4, 4)["grade"] == 2
    assert athlete(2024, 3, 5)["grade"] == 2
    assert athlete(2025, 1, 2)["grade"] == 3


def test_csv_reconciled_athletes_have_same_year_track_matches() -> None:
    data = build_joined()
    corrected = {
        (2012, "森澤彩乃"),
        (2012, "大道志歩"),
        (2012, "嶋村里恩"),
        (2013, "森澤彩乃"),
        (2013, "磧結里"),
        (2013, "嶋村里恩"),
        (2013, "開琴美"),
        (2015, "關知夏子"),
        (2015, "島﨑乃々佳"),
        (2016, "島﨑乃々佳"),
        (2017, "荒川夏凜"),
        (2018, "田上未来"),
        (2018, "前淵あかり"),
        (2023, "中尾彩朱"),
        (2023, "髙田春陽"),
    }
    matched = {
        (year_block["year"], athlete["name"])
        for year_block in data["years"]
        for team in year_block["teams"]
        for athlete in team["athletes"]
        if athlete["match_count"] > 0
    }
    assert corrected <= matched
    assert data["meta"]["verification"]["csv_reconciled_cells"] == 27


def test_reconciliation_manifest_validates_against_raw_csv() -> None:
    module = runpy.run_path(str(ROOT / "input/aragyoku/build_women_top4.py"))
    module["validate_csv_reconciliations"](module["data"])


def test_fact_check_joined_passes() -> None:
    data = build_joined()
    issues = fact_check_joined(data)
    assert issues == [], "\n".join(issues)


def test_joined_artifact_exists() -> None:
    path = ROOT / "out/analysis/aragyoku_women_track_joined.json"
    assert path.exists(), "run scripts/aragyoku_women_track.py first"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == build_joined()
    csv_header = (
        ROOT / "out/analysis/aragyoku_women_track_joined.csv"
    ).read_text(encoding="utf-8").splitlines()[0]
    assert "1000m" not in csv_header


def test_pdf_generation_and_same_mark_labels() -> None:
    data = build_joined()
    assert TRACK_EVENTS == ("800m", "1500m", "3000m")
    assert all(
        "1000m" not in athlete["track_events"]
        for year in data["years"]
        for team in year["teams"]
        for athlete in team["athletes"]
    )
    first_mark = next(
        event["sb"]
        for year in data["years"]
        for team in year["teams"]
        for athlete in team["athletes"]
        for event in athlete["track_events"].values()
        if event.get("sb")
    )
    assert first_mark["school"]
    assert first_mark["grade"]
    with tempfile.TemporaryDirectory() as tmp:
        output1 = Path(tmp) / "report-1.pdf"
        output2 = Path(tmp) / "report-2.pdf"
        build_pdf(data, output1)
        build_pdf(data, output2)
        assert output1.stat().st_size > 0
        assert output1.read_bytes() == output2.read_bytes()

    styles = build_styles(register_font())
    rows = athlete_rows(
        {
            "athletes": [
                {
                    "leg": 1,
                    "name": "テスト選手",
                    "grade": 1,
                    "ekiden_mark": "10:00",
                    "track_events": {
                        "800m": {
                            "sb": {"mark": "2:30.00"},
                            "recent": {"mark": "2:30.00"},
                        }
                    },
                }
            ]
        },
        styles,
    )
    header_text = "".join(cell.getPlainText() for cell in rows[0])
    assert "目安" not in header_text
    assert "換算メモ" not in header_text
    assert "1000" not in header_text
    text = rows[1][4].getPlainText()
    assert "SB 2:30.00" in text
    assert "直 2:30.00" in text
    assert shorten_url("https://example.com/path") == "example.com/path"
    assert link_para("https://example.com", styles["cell"]).getPlainText() == "example.com"
    assert (
        mark_with_link(
            {"mark": "2:30.00", "url": "https://example.com"}, styles["cell"]
        ).getPlainText()
        == "2:30.00"
    )


if __name__ == "__main__":
    test_time_helpers()
    test_invalid_track_source_row_fails_fast()
    test_track_records_never_leak_across_years()
    test_aggregate_sb_is_not_reported_as_recent_record()
    test_non_adopted_record_is_not_reported_as_sb()
    test_grade_evidence_excludes_same_name_different_athlete()
    test_build_joined_has_2025_top4()
    test_corrected_transcriptions_are_preserved()
    test_csv_reconciled_athletes_have_same_year_track_matches()
    test_reconciliation_manifest_validates_against_raw_csv()
    test_joined_artifact_exists()
    test_pdf_generation_and_same_mark_labels()
    print("ok")
