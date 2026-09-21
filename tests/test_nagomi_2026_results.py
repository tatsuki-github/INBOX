#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for 2026 なごみ成績表 structured data."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import nagomi_2026_results_data as results
from generate_nagomi_2026_results import validate_teams


def test_event_meta() -> None:
    assert results.EVENT["date"] == "2026-09-20"
    assert "第12回" in results.EVENT["title"]


def test_women_winner_and_daimei() -> None:
    w1 = results.WOMEN[0]
    assert w1["rank"] == 1
    assert w1["team"] == "金栗PROJECT A"
    assert w1["total"] == "26:55"
    assert w1["legs"][0]["name"] == "居石華音"
    assert w1["legs"][3]["name"] == "秀島恋莉"
    daimei = next(t for t in results.WOMEN if t["team"] == "岱明A")
    assert daimei["rank"] == 6
    assert daimei["total"] == "30:18"
    assert [leg["name"] for leg in daimei["legs"]] == [
        "山﨑莉奈",
        "村上咲稀",
        "増岡里俐",
        "角田亜美",
    ]


def test_women_nankan_beta_not_tamana() -> None:
    t = next(t for t in results.WOMEN if t["no"] == 17)
    assert t["team"] == "南関β"
    assert t["legs"][0]["name"] == "井口舞桜"


def test_men_winner_and_daimei() -> None:
    m1 = results.MEN[0]
    assert m1["rank"] == 1 and m1["team"] == "NJAC" and m1["total"] == "38:33"
    kanaguri = next(t for t in results.MEN if t["team"] == "金栗PROJECT A")
    assert kanaguri["rank"] == 2 and kanaguri["total"] == "38:49"
    daimei = next(t for t in results.MEN if t["team"] == "岱明A")
    assert daimei["rank"] == 18 and daimei["total"] == "42:39"
    assert daimei["legs"][0]["name"] == "山本哲瑠"
    daimei_b = next(t for t in results.MEN if t["team"] == "岱明B")
    assert daimei_b["rank"] == 31 and daimei_b["total"] == "48:10"


def test_cumulative_math() -> None:
    assert validate_teams(results.WOMEN, "女子") == []
    assert validate_teams(results.MEN, "男子") == []


def test_counts() -> None:
    assert sum(1 for t in results.WOMEN if t.get("rank")) == 23
    assert sum(1 for t in results.WOMEN if t.get("rank") is None) == 2
    assert sum(1 for t in results.MEN if t.get("rank")) == 34
    assert sum(1 for t in results.MEN if t.get("rank") is None) == 5
