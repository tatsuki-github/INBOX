#!/usr/bin/env python3
"""t-tsuchiyama の年度別 long CSV から中学生 SB JSON を生成する。

入力:
- input/external/drive/personal/t-tsuchiyama/sb/by-year/{year}-single-table.csv

出力:
- input/external/sb/middle-school/by-year/{year}-sb-adopted.json
- input/external/sb/middle-school/by-year/{year}-sb-adopted.status.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DRIVE_SB = ROOT / "input" / "external" / "drive" / "personal" / "t-tsuchiyama" / "sb"
SOURCE_DIR = DRIVE_SB / "by-year"
OUT_DIR = ROOT / "input" / "external" / "sb" / "middle-school" / "by-year"
SUPPORTED_YEARS = tuple(range(2012, 2027))
REQUIRED_FIELDS = {
    "名前",
    "所属",
    "性別",
    "カテゴリー",
    "大会名",
    "日付",
    "距離",
    "記録",
    "選手距離キー",
    "記録秒",
    "SB",
    "SB秒",
    "SB採用",
}


def is_sb_adopted(value: Any) -> bool:
    if value is True:
        return True
    if value is False:
        return False
    if isinstance(value, str):
        if value == "true":
            return True
        if value == "false":
            return False
    raise ValueError(f"invalid SB採用 value: {value!r}")


def normalize_sb_flag(value: Any) -> str:
    return "__YES__" if is_sb_adopted(value) else "__NO__"


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["選手距離キー"] = str(out.get("選手距離キー", "")).replace("\\|", "|")
    out["SB採用"] = normalize_sb_flag(out.get("SB採用"))
    return out


def serialize_rows(rows: list[dict[str, Any]]) -> str:
    return json.dumps(rows, ensure_ascii=False, indent=2) + "\n"


def load_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        missing = REQUIRED_FIELDS - fields
        if missing:
            raise ValueError(f"{path}: required columns missing: {sorted(missing)}")
        return list(reader)


def build_year(year: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if year not in SUPPORTED_YEARS:
        raise ValueError(f"Unsupported year: {year}")

    source_path = SOURCE_DIR / f"{year}-single-table.csv"
    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    source_rows = load_csv_rows(source_path)
    invalid_categories = sorted(
        {row.get("カテゴリー", "") for row in source_rows if row.get("カテゴリー") != "中学生"}
    )
    if invalid_categories:
        raise ValueError(f"{source_path}: non-middle-school categories: {invalid_categories}")

    rows: list[dict[str, Any]] = []
    for line_number, row in enumerate(source_rows, start=2):
        try:
            adopted = is_sb_adopted(row.get("SB採用"))
        except ValueError as exc:
            raise ValueError(f"{source_path}:{line_number}: {exc}") from exc
        if adopted:
            rows.append(normalize_row(row))
    rows.sort(key=lambda r: (r.get("日付", ""), r.get("名前", ""), r.get("距離", "")))

    output_text = serialize_rows(rows)
    status: dict[str, Any] = {
        "year": year,
        "source": str(source_path.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "source_row_count": len(source_rows),
        "sb_adopted_count": len(rows),
        "output_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        "complete": True,
        "source_status": "complete",
        "calendar_years": sorted(
            {str(row.get("日付", ""))[:4] for row in source_rows if row.get("日付")}
        ),
        "replacement_character_rows": sum(
            "\ufffd" in "".join(str(value) for value in row.values()) for row in source_rows
        ),
        "note": "年度はファイル名を正本とし、行の日付にかかわらず元ファイルの年度に保持",
    }
    return rows, status


def write_year(year: int, rows: list[dict[str, Any]], status: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / f"{year}-sb-adopted.json"
    status_path = OUT_DIR / f"{year}-sb-adopted.status.json"
    json_path.write_text(
        serialize_rows(rows),
        encoding="utf-8",
    )
    status_path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--years",
        nargs="*",
        type=int,
        default=list(SUPPORTED_YEARS),
        help="対象年度（既定: 2012〜2026）",
    )
    args = parser.parse_args()

    for year in args.years:
        rows, status = build_year(year)
        write_year(year, rows, status)
        print(f"{year}: source={status['source_row_count']} sb_adopted={len(rows)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
