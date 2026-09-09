"""arato_tamana_ranking の単体テスト。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from arato_tamana_ranking import (
    best_seconds_at_distance,
    compute_affiliation_rankings,
    compute_all_affiliation_rankings,
    format_seconds,
    project_3000m_seconds,
    top_n_average,
)
from arato_tamana_records import AffiliationSection, RecordRow


def _row(**kwargs) -> RecordRow:
    defaults = {
        "name": "A",
        "affiliation": "テスト中",
        "grade": 2,
        "gender": "男子",
        "distance": "1500m",
        "time_text": "4:30.00",
        "sb_text": "4:30.00",
        "sb_adopted": True,
        "date": "2026/01/01",
        "url": "",
        "record_seconds": 270.0,
    }
    defaults.update(kwargs)
    return RecordRow(**defaults)


def test_project_3000m_from_1500m_sb():
    projected = project_3000m_seconds([_row(distance="1500m", record_seconds=270.0, sb_adopted=True)])
    assert projected == 570.0
    assert format_seconds(projected) == "9:30.00"


def test_project_3000m_from_800m_sb():
    projected = project_3000m_seconds([_row(distance="800m", record_seconds=120.0, sb_adopted=True)])
    assert projected == 510.0


def test_project_3000m_prefers_actual_3000m():
    projected = project_3000m_seconds(
        [
            _row(name="A", distance="3000m", record_seconds=540.0, sb_adopted=True),
            _row(name="A", distance="1500m", record_seconds=260.0, sb_adopted=True),
        ]
    )
    assert projected == 540.0


def test_top_n_average_requires_full_n():
    assert top_n_average([500.0, 520.0, 540.0], 6) is None
    assert top_n_average([500.0, 520.0, 540.0, 560.0], 4) == (500.0 + 520.0 + 540.0 + 560.0) / 4


def test_best_seconds_at_distance_prefers_sb():
    rows = [
        _row(distance="800m", record_seconds=130.0, sb_adopted=False),
        _row(distance="800m", record_seconds=120.0, sb_adopted=True),
    ]
    assert best_seconds_at_distance(rows, "800m") == 120.0


def test_best_seconds_at_distance_falls_back_to_best():
    rows = [_row(distance="1500m", record_seconds=280.0, sb_adopted=False)]
    assert best_seconds_at_distance(rows, "1500m") == 280.0


def test_compute_all_affiliation_rankings_includes_actual_distances():
    section = AffiliationSection(
        affiliation="テスト中",
        records=[
            _row(name="A", distance="800m", record_seconds=130.0),
            _row(name="B", distance="1500m", record_seconds=280.0),
            _row(name="C", distance="3000m", record_seconds=600.0),
        ],
    )
    categories = compute_all_affiliation_rankings([section])
    keys = [category.spec.key for category in categories]
    assert keys == ["800m", "1500m", "3000m", "3000m-projected"]
    assert categories[0].boys.entries == []
    assert categories[1].boys.entries == []
    assert categories[2].boys.entries == []


def test_excludes_affiliation_below_minimum_athletes():
    def projected_row(name: str, seconds: float) -> RecordRow:
        return _row(
            name=name,
            distance="3000m",
            record_seconds=seconds,
            time_text=format_seconds(seconds),
        )

    enough = AffiliationSection(
        affiliation="十分所属",
        records=[projected_row(str(i), 500.0 + i) for i in range(6)],
    )
    too_few = AffiliationSection(
        affiliation="不足所属",
        records=[projected_row(str(i), 600.0 + i) for i in range(5)],
    )
    boys, _girls = compute_affiliation_rankings([too_few, enough])
    assert [entry.affiliation for entry in boys.entries] == ["十分所属"]
    assert boys.entries[0].rank == 1


def test_compute_affiliation_rankings_orders_by_primary_average():
    def projected_row(name: str, affiliation: str, seconds: float) -> RecordRow:
        return _row(
            name=name,
            affiliation=affiliation,
            distance="3000m",
            record_seconds=seconds,
            time_text=format_seconds(seconds),
        )

    fast = AffiliationSection(
        affiliation="A所属",
        records=[
            projected_row("1", "A所属", 500.0),
            projected_row("2", "A所属", 510.0),
            projected_row("3", "A所属", 520.0),
            projected_row("4", "A所属", 530.0),
            projected_row("5", "A所属", 540.0),
            projected_row("6", "A所属", 550.0),
        ],
    )
    slow = AffiliationSection(
        affiliation="B所属",
        records=[
            projected_row("1", "B所属", 600.0),
            projected_row("2", "B所属", 610.0),
            projected_row("3", "B所属", 620.0),
            projected_row("4", "B所属", 630.0),
            projected_row("5", "B所属", 640.0),
            projected_row("6", "B所属", 650.0),
        ],
    )
    boys, _girls = compute_affiliation_rankings([slow, fast])
    assert boys.entries[0].affiliation == "A所属"
    assert boys.entries[0].rank == 1
    assert boys.entries[0].averages[6] == (500.0 + 510.0 + 520.0 + 530.0 + 540.0 + 550.0) / 6
