#!/usr/bin/env python3
"""2025 なごみ成績表とレース前 SB 予想の単体テスト。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import generate_nagomi_2025_sb_vs_actual as nagomi2025  # noqa: E402
import generate_nagomi_order_sb_preview as g  # noqa: E402
import nagomi_2025_results_data as results  # noqa: E402


def test_daimyo_women_matches_known_memo() -> None:
    team = results.daimyo_women()
    assert team["rank"] == 8
    assert team["total"] == "31:22"
    names = [leg["name"] for leg in team["legs"]]
    assert names == ["村上咲稀", "高田麻由", "塚原優衣", "角田亜美"]
    assert [leg["split"] for leg in team["legs"]] == ["7:06", "7:37", "8:11", "8:28"]


def test_daimyo_men_b_is_tetsuru_not_satoru() -> None:
    team = results.daimyo_men_b()
    assert team["rank"] == 31
    assert team["total"] == "47:37"
    assert team["legs"][0]["name"] == "山本哲瑠"
    assert "悟瑠" not in team["legs"][0]["name"]


def test_official_totals_equal_split_sum() -> None:
    for teams in (results.WOMEN, results.MEN):
        for team in teams:
            if team.get("rank") is None:
                continue
            parts = [g.parse_seconds(leg["split"]) for leg in team["legs"]]
            assert all(p is not None for p in parts), team["team"]
            total = g.parse_seconds(team["total"])
            assert total is not None
            assert abs(sum(parts) - total) < 0.6, (team["team"], parts, total)


def test_as_of_excludes_post_race_1500() -> None:
    women = nagomi2025.load_2025_sb("女子")
    murakami = women[g.norm_name("村上咲稀")]
    assert "1500m" not in murakami.marks
    assert "800m" in murakami.marks
    men = nagomi2025.load_2025_sb("男子")
    imamura = men[g.norm_name("今村昇磨")]
    assert "1500m" in imamura.marks
    assert "3000m" not in imamura.marks


def test_gender_filter_skips_same_name_other_sex() -> None:
    men = nagomi2025.load_2025_sb("男子")
    # 玉南B 3区 田中小羽は成績表上男子。女子 SB の同姓同名を使わない。
    ath = men.get(g.norm_name("田中小羽"))
    assert ath is None or not ath.marks


def test_generated_preview_and_gap_files_exist() -> None:
    meet = nagomi2025.MEET_DIR
    for name in (
        "女子成績表.md",
        "男子成績表.md",
        "成績表.json",
        "女子区間オーダー_SB予想.md",
        "男子区間オーダー_SB予想.md",
        "女子区間オーダー_SB予想.pdf",
        "男子区間オーダー_SB予想.pdf",
        "予実比較.md",
        "予実比較.pdf",
    ):
        assert (meet / name).is_file(), name
    women = (meet / "女子区間オーダー_SB予想.md").read_text(encoding="utf-8")
    assert "as_of: 2025-09-20" in women
    assert "(通過順)通過予想 / (区間順)区間記録" in women
    assert " / (" in women  # セル内に通過/区間
    gap = (meet / "予実比較.md").read_text(encoding="utf-8")
    assert "岱明" in gap
    assert "山本哲瑠" in gap
    report = nagomi2025.build_2025_report("女子", results.WOMEN)
    daimyo = next(t for t in report["teams"] if t["team"] == "岱明")
    assert daimyo["actual_rank"] == 8
    assert daimyo["actual_total"] == g.parse_seconds("31:22")
    assert daimyo["legs"][0]["actual"] == g.parse_seconds("7:06")
    assert daimyo["legs"][0]["pred"] is not None
    assert daimyo["total_delta"] is not None
    assert daimyo["legs"][0].get("pred_cum_rank") is not None
    assert daimyo["legs"][0].get("pred_sec_rank") is not None
