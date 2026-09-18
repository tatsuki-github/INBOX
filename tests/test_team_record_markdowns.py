"""generate_team_record_markdowns の単体テスト。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from generate_team_record_markdowns import (  # noqa: E402
    generate_aragyoku_team_mds,
    generate_arato_tamana_team_mds,
    render_aragyoku_team_md,
    render_arato_team_md,
    safe_filename,
)
from arato_tamana_records import RecordRow, load_config  # noqa: E402


def test_safe_filename():
    assert "/" not in safe_filename("玉名/附")
    assert safe_filename("金栗PROJECT") == "金栗PROJECT"


def test_render_arato_includes_year_and_athlete():
    rows = {
        "2026": [
            RecordRow(
                name="テスト太郎",
                affiliation="岱明中",
                grade=2,
                gender="男子",
                distance="1500m",
                time_text="4:20.00",
                sb_text="",
                sb_adopted=False,
                date="2026/05/01",
                url="",
                record_seconds=260.0,
            )
        ]
    }
    md = render_arato_team_md("岱明中", rows)
    assert "2026年度" in md
    assert "テスト太郎" in md
    assert "1500m" in md


def test_render_aragyoku_includes_legs():
    md = render_aragyoku_team_md(
        "菊水",
        [
            {
                "year": 2025,
                "gender": "男子",
                "rank": 1,
                "total": "56:17",
                "legs": [
                    {"leg": 1, "name": "松浦眞大", "grade": 3, "split": "9:30", "cumulative": "9:30"}
                ],
            }
        ],
    )
    assert "菊水" in md
    assert "2025年" in md
    assert "松浦眞大" in md
    assert "優勝校" in md


def test_generate_writes_files(tmp_path, monkeypatch):
    # Run against real data but write to tmp by patching OUT dirs
    import generate_team_record_markdowns as mod

    monkeypatch.setattr(mod, "ARATO_OUT", tmp_path / "arato")
    monkeypatch.setattr(mod, "ARAGYOKU_OUT", tmp_path / "arag")
    config = load_config()
    arato = generate_arato_tamana_team_mds(config)
    arag = generate_aragyoku_team_mds()
    assert any(p.name == "INDEX.md" for p in arato)
    assert any(p.name.endswith(".md") and p.name != "INDEX.md" for p in arato)
    assert any(p.name == "INDEX.md" for p in arag)
    assert (tmp_path / "arag" / "菊水.md").exists() or any("菊水" in p.name for p in arag)
