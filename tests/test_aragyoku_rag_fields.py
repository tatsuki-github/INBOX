"""Independent fixture: section rank differs from cumulative passing rank."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_idaten_corpus import _chunk_aragyoku_transcript
from generate_prepared_qa_bulk import format_team_result_answer


def test_source_and_prepared_answer_keep_distinct_section_and_passing_fields(tmp_path):
    team = {"team": "検証校", "rank": 7, "total": "45:22", "legs": [
        {"leg": 2, "name": "検証選手", "grade": 1, "split": "7:01",
         "cumulative": "18:03", "split_rank": 3, "passing_rank": 4},
        {"leg": 3, "name": "未確認選手", "split": "7:44", "cumulative": "25:47"},
    ]}
    p = tmp_path / "fixture.json"
    p.write_text(json.dumps({"year": 2025, "gender": "女子", "teams": [team]}))
    rows = _chunk_aragyoku_transcript(p, "aragyoku/fixture.json")
    text = next(row["text"] for row in rows if "検証選手" in row["text"])
    assert "区間タイム7:01 区間順位3位 通過タイム（累計）18:03 通過順位4位" in text
    assert "区間順位未確認 通過タイム（累計）25:47 通過順位未確認" in text
    answer = format_team_result_answer(2025, "女子", team)
    assert "区間タイム 7:01（区間順位 3位） / 通過タイム 18:03（通過順位 4位）" in answer
    assert "区間順位 未確認" in answer
    assert "通過順位 未確認" in answer
