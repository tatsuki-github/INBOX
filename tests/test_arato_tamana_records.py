"""arato_tamana_records の単体テスト。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from arato_tamana_pdf import build_pdf
from arato_tamana_records import (
    RecordRow,
    filter_rows,
    group_by_affiliation,
    group_records_by_gender,
    load_cache,
    load_config,
    matches_arato_tamana,
    row_from_cache_dict,
    shorten_url,
    sort_records,
)

FIXTURE = ROOT / "tests" / "fixtures" / "arato_tamana_sample.json"


@pytest.fixture
def config() -> dict:
    return load_config()


@pytest.fixture
def sample_rows() -> list[tuple[RecordRow, str]]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows: list[tuple[RecordRow, str]] = []
    for item in data:
        prefecture = item.get("prefecture", "熊本県")
        rows.append((row_from_cache_dict({k: v for k, v in item.items() if k != "prefecture"}), prefecture))
    return rows


def test_matches_arato_tamana_by_affiliation(config):
    row = RecordRow(name="テスト", affiliation="岱明中", grade=1, gender="男子", distance="800m", time_text="2:00", sb_text="", sb_adopted=False, date="", url="")
    assert matches_arato_tamana(row, config) is True


def test_matches_arato_tamana_by_extra_name(config):
    row = RecordRow(name="福島志帆", affiliation="外部", grade=2, gender="女子", distance="1500m", time_text="5:00", sb_text="", sb_adopted=False, date="", url="")
    assert matches_arato_tamana(row, config) is True


def test_excludes_kaneki_girls(config):
    row = RecordRow(name="有尾明莉", affiliation="金栗PROJECT", grade=2, gender="女子", distance="800m", time_text="2:40", sb_text="", sb_adopted=False, date="", url="")
    assert matches_arato_tamana(row, config) is False


def test_filter_rows_prefecture_and_region(config, sample_rows):
    filtered = filter_rows(sample_rows, config)
    names = {row.name for row in filtered}
    assert "今村昇磨" in names
    assert "福島志帆" in names
    assert "有尾明莉" not in names
    assert "他県選手" not in names


def test_sort_records_by_name_date_distance(sample_rows):
    filtered = filter_rows(sample_rows, load_config())
    imamura = [r for r in filtered if r.name == "今村昇磨"]
    sorted_rows = sort_records(imamura)
    assert sorted_rows[0].distance == "1500m"
    assert sorted_rows[1].distance == "800m"


def test_group_by_affiliation(sample_rows):
    filtered = filter_rows(sample_rows, load_config())
    sections = group_by_affiliation(filtered)
    affiliations = [s.affiliation for s in sections]
    assert "ATRC" in affiliations
    assert "岱明中" in affiliations
    atrc = next(s for s in sections if s.affiliation == "ATRC")
    assert len(atrc.records) == 2


def test_sort_records_groups_gender_before_name():
    rows = [
        RecordRow(name="B", affiliation="岱明中", grade=2, gender="女子", distance="800m", time_text="2:30", sb_text="", sb_adopted=False, date="2026/01/02", url=""),
        RecordRow(name="A", affiliation="岱明中", grade=2, gender="男子", distance="800m", time_text="2:00", sb_text="", sb_adopted=False, date="2026/01/01", url=""),
    ]
    sorted_rows = sort_records(rows)
    assert [row.gender for row in sorted_rows] == ["男子", "女子"]


def test_group_records_by_gender():
    rows = [
        RecordRow(name="B", affiliation="岱明中", grade=2, gender="女子", distance="800m", time_text="2:30", sb_text="", sb_adopted=False, date="2026/01/02", url=""),
        RecordRow(name="A", affiliation="岱明中", grade=2, gender="男子", distance="800m", time_text="2:00", sb_text="", sb_adopted=False, date="2026/01/01", url=""),
    ]
    groups = group_records_by_gender(rows)
    assert [label for label, _ in groups] == ["男子", "女子"]
    assert groups[0][1][0].name == "A"


def test_shorten_url():
    url = "http://www.kumariku.org/26/26,6,13tsushin/rel175.html"
    short = shorten_url(url, max_len=20)
    assert len(short) <= 20
    assert short.endswith("...")


def test_load_cache_roundtrip(tmp_path):
    row = RecordRow(name="A", affiliation="岱明中", grade=1, gender="男子", distance="800m", time_text="2:00", sb_text="", sb_adopted=False, date="2026/01/01", url="http://x")
    path = tmp_path / "cache.json"
    path.write_text(json.dumps([row.to_dict()], ensure_ascii=False), encoding="utf-8")
    loaded = load_cache(path)
    assert loaded[0].name == "A"


def test_build_pdf_smoke(tmp_path, sample_rows):
    filtered = filter_rows(sample_rows, load_config())
    sections = group_by_affiliation(filtered)
    out = tmp_path / "test.pdf"
    build_pdf(sections, out, "テスト PDF")
    assert out.exists()
    assert out.stat().st_size > 1000
    assert b"/URI" in out.read_bytes()
    try:
        from pypdf import PdfReader

        page_text = PdfReader(str(out)).pages[0].extract_text() or ""
        assert "所属別ランキング" in page_text
    except ImportError:
        pass
