"""年度別中学生SB生成のテスト。"""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_middle_school_sb_by_year as builder  # noqa: E402


EXPECTED_COUNTS = {
    2012: (4628, 2180),
    2013: (4219, 2046),
    2014: (4750, 2139),
    2015: (5252, 2181),
    2016: (3991, 2021),
    2017: (4982, 2431),
    2018: (5885, 2168),
    2019: (5733, 2065),
    2020: (3119, 1407),
    2021: (4421, 1968),
    2022: (5406, 2300),
    2023: (6463, 2267),
    2024: (6649, 2267),
    2025: (7395, 2662),
    2026: (8063, 3981),
}


@pytest.mark.parametrize("year", builder.SUPPORTED_YEARS)
def test_build_year_uses_complete_season_file(year: int) -> None:
    rows, status = builder.build_year(year)

    source_count, adopted_count = EXPECTED_COUNTS[year]
    assert status["source_row_count"] == source_count
    assert status["sb_adopted_count"] == adopted_count
    assert status["complete"] is True
    assert len(rows) == adopted_count
    assert all(row["カテゴリー"] == "中学生" for row in rows)
    assert all(row["SB採用"] == "__YES__" for row in rows)
    assert status["source_sha256"] == hashlib.sha256(
        (builder.SOURCE_DIR / f"{year}-single-table.csv").read_bytes()
    ).hexdigest()
    assert status["output_sha256"] == hashlib.sha256(
        builder.serialize_rows(rows).encode("utf-8")
    ).hexdigest()


def test_build_year_keeps_rows_in_filename_year_regardless_of_date() -> None:
    rows, status = builder.build_year(2018)

    assert status["calendar_years"] == ["2018", "2019"]
    assert any(row["日付"].startswith("2019/04/") for row in rows)


def test_load_csv_rows_rejects_missing_required_columns(tmp_path: Path) -> None:
    source = tmp_path / "invalid.csv"
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["名前", "SB採用"])
        writer.writeheader()
        writer.writerow({"名前": "選手", "SB採用": "true"})

    with pytest.raises(ValueError, match="required columns missing"):
        builder.load_csv_rows(source)


def test_build_year_rejects_unsupported_year() -> None:
    with pytest.raises(ValueError, match="Unsupported year"):
        builder.build_year(2011)


@pytest.mark.parametrize(
    "value",
    ["yes", "__YES__", "1", "", None, "TRUE", "False", " true", "false "],
)
def test_unknown_sb_flag_is_rejected(value: object) -> None:
    with pytest.raises(ValueError, match="invalid SB採用 value"):
        builder.is_sb_adopted(value)
