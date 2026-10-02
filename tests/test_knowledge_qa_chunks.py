"""Independent lossless-boundary fixtures for the full knowledge inventory."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_knowledge_qa_chunks as c

def test_text_preserves_all_characters_and_paragraph_boundaries():
    raw = "# 練習\n\n" + ("距離は3000m。回復は3分。\n\n" * 1000) + "最後の条件"
    parts = c.chunk_source(raw, ".md")
    c.verify_partition(raw, ".md", parts)
    assert len(parts) > 1
    assert "".join(p["text"] for p in parts) == raw
    assert parts[-1]["text"].endswith("最後の条件")

def test_csv_preserves_quotes_multiline_and_extra_columns():
    raw = '名前,大会,記録\n"選手甲","大会,記録会",10:02\n"選手乙","説明\n次行",9:55,備考\n'
    parts = c.chunk_source(raw, ".csv")
    c.verify_partition(raw, ".csv", parts)
    assert parts[0]["units"][0]["cells"] == ["選手甲", "大会,記録会", "10:02"]
    assert parts[0]["units"][1]["cells"] == ["選手乙", "説明\n次行", "9:55", "備考"]

def test_structured_records_never_lose_identity_or_tail():
    value = {"meta": {"year": 2025, "gender": "女子"}, "teams": [
        {"team": "学校" + str(i), "split": "10:02", "notes": "本文。" * 3000}
        for i in range(5)]}
    raw = json.dumps(value, ensure_ascii=False)
    parts = c.chunk_source(raw, ".json")
    c.verify_partition(raw, ".json", parts)
    assert len(parts) > 5
    units = [u for p in parts for u in p["units"]]
    assert any(u["pointer"] == "/teams/4/team" and u["value"] == "学校4" for u in units)

def test_pointer_escaping_is_reversible():
    obj = {"区間/種目": {"a~b": "タイム"}}
    assert c.resolve_pointer(obj, "/区間~1種目/a~0b") == "タイム"

def test_invalid_imported_json_is_retained():
    raw = '{"broken": "引用\n未知の転記'
    parts = c.chunk_source(raw, ".json")
    assert parts[0]["kind"] == "text"
    c.verify_partition(raw, ".json", parts)

def test_yaml_dates_are_source_values():
    raw = "year: 2026\nevents:\n- title: 大会\n  date: 2026-10-14\n  status: scheduled\n"
    parts = c.chunk_source(raw, ".yaml")
    c.verify_partition(raw, ".yaml", parts)
    assert "2026-10-14" in c.compact(parts)

def test_path_cannot_escape_repository():
    import pytest
    with pytest.raises(ValueError):
        c.safe_path("../../outside")

def test_empty_exports_have_no_records_but_single_record_is_kept():
    assert c.empty_record_export("year,date,name\n", ".csv")
    assert c.empty_record_export("[]", ".json")
    assert not c.empty_record_export("year,date,name\n2026,2026-10-14,甲\n", ".csv")
    assert not c.empty_record_export('{"year": 2026}', ".json")

def test_mirror_ownership_does_not_guess_unrelated_documents():
    assert c.inferred_original("out/2026/calendar.md") == "calendar.md"
    assert c.inferred_original("input/idaten-corpus/out-analysis/race.md") == "out/analysis/race.md"
    assert c.inferred_original("input/other-year/race.md") == "input/other-year/race.md"

def test_historical_header_gender_and_year_are_retained_in_team_context():
    import json
    value={'meta':{'gender':'女子'},'years':{'2020':{'date':'2020-10-14','teams':[{'team':str(i),'legs':[{'leg':j,'name':'甲'*100,'passing_rank':j} for j in range(1,6)]} for i in range(12)]}}}
    raw=json.dumps(value,ensure_ascii=False);parts=c.chunk_source(raw,'.json');c.verify_partition(raw,'.json',parts)
    teams=[u for p in parts for u in p['units'] if '/years/2020/teams/' in u['pointer']]
    assert teams and all(u['context']['year']==2020 and u['context']['gender']=='女子' for u in teams)
