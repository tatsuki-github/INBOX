#!/usr/bin/env python3
"""なごみ SB 予実ギャップ分類・HTML 生成の単体テスト。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import nagomi_sb_gap_analysis as gap  # noqa: E402


def test_classify_three_level_compat_with_single_threshold() -> None:
    """hard 省略時は旧 3 段階相当（少し上/下は出ない）。"""
    assert gap.classify_delta(-25.0, gap.LEG_THRESHOLD_SEC) == "beat"
    assert gap.classify_delta(-5.0, gap.LEG_THRESHOLD_SEC) == "ok"
    assert gap.classify_delta(5.0, gap.LEG_THRESHOLD_SEC) == "ok"
    assert gap.classify_delta(25.0, gap.LEG_THRESHOLD_SEC) == "miss"
    assert gap.classify_delta(None, gap.LEG_THRESHOLD_SEC) == "unknown"


def test_classify_five_level_soft_hard() -> None:
    soft, hard = 10.0, 20.0
    assert gap.classify_delta(-20.0, soft, hard) == "beat"
    assert gap.classify_delta(-15.0, soft, hard) == "slight_beat"
    assert gap.classify_delta(-10.0, soft, hard) == "slight_beat"
    assert gap.classify_delta(-9.9, soft, hard) == "ok"
    assert gap.classify_delta(0.0, soft, hard) == "ok"
    assert gap.classify_delta(9.9, soft, hard) == "ok"
    assert gap.classify_delta(10.0, soft, hard) == "slight_miss"
    assert gap.classify_delta(19.9, soft, hard) == "slight_miss"
    assert gap.classify_delta(20.0, soft, hard) == "miss"


def test_classify_team_uses_team_band() -> None:
    soft, hard = gap.team_band("女子")
    assert soft == 30.0 and hard == 60.0
    assert gap.classify_delta(-70.0, soft, hard) == "beat"
    assert gap.classify_delta(-45.0, soft, hard) == "slight_beat"
    assert gap.classify_delta(20.0, soft, hard) == "ok"
    assert gap.classify_delta(45.0, soft, hard) == "slight_miss"
    assert gap.classify_delta(70.0, soft, hard) == "miss"
    assert gap.team_band("男子") == (60.0, 120.0)
    assert gap.leg_band("男子") == (15.0, 30.0)
    assert gap.team_threshold("男子") == 120.0
    assert gap.leg_threshold("男子") == 30.0


def test_build_analysis_rows_men_uses_wider_band() -> None:
    report = {
        "gender": "男子",
        "teams": [
            {
                "no": 1,
                "team": "X",
                "official": True,
                "actual_rank": 1,
                "rank_ref": 1,
                "actual_total": 2500.0,
                "total_ref": 2400.0,
                "total_delta": 100.0,
                "imputed": False,
                "legs": [
                    {
                        "leg": 1,
                        "name": "選手A",
                        "pred": 600.0,
                        "actual": 625.0,
                        "delta": 25.0,
                        "note": "",
                    }
                ],
            }
        ],
    }
    teams, legs = gap.build_analysis_rows(report, year=2026)
    assert teams[0]["class"] == "slight_miss"  # soft 60 ≤ 100 < hard 120
    assert legs[0]["class"] == "slight_miss"  # soft 15 ≤ 25 < hard 30


def test_label_ja() -> None:
    assert gap.label_ja("beat") == "大きく上回った"
    assert gap.label_ja("slight_beat") == "少し上回った"
    assert gap.label_ja("ok") == "妥当"
    assert gap.label_ja("slight_miss") == "少し下回った"
    assert gap.label_ja("miss") == "大きく下回った"
    assert gap.label_ja("unknown") == "判定不可"


def test_summarize_counts() -> None:
    rows = [
        {"class": "beat"},
        {"class": "slight_beat"},
        {"class": "ok"},
        {"class": "slight_miss"},
        {"class": "miss"},
        {"class": "unknown"},
    ]
    counts = gap.summarize_counts(rows)
    assert counts == {
        "beat": 1,
        "slight_beat": 1,
        "ok": 1,
        "slight_miss": 1,
        "miss": 1,
        "unknown": 1,
    }


def test_attach_actuals_by_no_matches_legs() -> None:
    report = {
        "teams": [
            {
                "no": 9,
                "team": "岱明中学校 A",
                "total_ref": 1800.0,
                "rank_ref": 5,
                "official": True,
                "legs": [
                    {"leg": 1, "name": "A", "pred": 450.0},
                    {"leg": 2, "name": "B", "pred": 450.0},
                    {"leg": 3, "name": "C", "pred": 450.0},
                    {"leg": 4, "name": "D", "pred": 450.0},
                ],
            }
        ]
    }
    results = [
        {
            "no": 9,
            "team": "岱明A",
            "rank": 6,
            "total": "30:18",
            "legs": [
                {"name": "A", "split": "7:38"},
                {"name": "B", "split": "7:07"},
                {"name": "C", "split": "7:45"},
                {"name": "D", "split": "7:48"},
            ],
        }
    ]
    gap.attach_actuals_by_no(report, results)
    row = report["teams"][0]
    assert row["actual_rank"] == 6
    assert abs(row["actual_total"] - 1818.0) < 0.1
    assert abs(row["total_delta"] - 18.0) < 0.1
    assert row["legs"][1]["delta"] is not None
    assert row["legs"][1]["delta"] < 0  # 予想より速い


def test_build_analysis_rows_adds_class() -> None:
    report = {
        "gender": "女子",
        "teams": [
            {
                "no": 1,
                "team": "金栗",
                "official": True,
                "actual_rank": 1,
                "rank_ref": 1,
                "actual_total": 1600.0,
                "total_ref": 1650.0,
                "total_delta": -50.0,
                "imputed": False,
                "legs": [
                    {
                        "leg": 1,
                        "name": "選手A",
                        "pred": 400.0,
                        "actual": 380.0,
                        "delta": -20.0,
                        "note": "",
                    },
                    {
                        "leg": 2,
                        "name": "選手B",
                        "pred": 400.0,
                        "actual": 420.0,
                        "delta": 20.0,
                        "note": "",
                    },
                    {
                        "leg": 3,
                        "name": "選手C",
                        "pred": 400.0,
                        "actual": 412.0,
                        "delta": 12.0,
                        "note": "",
                    },
                ],
            }
        ],
    }
    teams, legs = gap.build_analysis_rows(report, year=2026)
    assert teams[0]["class"] == "slight_beat"  # soft 30 ≤ |−50| < hard 60
    assert legs[0]["class"] == "beat"  # −20 <= −hard 20
    assert legs[1]["class"] == "miss"  # +20 >= hard 20
    assert legs[2]["class"] == "slight_miss"  # soft 10 ≤ 12 < hard 20


def test_render_html_contains_charts_and_labels() -> None:
    payload = {
        "years": [
            {
                "year": 2026,
                "event_date": "2026-09-20",
                "as_of": "2026-09-18",
                "genders": [
                    {
                        "gender": "女子",
                        "teams": [
                            {
                                "team": "岱明A",
                                "actual_rank": 6,
                                "rank_ref": 8,
                                "actual_total": 1818.0,
                                "total_ref": 1850.0,
                                "total_delta": -32.0,
                                "class": "slight_beat",
                                "imputed": False,
                            }
                        ],
                        "legs": [
                            {
                                "team": "金栗PROJECT A",
                                "leg": 1,
                                "name": "坂井優花",
                                "actual": 400.0,
                                "pred": 468.0,
                                "delta": -68.0,
                                "class": "beat",
                                "note": "",
                            }
                        ],
                    }
                ],
            }
        ]
    }
    html = gap.render_html(payload)
    assert "大きく上回った" in html
    assert "少し上回った" in html
    assert "少し下回った" in html
    assert "妥当" in html
    assert "大きく下回った" in html
    assert "5段階" in html
    assert 'id="chart-team-2026-女子"' in html
    assert "村上咲稀" not in html  # replaced fixture
    assert "金栗PROJECT A 1区 坂井優花" in html
    assert 'class="bar-row"' in html
    assert 'class="bar-label"' in html
    assert "overflow:visible" in html
    assert "--slight-beat" in html


def test_bar_chart_keeps_long_labels_outside_track() -> None:
    rows = [
        {
            "label": "金栗PROJECT A 1区 坂井優花",
            "delta": -68.0,
            "class": "beat",
        },
        {
            "label": "合志楓の森 4区 選手名",
            "delta": -56.7,
            "class": "slight_beat",
        },
    ]
    chart = gap._bar_chart_svg(
        rows, value_key="delta", label_key="label", chart_id="chart-leg-test"
    )
    assert "金栗PROJECT A 1区 坂井優花" in chart
    assert "合志楓の森 4区 選手名" in chart
    assert 'class="bar-label"' in chart
    assert "<svg" not in chart  # HTML layout, not clipped SVG text
    assert "−1:08.0" in chart or "−1:08" in chart


def test_is_arato_tamana_team() -> None:
    assert gap.is_arato_tamana_team("岱明A")
    assert gap.is_arato_tamana_team("玉名アスリーツB")
    assert gap.is_arato_tamana_team("南関α")
    assert gap.is_arato_tamana_team("金栗PROJECT A")
    assert gap.is_arato_tamana_team("荒尾第四")
    assert not gap.is_arato_tamana_team("NJAC")  # 選手単位のみ
    assert not gap.is_arato_tamana_team("富合")
    assert not gap.is_arato_tamana_team("合志楓の森")


def test_resolve_arato_school_njac_and_overrides() -> None:
    cfg = {
        "affiliation_keywords": list(gap.ARATO_TAMANA_KEYWORDS),
        "school_analysis_affiliation_overrides": {
            "金栗PROJECT": "菊水中",
            "玉名アスリーツ": "玉陵中",
        },
        "school_analysis_athlete_affiliation_overrides": {
            "ATRC": {
                "default": "荒尾第四中",
                "athletes": {"清藤結唯": "玉名中", "猿渡愛梨": "長洲中"},
            },
            "NJAC": {"athletes": {"濱北愛": "長洲中"}},
            "金栗PROJECT": {
                "athletes": {"居石華音": "玉陵中", "庄山瑠那": "荒尾三中"},
            },
        },
        "exclude_name_keywords": ["有尾明莉", "秀島恋莉", "竹熊紗良"],
        "exclude_when_affiliation_contains": "金栗",
    }
    assert gap.resolve_arato_school("NJAC", "濱北愛", cfg) == "長洲中"
    assert gap.resolve_arato_school("NJAC", "他の選手", cfg) is None
    assert gap.resolve_arato_school("金栗PROJECT A", "居石華音", cfg) == "玉陵中"
    assert gap.resolve_arato_school("金栗PROJECT A", "庄山瑠那", cfg) == "荒尾三中"
    assert gap.resolve_arato_school("金栗PROJECT B", "金澤", cfg) == "菊水中"
    assert gap.resolve_arato_school("金栗PROJECT A", "有尾明莉", cfg) is None
    assert gap.resolve_arato_school("金栗PROJECT B", "竹熊紗良", cfg) is None
    assert gap.resolve_arato_school("金栗PROJECT B", "竹熊 紗良", cfg) is None
    assert gap.resolve_arato_school("ATRC", "清藤結唯", cfg) == "玉名中"
    assert gap.resolve_arato_school("ATRC", "中尾", cfg) == "荒尾第四中"
    assert gap.resolve_arato_school("南関α", "福山", cfg) == "南関中"
    assert gap.resolve_arato_school("岱明A", "村上", cfg) == "岱明中"
    assert gap.resolve_arato_school("富合", "外", cfg) is None


def test_build_arato_school_topn_ranking() -> None:
    cfg = {
        "affiliation_keywords": list(gap.ARATO_TAMANA_KEYWORDS),
        "school_analysis_affiliation_overrides": {"金栗PROJECT": "菊水中"},
        "school_analysis_athlete_affiliation_overrides": {
            "NJAC": {"athletes": {"濱北愛": "長洲中"}},
            "金栗PROJECT": {"athletes": {"居石華音": "玉陵中"}},
        },
        "exclude_name_keywords": ["有尾明莉"],
        "exclude_when_affiliation_contains": "金栗",
    }
    # 南関: α+β で 5 人以上 → 女子ランキング対象（平均5）
    legs = []
    for i, name in enumerate(["A", "B", "C", "D", "E", "F", "G"], start=1):
        legs.append(
            {
                "team": "南関α" if i <= 4 else "南関β",
                "leg": ((i - 1) % 4) + 1,
                "name": f"南関{name}",
                "actual": 400.0 + i,
                "pred": 410.0,
                "delta": -10.0 + i,
                "class": "ok",
                "gender": "女子",
            }
        )
    legs.extend(
        [
            {
                "team": "NJAC",
                "leg": 1,
                "name": "濱北愛",
                "actual": 390.0,
                "pred": 400.0,
                "delta": -10.0,
                "class": "slight_beat",
                "gender": "女子",
            },
            {
                "team": "NJAC",
                "leg": 2,
                "name": "除外男子",
                "actual": 380.0,
                "pred": 380.0,
                "delta": 0.0,
                "class": "ok",
                "gender": "女子",
            },
            {
                "team": "金栗PROJECT A",
                "leg": 1,
                "name": "居石華音",
                "actual": 395.0,
                "pred": 400.0,
                "delta": -5.0,
                "class": "ok",
                "gender": "女子",
            },
            {
                "team": "金栗PROJECT A",
                "leg": 2,
                "name": "有尾明莉",
                "actual": 385.0,
                "pred": 390.0,
                "delta": -5.0,
                "class": "ok",
                "gender": "女子",
            },
            {
                "team": "岱明A",
                "leg": 1,
                "name": "村上",
                "actual": 427.0,
                "pred": 406.0,
                "delta": 21.0,
                "class": "miss",
                "gender": "女子",
            },
            {
                "team": "富合",
                "leg": 1,
                "name": "外部",
                "actual": 350.0,
                "pred": 350.0,
                "delta": 0.0,
                "class": "ok",
                "gender": "女子",
            },
        ]
    )
    ranked = gap.build_arato_school_topn_ranking(legs, gender="女子", config=cfg)
    complete = [e for e in ranked if e.get("complete")]
    short = [e for e in ranked if not e.get("complete")]
    assert gap.school_avg_n("女子") == 5
    assert len(complete) == 1
    assert complete[0]["school"] == "南関中"
    assert complete[0]["rank"] == 1
    assert complete[0]["top_n"] == 5
    assert complete[0]["avg_n"] == 5
    assert len(complete[0]["members"]) == 7  # 内訳は全員
    assert [m["name"] for m in complete[0]["members"]] == [
        "南関A",
        "南関B",
        "南関C",
        "南関D",
        "南関E",
        "南関F",
        "南関G",
    ]
    assert complete[0]["members"][4]["in_average"] is True
    assert complete[0]["members"][5]["in_average"] is False
    assert abs(complete[0]["average"] - (401 + 402 + 403 + 404 + 405) / 5) < 1e-6
    schools = {e["school"] for e in short}
    assert "長洲中" in schools  # 濱北愛のみ
    assert "玉陵中" in schools  # 居石のみ
    assert "岱明中" in schools
    assert "除外男子" not in {
        m["name"] for e in ranked for m in e.get("members") or []
    }
    assert "有尾明莉" not in {
        m["name"] for e in ranked for m in e.get("members") or []
    }
    assert "外部" not in {m["name"] for e in ranked for m in e.get("members") or []}
    nagasu = next(e for e in short if e["school"] == "長洲中")
    assert nagasu["members"][0]["name"] == "濱北愛"


def test_build_arato_school_men_avg6_show_all() -> None:
    cfg = {
        "affiliation_keywords": list(gap.ARATO_TAMANA_KEYWORDS),
        "school_analysis_affiliation_overrides": {},
        "school_analysis_athlete_affiliation_overrides": {},
        "exclude_name_keywords": [],
        "exclude_when_affiliation_contains": "金栗",
    }
    legs = []
    for i in range(1, 9):
        legs.append(
            {
                "team": "岱明A",
                "leg": ((i - 1) % 4) + 1,
                "name": f"岱明{i}",
                "actual": 600.0 + i,
                "pred": 600.0,
                "delta": float(i),
                "class": "ok",
                "gender": "男子",
            }
        )
    ranked = gap.build_arato_school_topn_ranking(legs, gender="男子", config=cfg)
    assert gap.school_avg_n("男子") == 6
    assert len(ranked) == 1
    e = ranked[0]
    assert e["complete"] is True
    assert e["top_n"] == 6
    assert len(e["members"]) == 8  # 内訳は全員
    assert [m["name"] for m in e["members"]] == [f"岱明{i}" for i in range(1, 9)]
    assert e["members"][5]["in_average"] is True
    assert e["members"][6]["in_average"] is False
    assert abs(e["average"] - (601 + 602 + 603 + 604 + 605 + 606) / 6) < 1e-6


def test_render_html_includes_arato_section() -> None:
    payload = {
        "years": [
            {
                "year": 2026,
                "event_date": "2026-09-20",
                "as_of": "2026-09-18",
                "genders": [
                    {
                        "gender": "女子",
                        "teams": [
                            {
                                "team": "岱明A",
                                "actual_rank": 6,
                                "rank_ref": 4,
                                "actual_total": 1818.0,
                                "total_ref": 1778.0,
                                "total_delta": 40.0,
                                "class": "slight_miss",
                                "imputed": False,
                            }
                        ],
                        "legs": [
                            {
                                "team": "岱明A",
                                "leg": 2,
                                "name": "村上咲稀",
                                "actual": 427.0,
                                "pred": 406.0,
                                "delta": 21.0,
                                "class": "miss",
                                "note": "",
                                "gender": "女子",
                            },
                            {
                                "team": "NJAC",
                                "leg": 1,
                                "name": "濱北愛",
                                "actual": 400.0,
                                "pred": 410.0,
                                "delta": -10.0,
                                "class": "slight_beat",
                                "note": "",
                                "gender": "女子",
                            },
                            {
                                "team": "NJAC",
                                "leg": 2,
                                "name": "他のNJAC",
                                "actual": 390.0,
                                "pred": 390.0,
                                "delta": 0.0,
                                "class": "ok",
                                "note": "",
                                "gender": "女子",
                            },
                        ],
                    }
                ],
            }
        ]
    }
    html = gap.render_html(payload)
    assert "荒玉学校対抗：上位5人平均" in html
    assert "荒尾玉名関連：出走チーム成績" in html
    assert "村上咲稀" in html
    assert "濱北愛" in html
    assert "長洲中" in html
    school_sec = html.split("荒玉学校対抗：上位5人平均", 1)[1].split(
        "荒尾玉名関連：出走チーム成績", 1
    )[0]
    assert "濱北愛" in school_sec
    assert "他のNJAC" not in school_sec
    assert "岱明中" in school_sec


def test_format_count_pct() -> None:
    assert gap.format_count_pct(1, 4) == "1（25%）"
    assert gap.format_count_pct(2, 3) == "2（67%）"
    assert gap.format_count_pct(0, 0) == "0（0%）"


def test_donut_legend_includes_percent() -> None:
    html = gap._donut_counts(
        {"beat": 1, "ok": 2, "miss": 1, "slight_beat": 0, "slight_miss": 0, "unknown": 0},
        "donut-test",
    )
    assert "大きく上回った 1（25%）" in html
    assert "妥当 2（50%）" in html
    assert "大きく下回った 1（25%）" in html
    assert "<title>" in html
