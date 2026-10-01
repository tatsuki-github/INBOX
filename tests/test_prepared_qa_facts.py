"""Fact regressions with explicit source fixtures, not generator self-comparisons."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_prepared_qa_facts as audit
import generate_prepared_qa_athlete_all_records as records
import generate_prepared_qa_aragyoku_3000 as aragyoku
import generate_prepared_qa_knowledge_1000 as knowledge
import gap_crush_prepared_1000 as gap


@pytest.mark.parametrize("line, name, mark", [
    ("3区 佐藤央琉 10:42 区間10位", "佐藤央琉", "10:42"),
    ("4区 松本空羽 12:37 区間31位", "松本空羽", "12:37"),
    ("1区 松野凛空2 7位通過 11:02 区間7位", "松野凛空", "11:02"),
    ("2区 村上咲稀（3年）7:07（区間4位）", "村上咲稀", "7:07"),
    ("1区 2.7km 村上咲稀（3年）9分58秒", "村上咲稀", "9:58"),
    ("| 4区 | 松本空羽 | 1 | 12:37 | 31 |", "松本空羽", "12:37"),
])
def test_grade_never_consumes_first_digit_of_time(line, name, mark):
    rows = records.extract_ekiden_from_text(line)
    assert len(rows) == 1
    assert (rows[0]["名前"], rows[0]["記録"]) == (name, mark)


def test_athlete_time_does_not_cross_a_line():
    assert records.extract_ekiden_from_text("1区 山本哲瑠\n2区 佐藤央琉 10:42") == [
        {"名前": "佐藤央琉", "距離": "2区", "記録": "10:42", "_leg": "2", "_note": "", "_kind": "ekiden"}
    ]


@pytest.mark.parametrize("raw, expected", [("2'33\"50", "2:33.50"), ("9分07秒", "9:07")])
def test_time_formats_preserve_fraction_and_leading_zero(raw, expected):
    assert records.normalize_mark(raw) == expected


def test_race_date_comes_from_transcript(tmp_path, monkeypatch):
    monkeypatch.setattr(records, "ROOT", tmp_path)
    monkeypatch.setattr(records, "ARAGYOKU_TX", tmp_path)
    (tmp_path / "2024-男子.json").write_text(json.dumps({
        "date": "2024-10-16", "teams": [{"team": "岱明", "rank": 15, "legs": [
            {"name": "松野凛空", "leg": 1, "split": "11:11"}]}]}))
    assert records.load_aragyoku_ekiden_rows()[0]["日付"] == "2024/10/16"


def test_school_average_uses_correct_table_section(tmp_path, monkeypatch):
    men = tmp_path / "men.md"
    women = tmp_path / "women.md"
    men.write_text("## 上位4人平均\n| 5 | 岱明中 | 9 | 4:30.05 |\n"
                   "## 上位6人平均\n| 5 | 岱明中 | 9 | 4:42.49 |\n")
    women.write_text("## 800m・上位3人平均\n| 3 | 岱明中 | 6 | 2:28.81 |\n"
                     "## 1500m・上位3人平均\n| 3 | 岱明中 | 6 | 5:10.77 |\n")
    monkeypatch.setattr(gap, "ROOT", tmp_path)
    monkeypatch.setattr(gap, "RANK_MEN", men)
    monkeypatch.setattr(gap, "RANK_WOMEN", women)
    entries = gap.gen_school_rank_paraphrases(set(), 100)
    assert len(entries) == 2
    assert "4:30.05" in entries[0]["answer"]
    assert "2:28.81" in entries[1]["answer"]


def test_partial_order_is_not_total_prediction():
    entries = aragyoku.gen_formula_2026(set(), 100000)
    partial = next(e for e in entries if e["id"] == "formula-2026-男子-荒尾三中-order")
    assert "3区間のみの小計 32:13" in partial["answer"]
    assert "総合タイムは算出できません" in partial["answer"]


def test_team_count_is_latest_year():
    entries = knowledge.gen_arato_tamana_teams(set(), 100)
    atrc = next(e for e in entries if e["id"] == "records-team-ATRC")
    assert "2026年度の収録件数は67件" in atrc["answer"]
    assert "直近セクション件数 47" not in atrc["answer"]


def test_audit_rejects_wrong_athlete_rank_and_date():
    expected = {"answer": "2025年荒玉駅伝男子の岱明1区は倉田裕斗（区間タイム10:15）です。区間8位。"}
    entry = {"id": "aragyoku-2025-男子-岱明-leg1", "sources": [],
             "answer": "2025年荒玉駅伝男子の岱明1区は松野凛空（区間タイム10:15）です。区間1位。"}
    problems = audit.check_entry(entry, expected)["problems"]
    assert any(p.startswith("identity_projection_mismatch:") for p in problems)
    assert "numeric_projection_mismatch:1位" in problems
    expected = {"answer": "2024/10/16 1区 10:15"}
    entry = {"id": "race-2024-松野凛空-荒玉", "sources": [], "answer": "2024/10/15 1区 10:15"}
    assert any(p.startswith("wrong_race_tuple:") for p in audit.check_entry(entry, expected)["problems"])


def test_sample_question_times_are_not_asserted_results():
    assert audit.asserted_clocks("「荒玉男子1区を3分30秒/kmで」のように聞いてください。") == set()
    assert audit.asserted_clocks("結果は10:42です。") == {"642"}


@pytest.mark.parametrize(
    "meet, expected",
    [
        ("第20回　天草市ナイター陸上記録会", "天草市ナイター"),
        ("令和7年度 第3回ナイター記録会", "ナイター記録会"),
        ("第25回玉名郡ナイター中・長距離記録会", "玉名郡ナイター"),
        ("玉名郡ナイター", "玉名郡ナイター"),
    ],
)
def test_nighter_short_labels_are_not_collapsed(meet, expected):
    import generate_prepared_qa_knowledge_5000 as k5000

    assert k5000.short_meet(meet) == expected
    assert aragyoku.short_event(meet) == expected


def test_audit_flags_false_tamana_nighter_alias():
    entry = {
        "id": "race-2025-某人-玉名郡ナイター",
        "sources": [],
        "answer": "某人の2025年度・玉名郡ナイターの記録は1件です（大会名: 第20回　天草市ナイター陸上記録会）。",
    }
    problems = audit.check_entry(entry, None)["problems"]
    assert any(p.startswith("nighter_meet_alias_mismatch") for p in problems)


def test_audit_flags_hollow_answers_that_miss_the_question():
    entry = {
        "id": "sb-women800-daiming",
        "sources": [],
        "answer": "女子800mの学校別上位3人平均は 。",
    }
    problems = audit.check_entry(entry, None)["problems"]
    assert "hollow_answer_fact" in problems


def test_alignment_fix_restores_daiming_order_facts():
    import yaml
    from pathlib import Path

    faq = yaml.safe_load((ROOT / "input/faq/prepared-qa.v1.yaml").read_text())
    by = {e["id"]: e for e in faq["entries"]}
    ans = by["meet-2026-aragyoku-daiming-order"]["answer"]
    for token in ("村上咲稀", "松野凛空", "山本哲瑠", "仮置き"):
        assert token in ans
    assert "「」" not in ans


def test_ux_brush_up_avoids_broken_doudatta_and_jargon():
    import yaml

    faq = yaml.safe_load((ROOT / "input/faq/prepared-qa.v1.yaml").read_text())
    assert not any("のどうだった" in q for e in faq["entries"] for q in e.get("questions") or [])
    by = {e["id"]: e for e in faq["entries"]}
    assert "transcript" not in by["aragyoku-tamana-fuzoku"]["answer"]
    assert "コーパス" not in by["sb-middle-generic"]["answer"]
    area = by["nagomi-2026-aragyoku-area-result"]["answer"]
    assert len(area) < 600
    assert "岱明A" in area
    assert "TujEJG7vAey" in area
