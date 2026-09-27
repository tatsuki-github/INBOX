"""generate_team_record_markdowns の単体テスト。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from generate_team_record_markdowns import (  # noqa: E402
    generate_aragyoku_team_mds,
    generate_aragyoku_year_mds,
    generate_arato_tamana_team_mds,
    render_aragyoku_team_md,
    render_aragyoku_year_md,
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


def test_render_aragyoku_year_groups_every_team_by_leg_and_indexes_results():
    md = render_aragyoku_year_md(
        2025,
        [{
            "gender": "男子",
            "teams": [{
                "rank": 2,
                "team": "玉陵",
                "legs": [{
                    "leg": 3,
                    "name": "一瀬彪眞",
                    "grade": 3,
                    "split": "9:26",
                    "cumulative": "28:22",
                    "passing_rank": 2,
                    "split_rank": 3,
                }],
            }],
        }],
    )
    assert "### 3区" in md
    assert "| 2 | 玉陵 | 一瀬彪眞 | 3 | 9:26 | 28:22 | 2 | 3 |" in md
    assert "2025年荒玉駅伝男子 玉陵 3区" in md


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


def test_generate_writes_year_level_aragyoku_files(tmp_path, monkeypatch):
    import generate_team_record_markdowns as mod

    monkeypatch.setattr(mod, "ARAGYOKU_YEAR_OUT", tmp_path / "years")
    written = generate_aragyoku_year_mds()
    assert any(path.name == "INDEX.md" for path in written)
    year_file = tmp_path / "years" / "2025.md"
    assert year_file.exists()
    assert "## 男子" in year_file.read_text(encoding="utf-8")


def test_2025_tamaryo_leg_three_uses_corrected_transcription(tmp_path, monkeypatch):
    import generate_team_record_markdowns as mod

    monkeypatch.setattr(mod, "ARAGYOKU_YEAR_OUT", tmp_path / "years")
    monkeypatch.setattr(mod, "ARAGYOKU_OUT", tmp_path / "teams")
    mod.generate_aragyoku_year_mds()
    mod.generate_aragyoku_team_mds()
    year_text = (tmp_path / "years" / "2025.md").read_text(encoding="utf-8")
    team_text = (tmp_path / "teams" / "玉陵.md").read_text(encoding="utf-8")
    assert "| 2 | 玉陵 | 一瀬彪眞 | 3 | 9:26 | 28:22 | 2 | 3 |" in year_text
    assert "| 3 | 一瀬彪眞 | 3 | 9:26 | 28:22 |" in team_text
    assert "| 3 | unknown | 3 | 9:26 | 28:22 |" not in team_text
