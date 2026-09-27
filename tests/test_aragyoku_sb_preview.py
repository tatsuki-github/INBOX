#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""荒玉 SB 予想の単体テスト（鮮度・距離・多校全区間仮置き）。"""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_aragyoku_ekiden_sb_preview as aragyoku  # noqa: E402
import generate_nagomi_order_sb_preview as nagomi  # noqa: E402


class TestFreshness(unittest.TestCase):
    def test_old_mark_excluded(self) -> None:
        self.assertFalse(
            nagomi.date_within_freshness("2025-01-01", "2026-09-27", 152)
        )

    def test_recent_mark_included(self) -> None:
        self.assertTrue(
            nagomi.date_within_freshness("2026-06-01", "2026-09-27", 152)
        )

    def test_missing_date_excluded_when_freshness(self) -> None:
        self.assertFalse(nagomi.date_within_freshness("", "2026-09-27", 152))

    def test_missing_date_allowed_without_freshness(self) -> None:
        self.assertTrue(
            nagomi.date_within_freshness("", "2026-09-27", None, allow_missing_date=True)
        )


class TestDistances(unittest.TestCase):
    def test_women_five_legs(self) -> None:
        self.assertEqual(len(aragyoku.WOMEN_DISTANCES_KM), 5)
        self.assertEqual(aragyoku.WOMEN_DISTANCES_KM[0], 3.0)
        self.assertEqual(aragyoku.WOMEN_DISTANCES_KM[1], 1.855)

    def test_men_six_legs(self) -> None:
        self.assertEqual(len(aragyoku.MEN_DISTANCES_KM), 6)
        self.assertEqual(aragyoku.MEN_DISTANCES_KM[1], 2.855)


class TestProvisionalOrders(unittest.TestCase):
    def test_women_all_teams_fill_five(self) -> None:
        for row in aragyoku.PROVISIONAL_ORDERS["女子"]:
            self.assertEqual(len(row["legs"]), 5, row["team"])

    def test_men_all_teams_fill_six(self) -> None:
        for row in aragyoku.PROVISIONAL_ORDERS["男子"]:
            self.assertEqual(len(row["legs"]), 6, row["team"])

    def test_taimei_women_confirmed(self) -> None:
        self.assertEqual(len(aragyoku.TAIMEI_KNOWN_LEGS["女子"]), 5)
        self.assertEqual(aragyoku.TAIMEI_KNOWN_LEGS["女子"][2], "山﨑 莉奈")

    def test_taimei_men_known_four_plus_provisional(self) -> None:
        self.assertEqual(len(aragyoku.TAIMEI_KNOWN_LEGS["男子"]), 4)
        taimei = next(r for r in aragyoku.PROVISIONAL_ORDERS["男子"] if "岱明" in r["team"])
        self.assertEqual(taimei["legs"][4], "中尾 快叶")
        self.assertEqual(taimei["legs"][5], "松本 空羽")

    def test_build_fills_men_5_6(self) -> None:
        # ディスク上の人間考慮を避けるため空メモで再構築
        row = next(r for r in aragyoku.PROVISIONAL_ORDERS["男子"] if "岱明" in r["team"])
        team = aragyoku.build_team(
            row, "男子", {}, human_notes=aragyoku.empty_human_notes("男子")
        )
        self.assertEqual(team["legs"][4]["name"], "中尾 快叶")
        self.assertEqual(team["legs"][5]["name"], "松本 空羽")
        self.assertIn("※仮", team["legs"][4]["note"])
        self.assertIn("確定", team["legs"][0]["note"])
        self.assertTrue(team["complete"])
        self.assertIn("駅伝加味", team["legs"][2]["note"])
        # 事実エビデンス: 大会名・実測・距離が入る
        self.assertRegex(team["legs"][2]["note"], r"(なごみ|ジュニア).+@\d+\.\d+km")
        self.assertIn("→予想", team["legs"][2]["note"])

    def test_includes_kikusui_and_gyokuryo_men(self) -> None:
        teams = [r["team"] for r in aragyoku.PROVISIONAL_ORDERS["男子"]]
        self.assertIn("菊水中", teams)
        self.assertIn("玉陵中", teams)

    def test_fuzoku_women_are_affiliation_real(self) -> None:
        fuzoku = next(r for r in aragyoku.PROVISIONAL_ORDERS["女子"] if "附" in r["team"])
        self.assertEqual(fuzoku["legs"][0], "大木 莉子")
        self.assertEqual(fuzoku["legs"][4], "戸谷 美月")
        self.assertNotIn("大木 夏菜", fuzoku["legs"])
        self.assertNotIn("小山 紗奈", fuzoku["legs"])

    def test_women_aces_on_leg1_and_anchor(self) -> None:
        """仮置き校は1区・5区に校内SB上位（エース）を置く。岱明確定は維持。"""
        # 南関: 福山・堀田が長距離向き上位。4区はなごみで速い原賀（稗島はβで遅い）
        nankan = next(r for r in aragyoku.PROVISIONAL_ORDERS["女子"] if r["team"] == "南関中")
        self.assertEqual(nankan["legs"][0], "福山 結衣")
        self.assertEqual(nankan["legs"][3], "原賀 美和")
        self.assertEqual(nankan["legs"][4], "堀田 稔々")
        self.assertNotIn("稗島 琴都", nankan["legs"])
        # 岱明: 確定どおり村上1・高田5
        taimei = next(r for r in aragyoku.PROVISIONAL_ORDERS["女子"] if "岱明" in r["team"])
        self.assertEqual(taimei["legs"][0], "村上 咲稀")
        self.assertEqual(taimei["legs"][4], "高田 麻由")
        # 海陽: 三原1・前田5
        kaiyo = next(r for r in aragyoku.PROVISIONAL_ORDERS["女子"] if "海陽" in r["team"])
        self.assertEqual(kaiyo["legs"][0], "三原 悠愛")
        self.assertEqual(kaiyo["legs"][4], "前田 凛子")

    def test_no_median_imputation_in_ranking(self) -> None:
        # 1名だけSBありでも、直近駅伝／前年荒玉がある区間は実績で埋まる（中央値補完ではない）
        mark = nagomi.Mark(seconds=300.0, text="5:00.00", date="2026-08-01", source="test")
        idx = {
            nagomi.norm_name("村上 咲稀"): nagomi.AthleteSB(
                name="村上 咲稀", marks={"1500m": mark}
            )
        }
        report = aragyoku.build_report("女子", idx, as_of="2026-09-27")
        self.assertIsNone(report.get("leg_medians"))
        self.assertIsNone(report.get("median_fill"))
        taimei = next(t for t in report["teams"] if "岱明" in t["team"])
        self.assertTrue(taimei["complete"])
        self.assertFalse(taimei.get("imputed"))
        self.assertIn("駅伝加味", taimei["legs"][1]["note"])
        # SB事実 + 駅伝事実がエビデンスに入る
        self.assertIn("SB:", taimei["legs"][0]["note"])
        self.assertRegex(taimei["legs"][1]["note"], r"@\d+\.\d+km")
        for t in report["teams"]:
            self.assertFalse(t.get("imputed"))
            for det in t["legs"]:
                self.assertNotIn("中央値", det.get("note") or "")
                # 予想がある区間は必ず事実エビデンス末尾に →予想
                if det.get("pred") is not None and det.get("name"):
                    self.assertIn("→予想", det["note"])

    def test_multi_school_report_ranks(self) -> None:
        mark = nagomi.Mark(seconds=300.0, text="5:00.00", date="2026-08-01", source="test")
        idx = {}
        for row in aragyoku.PROVISIONAL_ORDERS["女子"]:
            for name in row["legs"]:
                idx[nagomi.norm_name(name)] = nagomi.AthleteSB(
                    name=name, marks={"1500m": mark}
                )
        report2 = aragyoku.build_report("女子", idx, as_of="2026-09-27")
        seed_teams = {r["team"] for r in aragyoku.PROVISIONAL_ORDERS["女子"]}
        ranked_seed = [t for t in report2["ranked"] if t["team"] in seed_teams]
        self.assertEqual(len(ranked_seed), len(aragyoku.PROVISIONAL_ORDERS["女子"]))
        for t in report2["teams"]:
            if t["team"] not in seed_teams:
                continue
            self.assertEqual(len(t["legs"]), 5)
            self.assertTrue(all(d["name"] for d in t["legs"]))
            self.assertFalse(t.get("imputed"))


class TestSchoolAffiliationMap(unittest.TestCase):
    """クラブ所属を arato_tamana_report.yaml で各校へ分配する。"""

    def test_resolve_atrc_and_kanaguri(self) -> None:
        smap = aragyoku.load_arato_school_map()
        ov = smap["affiliation_overrides"]
        ath = smap["athlete_overrides"]
        self.assertEqual(
            aragyoku.resolve_analysis_school(
                "ATRC", "今村昇磨", affiliation_overrides=ov, athlete_overrides=ath
            ),
            "岱明中",
        )
        self.assertEqual(
            aragyoku.resolve_analysis_school(
                "ATRC", "石川隼", affiliation_overrides=ov, athlete_overrides=ath
            ),
            "長洲中",
        )
        self.assertEqual(
            aragyoku.resolve_analysis_school(
                "ATRC", "藤原尚己", affiliation_overrides=ov, athlete_overrides=ath
            ),
            "荒尾第四中",
        )
        self.assertEqual(
            aragyoku.resolve_analysis_school(
                "金栗PROJECT",
                "居石華音",
                affiliation_overrides=ov,
                athlete_overrides=ath,
            ),
            "玉陵中",
        )
        self.assertEqual(
            aragyoku.resolve_analysis_school(
                "金栗PROJECT",
                "庄山瑠那",
                affiliation_overrides=ov,
                athlete_overrides=ath,
            ),
            "荒尾三中",
        )
        self.assertEqual(
            aragyoku.resolve_analysis_school(
                "金栗PROJECT",
                "隈部侑成",
                affiliation_overrides=ov,
                athlete_overrides=ath,
            ),
            "菊水中",
        )

    def test_redistribute_builds_nagasu_men_and_women_clubs(self) -> None:
        men_sb, _ = nagomi.load_sb_index(
            as_of="2026-09-27", gender="男子", freshness_days=152
        )
        women_sb, _ = nagomi.load_sb_index(
            as_of="2026-09-27", gender="女子", freshness_days=152
        )
        men = aragyoku.get_provisional_orders("男子", men_sb)
        women = aragyoku.get_provisional_orders("女子", women_sb)
        men_teams = [r["team"] for r in men]
        women_teams = [r["team"] for r in women]
        # 米谷慶吾は2025中3→今年度卒業。在籍が石川隼のみのため男子長洲は最低人数未満で非掲載
        self.assertNotIn("長洲中", men_teams)
        grads = aragyoku.load_graduated_school_names("男子")
        self.assertIn("長洲中|米谷慶吾", grads)
        pools = aragyoku.build_school_athlete_pools("男子", men_sb)
        nagasu_pool = {nagomi.norm_name(n) for n, _ in pools.get("長洲中", [])}
        self.assertIn(nagomi.norm_name("石川隼"), nagasu_pool)
        self.assertNotIn(nagomi.norm_name("米谷慶吾"), nagasu_pool)
        self.assertIn("菊水中", women_teams)
        self.assertIn("玉陵中", women_teams)
        # 荒尾四女子は ATRC default が1名だと最低人数未満で載らない
        self.assertNotIn("荒尾第四中", women_teams)

        yondai = next(r for r in men if r["team"] == "荒尾第四中")
        names_y = {nagomi.norm_name(n) for n in yondai["legs"]}
        self.assertIn(nagomi.norm_name("藤原尚己"), names_y)
        self.assertIn(nagomi.norm_name("藤井祐吏"), names_y)
        self.assertTrue(all(str(n).strip() for n in yondai["legs"]))
        self.assertEqual(yondai["source"], "prior_year+nagomi")
        self.assertEqual(yondai["legs"][4], "藤井 祐吏")  # 遅→5区
        self.assertEqual(yondai["legs"][1], "本戸 優貴")  # 次遅→2区

        taimei = next(r for r in men if "岱明" in r["team"])
        self.assertEqual(
            taimei["legs"],
            ["松野 凛空", "山本 哲瑠", "今村 昇磨", "田上 颯人", "中尾 快叶", "松本 空羽"],
        )
        self.assertEqual(taimei["legs"][2], "今村 昇磨")

        nagasu_w = next(r for r in women if r["team"] == "長洲中")
        names_w = {nagomi.norm_name(n) for n in nagasu_w["legs"]}
        self.assertTrue(
            names_w & {nagomi.norm_name(x) for x in ("猿渡愛梨", "山川綾", "濱北愛")}
        )
        self.assertEqual(nagasu_w["legs"][0], "猿渡 愛梨")
        self.assertEqual(nagasu_w["source"], "locked_ace_leg1")
        self.assertEqual(nagasu_w["legs"][1], "村里 唯花")
        self.assertEqual(nagasu_w["legs"][2], "濱北 愛")
        self.assertEqual(nagasu_w["legs"][3], "山川 綾")
        self.assertEqual(nagasu_w["legs"][4], "中村 羽音")
        marks = aragyoku.RECENT_EKIDEN_MARKS[nagomi.norm_name("猿渡愛梨")]
        self.assertTrue(any(m.get("meet") == "なごみ" and m.get("sec") == 6 * 60 + 55 for m in marks))

        gyokuryo_w = next(r for r in women if r["team"] == "玉陵中")
        self.assertIn(nagomi.norm_name("居石華音"), {nagomi.norm_name(n) for n in gyokuryo_w["legs"]})

        # 玉陵男子: プール全員を見たうえで最速6名のみ。三次・五郎丸（下位）は載せない
        gyokuryo_m = next(r for r in men if r["team"] == "玉陵中")
        names_g = {nagomi.norm_name(n) for n in gyokuryo_m["legs"] if str(n).strip()}
        self.assertIn(nagomi.norm_name("柿本晴仁"), names_g)
        self.assertIn(nagomi.norm_name("内野翼"), names_g)
        self.assertIn(nagomi.norm_name("松島颯希"), names_g)
        self.assertNotIn(nagomi.norm_name("三次郷太"), names_g)
        self.assertNotIn(nagomi.norm_name("五郎丸壱悟"), names_g)
        pools_m = aragyoku.build_school_athlete_pools("男子", men_sb)
        self.assertGreaterEqual(len(pools_m.get("玉陵中", [])), 6)

        san = next(r for r in women if r["team"] == "荒尾三中")
        self.assertIn(nagomi.norm_name("庄山瑠那"), {nagomi.norm_name(n) for n in san["legs"]})
        self.assertEqual(san["legs"][0], "庄山 瑠那")
        self.assertEqual(san["legs"][1], "平 夢花")
        self.assertEqual(san["legs"][2], "内野 沙笑")
        self.assertEqual(san["legs"][3], "佐藤 妃葵")
        self.assertEqual(san["legs"][4], "福島 志帆")

        tamana = next(r for r in women if r["team"] == "玉名中")
        # 川原は今年フォーム落ち → 1区・アンカー外（2–4区のライン）
        self.assertNotEqual(tamana["legs"][0], "川原 芽吹")
        self.assertNotEqual(tamana["legs"][4], "川原 芽吹")
        self.assertEqual(tamana["legs"][0], "清藤 結唯")
        self.assertEqual(tamana["legs"][2], "川原 芽吹")
        self.assertEqual(tamana["legs"][4], "水本 星夏")
        self.assertTrue(all(str(n).strip() for n in tamana["legs"]))
        self.assertIn("亀木", tamana["legs"][1])
        self.assertIn(nagomi.norm_name("清藤結唯"), {nagomi.norm_name(n) for n in tamana["legs"]})

    def test_no_duplicate_athletes_across_legs(self) -> None:
        men_sb, _ = nagomi.load_sb_index(
            as_of="2026-09-27", gender="男子", freshness_days=152
        )
        women_sb, _ = nagomi.load_sb_index(
            as_of="2026-09-27", gender="女子", freshness_days=152
        )
        for gender, idx in (("男子", men_sb), ("女子", women_sb)):
            for row in aragyoku.get_provisional_orders(gender, idx):
                filled = [n for n in row["legs"] if str(n).strip()]
                for i, a in enumerate(filled):
                    for b in filled[i + 1 :]:
                        self.assertFalse(
                            aragyoku.is_same_athlete(a, b),
                            f"{gender} {row['team']} near-dup: {a!r} vs {b!r} in {filled}",
                        )

    def test_near_duplicate_names_collapsed(self) -> None:
        self.assertTrue(aragyoku.is_same_athlete("河野壮大", "河野壮太"))
        self.assertTrue(aragyoku.is_same_athlete("森 絢恵", "森 絢惠"))
        self.assertFalse(aragyoku.is_same_athlete("小倉十和", "小倉由宇"))
        legs = aragyoku.legs_from_ranked_athletes(
            ["河野壮大", "田島航", "河野壮太", "萩原大介"],
            6,
            women_aces=False,
        )
        self.assertEqual(legs[0], "河野壮大")
        self.assertNotIn("河野壮太", legs)
        # 3 unique: 最速1・最遅5・残り2 → 空が3
        self.assertEqual(legs.count(""), 3)
        self.assertEqual(legs[4], "萩原大介")
        self.assertEqual(legs[1], "田島航")

    def test_legs_from_ranked_men_slow_to_leg5_then_leg2(self) -> None:
        legs = aragyoku.legs_from_ranked_athletes(
            ["A", "B", "C", "D", "E", "F"], 6, women_aces=False
        )
        self.assertEqual(legs, ["A", "E", "B", "C", "F", "D"])
        thin = aragyoku.legs_from_ranked_athletes(["X", "Y"], 6, women_aces=False)
        self.assertEqual(thin, ["X", "", "", "", "Y", ""])
        # 候補が区間数より多いとき、最遅のG/Hは出走枠に入らない
        oversized = aragyoku.legs_from_ranked_athletes(
            ["A", "B", "C", "D", "E", "F", "G", "H"], 6, women_aces=False
        )
        self.assertEqual(oversized, ["A", "E", "B", "C", "F", "D"])
        self.assertNotIn("G", oversized)
        self.assertNotIn("H", oversized)

    def test_seeds_have_no_literal_repeats(self) -> None:
        for gender, rows in aragyoku.PROVISIONAL_ORDERS.items():
            for row in rows:
                filled = [n for n in row["legs"] if str(n).strip()]
                keys = [nagomi.norm_name(n) for n in filled]
                self.assertEqual(
                    len(keys),
                    len(set(keys)),
                    f"seed {gender} {row['team']} still repeats: {filled}",
                )

    def test_legs_from_ranked_women_aces(self) -> None:
        legs = aragyoku.legs_from_ranked_athletes(
            ["A", "B", "C", "D", "E"], 5, women_aces=True
        )
        self.assertEqual(legs[0], "A")
        self.assertEqual(legs[4], "B")
        self.assertEqual(legs[1:4], ["C", "D", "E"])

    def test_legs_from_ranked_no_repeat_when_short(self) -> None:
        legs = aragyoku.legs_from_ranked_athletes(["A", "B"], 5, women_aces=True)
        self.assertEqual(legs, ["A", "", "", "", "B"])
        men = aragyoku.legs_from_ranked_athletes(["X", "Y"], 6, women_aces=False)
        self.assertEqual(men, ["X", "", "", "", "Y", ""])
        single = aragyoku.legs_from_ranked_athletes(["Solo"], 6, women_aces=False)
        self.assertEqual(single, ["Solo", "", "", "", "", ""])


class TestPriorYearReturners(unittest.TestCase):
    def test_load_includes_grade_1_2_only(self) -> None:
        rows = aragyoku.load_prior_year_returners("男子")
        self.assertGreater(len(rows), 10)
        self.assertTrue(all(r["grade_was"] in (1, 2) for r in rows))
        # 2024 は学年1のみ（一昨年の2年は今は卒業相当）
        y2024 = [r for r in rows if int(r["year"]) == 2024]
        self.assertTrue(y2024)
        self.assertTrue(all(r["grade_was"] == 1 for r in y2024))
        names = {nagomi.norm_name(r["name"]) for r in rows}
        self.assertIn(nagomi.norm_name("今村昇磨"), names)
        self.assertIn(nagomi.norm_name("山本哲瑠"), names)
        self.assertIn(nagomi.norm_name("佐藤央琉"), names)
        # 3年は復帰対象外
        self.assertNotIn(nagomi.norm_name("倉田裕斗"), names)

    def test_eligible_max_grade(self) -> None:
        self.assertEqual(aragyoku.eligible_max_grade_in_meet_year(2025), 2)
        self.assertEqual(aragyoku.eligible_max_grade_in_meet_year(2024), 1)

    def test_excludes_graduated_yamamoto_yuto(self) -> None:
        # 2025成績表は(1)だが2023天水(3)→幽霊。復帰候補・プールから除外する
        rows = aragyoku.load_prior_year_returners("男子")
        names = {nagomi.norm_name(r["name"]) for r in rows}
        self.assertNotIn(nagomi.norm_name("山本悠斗"), names)
        grads = aragyoku.load_graduated_school_names("男子")
        self.assertIn("天水中|山本悠斗", grads)
        self.assertTrue(
            aragyoku.is_excluded_graduate(
                "山本悠斗", school="天水中", graduated_keys=grads
            )
        )
        # 本戸は2024(2)/2025(2)の学年揺れでも最新が中2→今中3。除外しない
        self.assertNotIn("荒尾第四中|本戸優貴", grads)
        pools = aragyoku.build_school_athlete_pools("男子", {})
        tensui = {nagomi.norm_name(n) for n, _ in pools.get("天水中", [])}
        self.assertNotIn(nagomi.norm_name("山本悠斗"), tensui)

    def test_projected_current_grade(self) -> None:
        self.assertEqual(aragyoku.projected_current_grade(1, 2025), 2)
        self.assertEqual(aragyoku.projected_current_grade(3, 2023), 6)
        self.assertTrue(aragyoku.is_current_middle_schooler(2, 2025))
        self.assertFalse(aragyoku.is_current_middle_schooler(3, 2023))
        # 幽霊: 2023(3)のあと2025に再登場はあり得ない
        self.assertTrue(
            aragyoku.is_graduated_by_grade_history(
                [(2023, 3), (2024, 2), (2025, 1)]
            )
        )
        # 学年揺れのみ: 最新2025(2)は今年度中3
        self.assertFalse(
            aragyoku.is_graduated_by_grade_history([(2024, 2), (2025, 2)])
        )
        # 2025中3は今年度卒業
        self.assertTrue(aragyoku.is_graduated_by_grade_history([(2025, 3)]))

    def test_inject_adds_aragyoku_meet_mark(self) -> None:
        aragyoku.inject_prior_year_race_marks("男子")
        marks = aragyoku.RECENT_EKIDEN_MARKS[nagomi.norm_name("今村昇磨")]
        meets = [str(m.get("meet")) for m in marks]
        self.assertTrue(any(m.startswith("荒玉") for m in meets))

    def test_pool_includes_returner_without_sb(self) -> None:
        # SBインデックス空でも前年1–2年はプールに入る
        pools = aragyoku.build_school_athlete_pools("男子", {})
        taimei = {nagomi.norm_name(n) for n, _ in pools.get("岱明中", [])}
        self.assertIn(nagomi.norm_name("佐藤央琉"), taimei)

    def test_imamura_near_prior_aragyoku(self) -> None:
        aragyoku.inject_prior_year_race_marks("男子")
        mark = nagomi.Mark(
            seconds=10 * 60 + 28.92, text="10:28.92", date="2026-07-04", source="test"
        )
        idx = {
            nagomi.norm_name("今村 昇磨"): nagomi.AthleteSB(
                name="今村 昇磨", marks={"3000m": mark}
            )
        }
        team = aragyoku.build_team(
            {
                "no": 5,
                "team": "岱明中",
                "source": "test",
                "legs": [
                    "松野 凛空",
                    "山本 哲瑠",
                    "今村 昇磨",
                    "田上 颯人",
                    "中尾 快叶",
                    "松本 空羽",
                ],
                "notes": "test",
            },
            "男子",
            idx,
            human_notes=aragyoku.empty_human_notes("男子"),
        )
        imamura = team["legs"][2]["pred"]
        self.assertIsNotNone(imamura)
        # 前年9:38＋Jr寄り。トラック10:28単独より十分速い
        self.assertLess(imamura or 999, 9 * 60 + 52)
        self.assertIn("荒玉", team["legs"][2]["note"])


class TestPredict(unittest.TestCase):
    def test_women_1500_scales(self) -> None:
        mark = nagomi.Mark(seconds=300.0, text="5:00.00", date="2026-08-01", source="test")
        ath = nagomi.AthleteSB(name="テスト", marks={"1500m": mark})
        pred, _, note = aragyoku.predict_leg("テスト", "女子", 2.0, {"テスト": ath})
        self.assertIsNotNone(pred)
        self.assertAlmostEqual(pred or 0, 415.0, places=1)
        self.assertIn("1500m", note)


class TestRecentFormBlend(unittest.TestCase):
    def test_recency_weight_prefers_newer(self) -> None:
        event = date.fromisoformat("2026-10-14")
        newer = aragyoku.recency_weight("2026-09-26", event)
        older = aragyoku.recency_weight("2026-07-01", event)
        self.assertGreater(newer, older)

    def test_imamura_faster_than_track_sb_alone(self) -> None:
        # 3000m 10:28.92 相当の遅めSBだけだと 10:30 超。直近駅伝で引き上がる。
        mark = nagomi.Mark(seconds=10 * 60 + 28.92, text="10:28.92", date="2026-07-04", source="test")
        idx = {
            nagomi.norm_name("今村 昇磨"): nagomi.AthleteSB(
                name="今村 昇磨", marks={"3000m": mark}
            )
        }
        team = aragyoku.build_team(
            {
                "no": 5,
                "team": "岱明中",
                "source": "test",
                "legs": ["松野 凛空", "山本 哲瑠", "今村 昇磨", "田上 颯人", "中尾 快叶", "松本 空羽"],
                "notes": "test",
            },
            "男子",
            idx,
            human_notes=aragyoku.empty_human_notes("男子"),
        )
        imamura = team["legs"][2]["pred"]
        self.assertIsNotNone(imamura)
        self.assertLess(imamura or 999, 10 * 60 + 10)
        self.assertIn("駅伝加味", team["legs"][2]["note"])
        self.assertRegex(team["legs"][2]["note"], r"(なごみ|ジュニア).+@\d+\.\d+km")

    def test_tagami_blends_junior_and_nagomi(self) -> None:
        mark = nagomi.Mark(seconds=4 * 60 + 33.6, text="4:33.6", date="2026-07-18", source="test")
        slow3k = nagomi.Mark(seconds=10 * 60 + 24.08, text="10:24.08", date="2026-06-13", source="test")
        idx = {
            nagomi.norm_name("田上 颯人"): nagomi.AthleteSB(
                name="田上 颯人", marks={"1500m": mark, "3000m": slow3k}
            )
        }
        pred, details, note = aragyoku.predict_leg("田上 颯人", "男子", 3.0, idx, bias_sec=0.0)
        blended, form_note = aragyoku.blend_with_recent_form(
            "田上 颯人",
            3.0,
            pred,
            aragyoku.sb_source_date(details, note),
            event_date=date.fromisoformat("2026-10-14"),
            gender="男子",
        )
        self.assertIsNotNone(blended)
        self.assertIn("ジュニアCS", form_note)
        self.assertIn("なごみ", form_note)
        # 直近実績が効き、遅い3000m単独より速く、かつ Jr/なごみの間に寄る
        self.assertLess(blended or 999, 10 * 60 + 24)
        self.assertGreater(blended or 0, 9 * 60 + 40)

    def test_ogura_yuu_uses_junior_not_slow_nagomi(self) -> None:
        """小倉由宇: なごみ不調は注入せず、Jr 8:48@2.6km で10:36級にならない。"""
        marks = aragyoku.RECENT_EKIDEN_MARKS[nagomi.norm_name("小倉由宇")]
        self.assertTrue(any(str(m.get("meet")) == "ジュニアCS" for m in marks))
        self.assertFalse(any("なごみ" in str(m.get("meet")) for m in marks))
        men_sb, _ = nagomi.load_sb_index(
            as_of="2026-09-27", gender="男子", freshness_days=152
        )
        report = aragyoku.build_report("男子", men_sb, as_of="2026-09-27")
        team = next(t for t in report["teams"] if t["team"] == "玉名高附")
        ogura = next(leg for leg in team["legs"] if "由宇" in leg["name"])
        # 男子配置: シード4番手は6区（遅→5・次遅→2の残り埋め）
        self.assertEqual(ogura["leg"], 6)
        self.assertIsNotNone(ogura["pred"])
        # Jr比例≈10:09。旧SB+バイアス10:36より十分速く、なごみ10:30より速い帯
        self.assertLess(ogura["pred"] or 999, 10 * 60 + 20)
        self.assertIn("ジュニアCS", ogura["note"])
        self.assertNotIn("なごみ", ogura["note"])

    def test_arao_yon_men_complete_from_nagomi(self) -> None:
        """荒尾第四男子: なごみOPの藤井が5区（遅→5）に入り総合が立つ。"""
        marks = aragyoku.RECENT_EKIDEN_MARKS[nagomi.norm_name("藤井祐吏")]
        self.assertTrue(any("なごみ" in str(m.get("meet")) for m in marks))
        men_sb, _ = nagomi.load_sb_index(
            as_of="2026-09-27", gender="男子", freshness_days=152
        )
        report = aragyoku.build_report("男子", men_sb, as_of="2026-09-27")
        team = next(t for t in report["teams"] if t["team"] == "荒尾第四中")
        self.assertTrue(team["complete"])
        self.assertIsNotNone(team["total"])
        self.assertEqual(team["legs"][4]["name"], "藤井 祐吏")
        self.assertIsNotNone(team["legs"][4]["pred"])
        self.assertIn("なごみ", team["legs"][4]["note"])
        # 5区は2.855km。なごみ3.0km≈10:15 → 比例≈9:45帯
        self.assertGreater(team["legs"][4]["pred"] or 0, 9 * 60 + 30)
        self.assertLess(team["legs"][4]["pred"] or 999, 10 * 60 + 5)

    def test_men_leg1_floor_8_50(self) -> None:
        floored, note = aragyoku.apply_men_leg1_floor(8 * 60 + 40.0, "男子", 1)
        self.assertAlmostEqual(floored or 0, 8 * 60 + 50.0, places=1)
        self.assertIn("8:50", note)
        kept, empty = aragyoku.apply_men_leg1_floor(9 * 60 + 0.0, "男子", 1)
        self.assertAlmostEqual(kept or 0, 9 * 60, places=1)
        self.assertEqual(empty, "")
        # 女子・他区は適用しない
        w, _ = aragyoku.apply_men_leg1_floor(8 * 60 + 40.0, "女子", 1)
        self.assertAlmostEqual(w or 0, 8 * 60 + 40.0, places=1)

    def test_track_3000m_cap_pulls_slow_prior_year_up(self) -> None:
        """直近3000m 9:14 があるのに前年比例で 9:55 になるのをトラック基準へ。"""
        m3000 = nagomi.Mark(
            seconds=9 * 60 + 14.53, text="9:14.53", date="2026-09-12", source="test"
        )
        marks = {"3000m": m3000}
        slow = 9 * 60 + 55.1
        capped, note = aragyoku.apply_men_track_3000m_cap(slow, "男子", marks, 3.0)
        expect = (9 * 60 + 14.53) + aragyoku.MEN_TRACK_3000_ROAD_ADD_SEC
        self.assertAlmostEqual(capped or 0, expect, places=1)
        self.assertIn("3000mトラック優先", note)
        self.assertIn("9:14.53", note)
        # すでに速い予想は据え置き
        fast = 9 * 60 + 0.0
        kept, empty = aragyoku.apply_men_track_3000m_cap(fast, "男子", marks, 3.0)
        self.assertAlmostEqual(kept or 0, fast, places=1)
        self.assertEqual(empty, "")
        # 女子は適用しない
        w, _ = aragyoku.apply_men_track_3000m_cap(slow, "女子", marks, 3.0)
        self.assertAlmostEqual(w or 0, slow, places=1)

    def test_gyokuryo_kakimoto_near_track_3000m(self) -> None:
        """玉陵・柿本: 3000m 9:14 があるのに前年で 9:55 にならない。"""
        m1500 = nagomi.Mark(
            seconds=4 * 60 + 19.41, text="4:19.41", date="2026-06-14", source="test"
        )
        m3000 = nagomi.Mark(
            seconds=9 * 60 + 14.53, text="9:14.53", date="2026-09-12", source="test"
        )
        key = nagomi.norm_name("柿本晴仁")
        # 前年荒玉のみ（遅い）を注入
        aragyoku.RECENT_EKIDEN_MARKS[key] = [
            {"date": "2025-10-15", "km": 2.855, "sec": 9 * 60 + 35, "meet": "荒玉2025"},
        ]
        try:
            idx = {
                key: nagomi.AthleteSB(
                    name="柿本晴仁", marks={"1500m": m1500, "3000m": m3000}
                )
            }
            team = aragyoku.build_team(
                {
                    "no": 3,
                    "team": "玉陵中",
                    "source": "test",
                    "legs": ["柿本晴仁", "永田來夢", "辛嶋大宙", "宮川晴", "内野翼", "松島颯希"],
                    "notes": "test",
                },
                "男子",
                idx,
                human_notes=aragyoku.empty_human_notes("男子"),
            )
            pred = team["legs"][0]["pred"]
            self.assertIsNotNone(pred)
            # 9:14 + 5s 近傍。前年比例の 9:55 帯には戻さない
            self.assertLess(pred or 999, 9 * 60 + 30)
            self.assertGreater(pred or 0, 9 * 60 + 10)
            self.assertIn("3000mトラック優先", team["legs"][0]["note"])
        finally:
            aragyoku.RECENT_EKIDEN_MARKS.pop(key, None)


class TestHumanNotes(unittest.TestCase):
    def test_delta_sec_slows_and_speeds(self) -> None:
        notes = {
            "adjustments": [
                {"athlete": "今村 昇磨", "delta_sec": -8, "reason": "覚醒"},
            ]
        }
        out, bit = aragyoku.apply_human_adjustments(
            600.0, athlete="今村 昇磨", team="岱明中", leg_no=3, notes=notes
        )
        self.assertAlmostEqual(out or 0, 592.0, places=1)
        self.assertIn("人間-8s", bit)
        self.assertIn("覚醒", bit)

    def test_team_leg_min_sec(self) -> None:
        notes = {
            "adjustments": [
                {
                    "team": "菊水中",
                    "leg": 1,
                    "min_sec": 8 * 60 + 50,
                    "reason": "現実線",
                }
            ]
        }
        out, bit = aragyoku.apply_human_adjustments(
            8 * 60 + 40.0, athlete="隈部 侑成", team="菊水中", leg_no=1, notes=notes
        )
        self.assertAlmostEqual(out or 0, 8 * 60 + 50.0, places=1)
        self.assertIn("人間min", bit)

    def test_team_only_delta_applies_all_legs(self) -> None:
        """team のみ指定は校の全区間に適用（南関男子フォーム落ちなど）。"""
        notes = {
            "adjustments": [
                {
                    "team": "南関中",
                    "delta_sec": 20,
                    "reason": "直近フォーム上がらず",
                }
            ]
        }
        for leg_no in (1, 3, 6):
            out, bit = aragyoku.apply_human_adjustments(
                600.0, athlete="永清 芯", team="南関中", leg_no=leg_no, notes=notes
            )
            self.assertAlmostEqual(out or 0, 620.0, places=1)
            self.assertIn("人間+20s", bit)
        other, empty = aragyoku.apply_human_adjustments(
            600.0, athlete="松野 凛空", team="岱明中", leg_no=1, notes=notes
        )
        self.assertAlmostEqual(other or 0, 600.0, places=1)
        self.assertEqual(empty, "")

    def test_set_sec_overrides(self) -> None:
        notes = {
            "adjustments": [
                {"athlete": "村上 咲稀", "set_sec": 640.0, "reason": "固定"},
            ]
        }
        out, _ = aragyoku.apply_human_adjustments(
            600.0, athlete="村上 咲稀", team="岱明中", leg_no=1, notes=notes
        )
        self.assertAlmostEqual(out or 0, 640.0, places=1)

    def test_build_team_applies_human_notes(self) -> None:
        notes = {
            "memo": "テストメモ",
            "updated": "2026-09-27",
            "adjustments": [
                {"athlete": "今村 昇磨", "delta_sec": -10, "reason": "test"},
            ],
        }
        mark = nagomi.Mark(seconds=10 * 60 + 28.92, text="10:28.92", date="2026-07-04", source="test")
        idx = {
            nagomi.norm_name("今村 昇磨"): nagomi.AthleteSB(
                name="今村 昇磨", marks={"3000m": mark}
            )
        }
        empty = aragyoku.empty_human_notes("男子")
        base = aragyoku.build_team(
            {
                "no": 5,
                "team": "岱明中",
                "source": "test",
                "legs": ["松野 凛空", "山本 哲瑠", "今村 昇磨", "田上 颯人", "中尾 快叶", "松本 空羽"],
                "notes": "test",
            },
            "男子",
            idx,
            human_notes=empty,
        )
        adj = aragyoku.build_team(
            {
                "no": 5,
                "team": "岱明中",
                "source": "test",
                "legs": ["松野 凛空", "山本 哲瑠", "今村 昇磨", "田上 颯人", "中尾 快叶", "松本 空羽"],
                "notes": "test",
            },
            "男子",
            idx,
            human_notes=notes,
        )
        self.assertIsNotNone(base["legs"][2]["pred"])
        self.assertIsNotNone(adj["legs"][2]["pred"])
        self.assertAlmostEqual(
            (adj["legs"][2]["pred"] or 0) - (base["legs"][2]["pred"] or 0),
            -10.0,
            places=1,
        )
        self.assertIn("人間-10s", adj["legs"][2]["note"])
        self.assertEqual(adj["human_memo"], "テストメモ")

    def test_taimei_set_sec_matsuno_tagami_yamasaki(self) -> None:
        """岱明: 松野9:20 / 田上4区9:40 / 山﨑2区6:50 を人間考慮 set_sec で固定。"""
        men_notes = aragyoku.load_human_notes("男子")
        women_notes = aragyoku.load_human_notes("女子")
        men_adj = {
            (a.get("athlete"), a.get("team"), a.get("leg")): a
            for a in men_notes.get("adjustments") or []
        }
        women_adj = {
            (a.get("athlete"), a.get("team"), a.get("leg")): a
            for a in women_notes.get("adjustments") or []
        }
        self.assertEqual(men_adj[("松野 凛空", None, None)]["set_sec"], 9 * 60 + 20)
        self.assertEqual(
            men_adj[("田上 颯人", "岱明中", 4)]["set_sec"], 9 * 60 + 40
        )
        self.assertEqual(
            women_adj[("山﨑 莉奈", "岱明中", 2)]["set_sec"], 6 * 60 + 50
        )

        men_sb, _ = nagomi.load_sb_index(
            as_of="2026-09-27", gender="男子", freshness_days=152
        )
        women_sb, _ = nagomi.load_sb_index(
            as_of="2026-09-27", gender="女子", freshness_days=152
        )
        men_row = next(
            r for r in aragyoku.get_provisional_orders("男子", men_sb) if r["team"] == "岱明中"
        )
        women_row = next(
            r
            for r in aragyoku.get_provisional_orders("女子", women_sb)
            if r["team"] == "岱明中"
        )
        men_team = aragyoku.build_team(
            men_row, "男子", men_sb, human_notes=men_notes
        )
        women_team = aragyoku.build_team(
            women_row, "女子", women_sb, human_notes=women_notes
        )
        self.assertAlmostEqual(men_team["legs"][0]["pred"] or 0, 9 * 60 + 20, places=1)
        self.assertAlmostEqual(men_team["legs"][3]["pred"] or 0, 9 * 60 + 40, places=1)
        self.assertAlmostEqual(women_team["legs"][1]["pred"] or 0, 6 * 60 + 50, places=1)
        self.assertIn("人間set", men_team["legs"][0]["note"])
        self.assertIn("人間set", men_team["legs"][3]["note"])
        self.assertIn("人間set", women_team["legs"][1]["note"])


class TestWomenRaceFormPrimary(unittest.TestCase):
    def test_nankan_slowest_near_nagomi_not_hieshima(self) -> None:
        """南関女子の最遅はなごみβの原賀（7:53）級。稗島9:07を仮置きしない。"""
        women_sb, _ = nagomi.load_sb_index(
            as_of="2026-09-27", gender="女子", freshness_days=152
        )
        row = next(
            r for r in aragyoku.get_provisional_orders("女子", women_sb) if r["team"] == "南関中"
        )
        self.assertIn("原賀 美和", row["legs"])
        self.assertNotIn("稗島 琴都", row["legs"])
        team = aragyoku.build_team(
            row, "女子", women_sb, human_notes=aragyoku.empty_human_notes("女子")
        )
        preds = [leg["pred"] for leg in team["legs"] if leg["pred"] is not None]
        self.assertEqual(len(preds), 5)
        # 短中継2.0km換算で最遅でもなごみ原賀7:53＋余裕（≈8:20）より速い側
        mid_preds = [
            leg["pred"]
            for leg in team["legs"]
            if leg["leg"] in (2, 3, 4) and leg["pred"] is not None
        ]
        self.assertTrue(mid_preds)
        self.assertLess(max(mid_preds), 8 * 60 + 20)
        haruga = next(leg for leg in team["legs"] if "原賀" in leg["name"])
        self.assertIsNotNone(haruga["pred"])
        self.assertAlmostEqual(haruga["pred"] or 0, 7 * 60 + 53, delta=25)
        self.assertIn("なごみ", haruga["note"])

    def test_murakami_3k_near_junior_not_optimistic_sb(self) -> None:
        # 楽観的な1500SBだけだと荒玉3kmが速すぎる。Jr 9:58@2.7 → ~11:04 近傍へ寄る。
        mark = nagomi.Mark(seconds=4 * 60 + 53.85, text="4:53.85", date="2026-07-18", source="test")
        idx = {
            nagomi.norm_name("村上 咲稀"): nagomi.AthleteSB(
                name="村上 咲稀", marks={"1500m": mark}
            )
        }
        pred, details, note = aragyoku.predict_leg(
            "村上 咲稀", "女子", 3.0, idx, bias_sec=0.0
        )
        blended, form_note = aragyoku.blend_with_recent_form(
            "村上 咲稀",
            3.0,
            pred,
            aragyoku.sb_source_date(details, note),
            event_date=date.fromisoformat("2026-10-14"),
            gender="女子",
        )
        self.assertIn("ジュニアCS", form_note)
        self.assertIsNotNone(blended)
        # Jr比例 9:58*(3/2.7)≈11:04。なごみ寄りでやや速いが、楽観SB単独より明らかに遅い。
        self.assertGreater(blended or 0, 10 * 60 + 30)
        self.assertLess(blended or 999, 11 * 60 + 20)
        self.assertGreater(blended or 0, (pred or 0) + 20)

    def test_women_sb_weight_scale_constant(self) -> None:
        self.assertLess(aragyoku.WOMEN_SB_WEIGHT_SCALE, 0.5)
        self.assertGreater(aragyoku.WOMEN_SB_WEIGHT_SCALE, 0.0)


class TestYoyCourseGrowth(unittest.TestCase):
    def tearDown(self) -> None:
        # テスト用キーを掃除し、角田は raw に戻す
        for fake in ("遅い選手", "伸び選手", "復帰のみ", "距離差選手"):
            aragyoku.RECENT_EKIDEN_MARKS.pop(nagomi.norm_name(fake), None)
        key = nagomi.norm_name("角田 亜美")
        raw = aragyoku._RECENT_EKIDEN_MARKS_RAW.get("角田 亜美")
        if raw is not None:
            aragyoku.RECENT_EKIDEN_MARKS[key] = list(raw)
        else:
            aragyoku.RECENT_EKIDEN_MARKS.pop(key, None)

    def test_tsunoda_faster_than_prior_year_7_44(self) -> None:
        """去年 3区 7:44 + 今年フォーム同程度 → 前年より速く。"""
        key = nagomi.norm_name("角田 亜美")
        aragyoku.RECENT_EKIDEN_MARKS[key] = [
            {"date": "2026-09-26", "km": 2.3, "sec": 542, "meet": "ジュニアOP"},
            {"date": "2026-09-20", "km": 2.0, "sec": 468, "meet": "なごみ"},
            {"date": "2025-10-15", "km": 2.0, "sec": 7 * 60 + 44, "meet": "荒玉2025"},
        ]
        blended = 7 * 60 + 47.7  # ブレンドは前年よりやや遅い想定
        grown, note = aragyoku.apply_yoy_course_growth("角田 亜美", 2.0, blended)
        self.assertIsNotNone(grown)
        self.assertLess(grown or 999, 7 * 60 + 44)
        self.assertIn("前年伸び", note)
        # デフォルト 2%: 464 * 0.98 ≈ 454.7
        self.assertAlmostEqual(grown or 0, (7 * 60 + 44) * 0.98, delta=1.0)
        self.assertIn("荒玉2025", note)
        self.assertIn("7:44", note)

    def test_clearly_slower_form_skips_growth(self) -> None:
        key = nagomi.norm_name("遅い選手")
        aragyoku.RECENT_EKIDEN_MARKS[key] = [
            {"date": "2026-09-20", "km": 2.0, "sec": 8 * 60 + 30, "meet": "なごみ"},
            {"date": "2025-10-15", "km": 2.0, "sec": 7 * 60 + 44, "meet": "荒玉2025"},
        ]
        blended = 8 * 60 + 10.0
        out, note = aragyoku.apply_yoy_course_growth("遅い選手", 2.0, blended)
        self.assertAlmostEqual(out or 0, blended, places=1)
        self.assertEqual(note, "")

    def test_faster_current_form_uses_growth_floor(self) -> None:
        key = nagomi.norm_name("伸び選手")
        aragyoku.RECENT_EKIDEN_MARKS[key] = [
            {"date": "2026-09-20", "km": 2.0, "sec": 7 * 60 + 20, "meet": "なごみ"},
            {"date": "2025-10-15", "km": 2.0, "sec": 7 * 60 + 44, "meet": "荒玉2025"},
        ]
        # ブレンドがまだ前年寄りで遅い場合、成長予想で切り下げる
        blended = 7 * 60 + 40.0
        grown, note = aragyoku.apply_yoy_course_growth("伸び選手", 2.0, blended)
        self.assertIsNotNone(grown)
        self.assertLess(grown or 999, blended)
        self.assertIn("前年伸び", note)

    def test_prior_only_light_growth(self) -> None:
        key = nagomi.norm_name("復帰のみ")
        aragyoku.RECENT_EKIDEN_MARKS[key] = [
            {"date": "2025-10-15", "km": 2.0, "sec": 8 * 60 + 0, "meet": "荒玉2025"},
        ]
        blended = 8 * 60 + 0.0
        grown, note = aragyoku.apply_yoy_course_growth("復帰のみ", 2.0, blended)
        self.assertIsNotNone(grown)
        self.assertLess(grown or 999, blended)
        self.assertAlmostEqual(
            grown or 0,
            480.0 * (1.0 - aragyoku.YOY_PRIOR_ONLY_IMPROVEMENT),
            delta=0.5,
        )
        self.assertIn("前年伸び", note)

    def test_distant_jr_does_not_overstate_vs_same_distance_nagomi(self) -> None:
        """距離の離れた Jr 比例だけで 5% 伸びを強制しない（なごみ同距離を優先）。"""
        key = nagomi.norm_name("距離差選手")
        aragyoku.RECENT_EKIDEN_MARKS[key] = [
            {"date": "2026-09-26", "km": 2.3, "sec": 8 * 60 + 22, "meet": "ジュニアCS"},
            {"date": "2026-09-20", "km": 2.0, "sec": 8 * 60 + 1, "meet": "なごみ"},
            {"date": "2025-10-15", "km": 1.855, "sec": 7 * 60 + 12, "meet": "荒玉2025"},
        ]
        prior_2k = (7 * 60 + 12) * 2.0 / 1.855
        blended = prior_2k + 20.0
        grown, note = aragyoku.apply_yoy_course_growth("距離差選手", 2.0, blended)
        # なごみ 8:01 は前年比例より遅い → 伸びなし、または最大でもデフォルト2%止まり
        if note:
            self.assertIn("前年伸び", note)
            self.assertIn("×-2%", note)
            self.assertNotIn("×-5%", note)
        else:
            self.assertAlmostEqual(grown or 0, blended, places=1)


class TestPriorBTeamTamana(unittest.TestCase):
    def test_b_team_returners_include_tamana_kameki(self) -> None:
        rows = aragyoku.load_prior_year_returners("女子")
        names = {nagomi.norm_name(r["name"]) for r in rows}
        self.assertIn(nagomi.norm_name("亀木"), names)
        self.assertIn(nagomi.norm_name("結菜"), names)
        self.assertIn(nagomi.norm_name("清藤結唯"), names)
        kameki = next(r for r in rows if nagomi.norm_name(r["name"]) == nagomi.norm_name("亀木"))
        self.assertEqual(kameki["school"], "玉名中")
        self.assertEqual(kameki["sec"], 7 * 60 + 12)
        self.assertIn("B", kameki["meet"])

    def test_tamana_women_order_fully_filled(self) -> None:
        women_sb, _ = nagomi.load_sb_index(
            as_of="2026-09-27", gender="女子", freshness_days=152
        )
        orders = aragyoku.get_provisional_orders("女子", women_sb)
        tamana = next(r for r in orders if r["team"] == "玉名中")
        self.assertTrue(all(str(n).strip() for n in tamana["legs"]))
        self.assertEqual(tamana["legs"][0], "清藤 結唯")
        self.assertEqual(tamana["legs"][2], "川原 芽吹")
        self.assertEqual(tamana["legs"][4], "水本 星夏")
        self.assertNotIn("川原 芽吹", [tamana["legs"][0], tamana["legs"][4]])
        report = aragyoku.build_report("女子", women_sb, as_of="2026-09-27")
        team = next(t for t in report["teams"] if t["team"] == "玉名中")
        self.assertTrue(team["complete"])
        # 亀木 2区配置でも前年7:12実績で予想が出る
        kameki_leg = next(leg for leg in team["legs"] if "亀木" in leg["name"])
        self.assertIsNotNone(kameki_leg["pred"])
        self.assertLess(kameki_leg["pred"] or 999, 8 * 60)


class TestSchoolScenarioYoy(unittest.TestCase):
    def test_parse_clock_and_signed(self) -> None:
        self.assertAlmostEqual(aragyoku.parse_clock_to_sec("56:17") or 0, 56 * 60 + 17)
        self.assertAlmostEqual(aragyoku.parse_clock_to_sec("9:14.5") or 0, 9 * 60 + 14.5)
        self.assertEqual(aragyoku.fmt_signed_clock(-37.0), "-0:37")
        self.assertEqual(aragyoku.fmt_signed_clock(75.0), "+1:15")

    def test_prior_standings_men_first_is_kikusui(self) -> None:
        prior = aragyoku.load_prior_year_team_standings("男子")
        self.assertGreaterEqual(len(prior), 5)
        self.assertEqual(prior[0]["rank"], 1)
        self.assertEqual(prior[0]["school"], "菊水中")
        self.assertAlmostEqual(prior[0]["total_sec"], 56 * 60 + 17)

    def test_yoy_rows_compare_same_rank(self) -> None:
        prior = [
            {
                "rank": 1,
                "team_raw": "菊水",
                "school": "菊水中",
                "total_sec": 56 * 60 + 17,
                "total_text": "56:17",
                "year": 2025,
            },
            {
                "rank": 2,
                "team_raw": "玉陵",
                "school": "玉陵中",
                "total_sec": 58 * 60 + 2,
                "total_text": "58:02",
                "year": 2025,
            },
        ]
        report = {
            "ranked": [
                {"rank": 1, "team": "玉陵中", "total": 56 * 60 + 54.0, "legs": []},
                {"rank": 2, "team": "菊水中", "total": 57 * 60 + 13.0, "legs": []},
            ]
        }
        rows = aragyoku.build_yoy_rank_rows(report, prior)
        self.assertEqual(rows[0]["team"], "玉陵中")
        # 今年1位 56:54 − 昨年1位 56:17 = +37s（昨年同順位より遅い）
        self.assertAlmostEqual(rows[0]["vs_same_rank_sec"] or 0, 37.0, places=0)
        # 同校（玉陵）は昨年2位 58:02 → 今年の方が速い
        self.assertLess(rows[0]["vs_same_school_sec"] or 0, 0)

    def test_render_scenario_contains_yoy_and_outlook(self) -> None:
        women_sb, _ = nagomi.load_sb_index(
            as_of="2026-09-27", gender="女子", freshness_days=152
        )
        men_sb, _ = nagomi.load_sb_index(
            as_of="2026-09-27", gender="男子", freshness_days=152
        )
        women = aragyoku.build_report("女子", women_sb, as_of="2026-09-27")
        men = aragyoku.build_report("男子", men_sb, as_of="2026-09-27")
        md = aragyoku.render_school_scenario_md(women, men, as_of="2026-09-27")
        self.assertIn("昨年同順位とのレベル差", md)
        self.assertIn("今年どうなるか", md)
        self.assertIn("同順位差", md)
        self.assertIn("玉陵中", md)
        self.assertIn("今年の見立て", md)


class TestRankTableNames(unittest.TestCase):
    def test_fmt_leg_pred_cell_includes_athlete_name(self) -> None:
        det = {
            "name": "松野 凛空",
            "pred": 560.0,
            "pred_used": 560.0,
            "pred_cum": 560.0,
            "pred_sec_rank": 4,
            "pred_cum_rank": 4,
        }
        cell = aragyoku.fmt_leg_pred_cell(det)
        self.assertIn("松野凛空", cell)
        self.assertIn("(4)9:20.0", cell)
        self.assertTrue(cell.startswith("松野凛空"))

    def test_ranked_md_cells_include_names(self) -> None:
        men_sb, _ = nagomi.load_sb_index(
            as_of="2026-09-27", gender="男子", freshness_days=152
        )
        report = aragyoku.build_report("男子", men_sb, as_of="2026-09-27")
        md = aragyoku.render_markdown(report, freshness=152)
        self.assertIn("選手名 (通過順)通過予想", md)
        # 総合順位表の岱明1区セル（通過順は他校1区次第で変動し得る）
        self.assertRegex(md, r"松野凛空 \(\d+\)9:20\.0 / \(\d+\)9:20\.0")


if __name__ == "__main__":
    unittest.main()
