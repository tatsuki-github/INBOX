#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""荒玉中体連駅伝 2026: 区間オーダー×SB予想（なごみ換算＋距離比例＋5ヶ月鮮度）。

公式オーダー未着のため、ジュニア実績・トラックSB上位で全区間を仮置きして
なごみ／ジュニア同型の総合順位・通過順テーブルを出す。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
import generate_nagomi_order_sb_preview as nagomi  # noqa: E402

MEET_DIR = ROOT / "input/external/drive/shared/大会/2026年度/1014-1015_荒玉中体連駅伝"
CORPUS_MEET = ROOT / "input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝"
EVENT_DATE = "2026-10-14"
DEFAULT_AS_OF = "2026-09-27"
SB_FRESHNESS_DAYS = 152
MEN_3000M_FALLBACK_THRESHOLD_SEC = 30.0
HUMAN_NOTES_FILENAME = {
    "女子": "人間考慮_女子.yaml",
    "男子": "人間考慮_男子.yaml",
}

# 2024年以降の区間距離（docs/aragyoku-ekiden-distance-definitions.md）
WOMEN_DISTANCES_KM = [3.00, 1.855, 2.00, 2.00, 3.00]
MEN_DISTANCES_KM = [3.00, 2.855, 3.00, 3.00, 2.855, 3.00]

# 区間バイアス秒（実績−予想の中央値）。calibrate_aragyoku_sb_preview.py で更新。
LEG_BIAS_SEC: dict[str, list[float]] = {
    "女子": [20.8, 1.9, -11.2, 7.8, 37.1],
    "男子": [-5.8, 14.4, 9.9, 35.5, 17.7, 15.2],
}

# 監督確定オーダー（女子フル／男子1–4）。男子5–6は仮置きで埋める。
TAIMEI_KNOWN_LEGS: dict[str, dict[int, str]] = {
    "女子": {1: "村上 咲稀", 2: "山﨑 莉奈", 3: "角田 亜美", 4: "増岡 里俐", 5: "高田 麻由"},
    "男子": {1: "松野 凛空", 2: "山本 哲瑠", 3: "今村 昇磨", 4: "田上 颯人"},
}

# 仮区間オーダーのシード（公式未着）。※ は仮置き。氏名は表示用（スペース可）。
# クラブ所属は arato_tamana_report.yaml の学校／選手マッピングで各校へ再分配する
# （get_provisional_orders）。シードの LOCKED 校はジュニア／確定を優先して維持。
# 予想タイムは実SBがある区間のみ。中央値補完はしない。
PROVISIONAL_ORDERS: dict[str, list[dict[str, Any]]] = {
    "女子": [
        {
            "no": 1,
            "team": "南関中",
            "source": "junior+open",
            "legs": ["福山 結衣", "米田 美空", "平山 結菜", "原賀 美和", "堀田 稔々"],
            "notes": "1区・5区にエース（福山／堀田）。4区はなごみβ 7:53の原賀（稗島9:07より現実的）",
        },
        {
            "no": 2,
            "team": "岱明中",
            "source": "confirmed",
            "legs": ["村上 咲稀", "山﨑 莉奈", "角田 亜美", "増岡 里俐", "高田 麻由"],
            "notes": "監督確定（1村上・5高田＝エース配置済み）",
        },
        {
            "no": 3,
            "team": "玉名高附",
            "source": "affiliation_sb+junior_open",
            "legs": ["大木 莉子", "田口 心晴", "永江 春花", "中山 結葵", "戸谷 美月"],
            "notes": "所属=玉名附中の実SBのみ。1大木・5戸谷にエース。中山はJrオープン・SB窓外の可能性",
        },
        {
            "no": 4,
            "team": "天水中",
            "source": "sb_rank",
            "legs": ["田尻 雛菜乃", "山本 桜愛", "竹原 晴美", "木根 咲姫", "花谷 明優"],
            "notes": "1田尻・5花谷にエース（校内SB上位）",
        },
        {
            "no": 5,
            "team": "荒尾海陽中",
            "source": "sb_rank",
            "legs": ["三原 悠愛", "石川 葵葉", "今村 心晴", "湯村 絢音", "前田 凛子"],
            "notes": "1三原・5前田にエース（校内SB上位）",
        },
        {
            "no": 6,
            "team": "荒尾三中",
            "source": "prior_a_b_team",
            "legs": ["庄山 瑠那", "平 夢花", "内野 沙笑", "佐藤 妃葵", "福島 志帆"],
            "notes": (
                "1区庄山（1500m 4:39・なごみ金栗A 6:28）。"
                "5区福島（前年A 1区→アンカー）。2平・3内野（前年5区）入れ替え、4佐藤は残置"
            ),
        },
        {
            "no": 7,
            "team": "長洲中",
            "source": "locked_ace_leg1",
            "legs": ["猿渡 愛梨", "村里 唯花", "濱北 愛", "山川 綾", "中村 羽音"],
            "notes": (
                "1区猿渡（直近3000m・なごみ6:55）。"
                "2村里・3濱北・4山川・5中村（アンカー）"
            ),
        },
        {
            "no": 10,
            "team": "玉名中",
            "source": "prior_a_b_team",
            "legs": ["清藤 結唯", "亀木", "川原 芽吹", "結菜", "水本 星夏"],
            "notes": (
                "1清藤（直近トラック厚い）・5水本。"
                "川原は今年フォーム落ちで1/5区外→3区（入れるか入れないかのライン）。"
                "2亀木・4結菜は前年B。姓名一部未確認"
            ),
        },
    ],
    "男子": [
        {
            "no": 1,
            "team": "玉名高附",
            "source": "junior+sb",
            "legs": [
                "小倉 十和",
                "草野 瑠唯",
                "秋原 康秀",
                "小倉 由宇",
                "中岡 謙太",
                "福島 圭希",
            ],
            "notes": "ジュニアA＋B補完。配置は遅→5・次遅→2。3区は紙面「萩原」→SB「秋原」",
        },
        {
            "no": 2,
            "team": "菊水中",
            "source": "金栗PROJECT_sb",
            "legs": [
                "隈部 侑成",
                "松浦 眞大",
                "津口 晃誠",
                "松山 哲丈",
                "川崎 大芽",
                "福原 雅史",
            ],
            "notes": "金栗PROJECT所属のトラックSB上位（配置は遅→5・次遅→2）",
        },
        {
            "no": 3,
            "team": "玉陵中",
            "source": "玉名アスリーツ_sb",
            "legs": [
                "柿本 晴仁",
                "永田 來夢",
                "辛嶋 大宙",
                "松島 颯希",
                "内野 翼",
                "宮川 晴",
            ],
            "notes": "玉名アスリーツ所属のトラックSB上位（配置は遅→5・次遅→2）",
        },
        {
            "no": 4,
            "team": "南関中",
            "source": "junior+sb",
            "legs": [
                "永清 芯",
                "大木 蒼介",
                "本多 蒼",
                "猿渡 元喜",
                "田中 翔大",
                "村上 葉侑",
            ],
            "notes": "ジュニアA＋SB。配置は遅→5・次遅→2",
        },
        {
            "no": 5,
            "team": "岱明中",
            "source": "confirmed+provisional",
            "legs": [
                "松野 凛空",
                "山本 哲瑠",
                "今村 昇磨",
                "田上 颯人",
                "中尾 快叶",
                "松本 空羽",
            ],
            "notes": "1–4監督確定。5中尾・6松本はジュニア／SBによる仮置き（遅→5配置の対象外）",
        },
        {
            "no": 6,
            "team": "玉名中",
            "source": "sb_rank",
            "legs": [
                "田島 航",
                "萩原 大介",
                "中村 龍之介",
                "林田 竜空",
                "大原 彩透",
                "安田 朔",
            ],
            "notes": "校内SBスコア上位（配置は遅→5・次遅→2）",
        },
        {
            "no": 7,
            "team": "天水中",
            "source": "sb_rank",
            "legs": [
                "中村 七皇",
                "木村 幹太",
                "坂口 昂輝",
                "眞田 和季",
                "中村 泰夢",
                "宮田 明仁",
            ],
            "notes": "校内SBスコア上位（配置は遅→5・次遅→2）",
        },
        {
            "no": 8,
            "team": "荒尾海陽中",
            "source": "junior+sb",
            "legs": [
                "松本 颯斗",
                "吉田 理人",
                "荒木 陽翔",
                "林田 光司",
                "松井 智義",
                "宮原 維吹",
            ],
            "notes": "ジュニア下位帯＋SB上位（遅→5・次遅→2。紙面「宮原照吹」→SB「維吹」）",
        },
        {
            "no": 9,
            "team": "荒尾第四中",
            "source": "prior_year+nagomi",
            "legs": [
                "藤原 尚己",
                "谷平 陽生",
                "中田 透和",
                "北村 春磨",
                "本戸 優貴",
                "藤井 祐吏",
            ],
            "notes": (
                "前年A復帰（藤原・谷平・中田・本戸）＋SBの北村春磨。"
                "シードは速い順。配置時に遅→5（藤井）・次遅→2。松岡・浦本は控え"
            ),
        },
        {
            "no": 10,
            "team": "荒尾三中",
            "source": "sb_rank",
            "legs": [
                "田中 羚弥",
                "井形 朝陽",
                "",
                "",
                "",
                "",
            ],
            "notes": "層薄。配置時に最速1区・最遅5区。不足は欠測",
        },
    ],
}

ARATO_REPORT_PATH = ROOT / "input/arato_tamana_report.yaml"
CLUB_AFFILIATION_HINTS = (
    "ATRC",
    "金栗PROJECT",
    "玉名アスリーツ",
    "玉東クラブ",
    "NJAC",
)
# ジュニア／監督確定を優先して維持する校（学校プールで上書きしない）
LOCKED_ORDER_TEAMS: dict[str, set[str]] = {
    "女子": {"岱明中", "南関中", "玉名高附", "玉名中", "荒尾三中", "長洲中"},
    "男子": {"岱明中", "玉名高附", "南関中", "荒尾海陽中", "荒尾第四中"},
}
# 出力順（分配後に追加される校を含む）
TEAM_DISPLAY_ORDER: dict[str, list[str]] = {
    "女子": [
        "南関中",
        "岱明中",
        "玉名高附",
        "菊水中",
        "玉陵中",
        "天水中",
        "荒尾海陽中",
        "荒尾三中",
        "荒尾第四中",
        "長洲中",
        "玉名中",
    ],
    "男子": [
        "玉名高附",
        "菊水中",
        "玉陵中",
        "南関中",
        "岱明中",
        "長洲中",
        "玉名中",
        "天水中",
        "荒尾海陽中",
        "荒尾第四中",
        "荒尾三中",
    ],
}
# 学校マッピング由来の仮オーダーに必要な最低ユニーク人数（1人の繰り返し全区間埋めを防ぐ）
MIN_UNIQUE_FOR_SCHOOL_MAP: dict[str, int] = {"女子": 2, "男子": 2}


def load_arato_school_map(path: Path | None = None) -> dict[str, Any]:
    """荒尾玉名レポート設定から学校集約マッピングを読む。"""
    p = path or ARATO_REPORT_PATH
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {
        "affiliation_overrides": dict(raw.get("school_analysis_affiliation_overrides") or {}),
        "athlete_overrides": dict(raw.get("school_analysis_athlete_affiliation_overrides") or {}),
        "exclude_name_keywords": list(raw.get("exclude_name_keywords") or []),
        "exclude_when_affiliation_contains": str(
            raw.get("exclude_when_affiliation_contains") or ""
        ),
    }


def resolve_analysis_school(
    affiliation: str,
    name: str,
    *,
    affiliation_overrides: dict[str, str] | None = None,
    athlete_overrides: dict[str, dict] | None = None,
) -> str:
    """クラブ／所属を駅伝校名へ解決する（arato_tamana_ranking と同規則）。"""
    overrides = affiliation_overrides or {}
    athlete_map = athlete_overrides or {}
    aff = affiliation or ""
    spec: dict[str, Any] | None = None
    for club_key, club_spec in athlete_map.items():
        if club_key in aff or aff == club_key:
            spec = club_spec if isinstance(club_spec, dict) else None
            break
    if spec:
        for ath_name, school in (spec.get("athletes") or {}).items():
            if nagomi.norm_name(str(ath_name)) == nagomi.norm_name(name):
                return str(school)
        if spec.get("default"):
            return str(spec["default"])
    for club, school in overrides.items():
        if club in aff or aff == club:
            return str(school)
    return aff


def pick_preferred_affiliation(affiliations: set[str]) -> str:
    """複数所属があるときクラブ表記を優先する。"""
    if not affiliations:
        return ""
    for hint in CLUB_AFFILIATION_HINTS:
        for aff in affiliations:
            if hint in aff or aff == hint:
                return aff
    return sorted(affiliations)[0]


def load_name_affiliations() -> dict[str, str]:
    """正規化氏名 → 優先所属。"""
    by_name: dict[str, set[str]] = defaultdict(set)
    if nagomi.SB_ADOPTED.exists():
        for r in json.loads(nagomi.SB_ADOPTED.read_text(encoding="utf-8")):
            name = str(r.get("名前") or "")
            aff = str(r.get("所属") or "").strip()
            key = nagomi.norm_name(name)
            if key and aff:
                by_name[key].add(aff)
    if nagomi.NOTION_ROWS.exists():
        for r in json.loads(nagomi.NOTION_ROWS.read_text(encoding="utf-8")):
            name = str(r.get("name") or r.get("名前") or "")
            aff = str(r.get("affiliation") or r.get("所属") or "").strip()
            key = nagomi.norm_name(name)
            if key and aff:
                by_name[key].add(aff)
    return {k: pick_preferred_affiliation(v) for k, v in by_name.items()}


def _should_exclude_athlete(name: str, affiliation: str, school_map: dict[str, Any]) -> bool:
    needle = school_map.get("exclude_when_affiliation_contains") or ""
    if not needle or needle not in affiliation:
        return False
    compact = name.replace(" ", "")
    return any(kw in compact for kw in school_map.get("exclude_name_keywords") or [])


def athlete_ekiden_score(gender: str, ath: Any) -> float | None:
    """校内順位付け用の換算秒（小さいほど速い）。"""
    if gender == "男子":
        sec, _ = nagomi.predict_men_3k(ath.marks)
    else:
        sec, _ = nagomi.predict_women_2k(ath.marks)
    return sec


def build_school_athlete_pools(
    gender: str,
    sb_index: dict,
    *,
    school_map: dict[str, Any] | None = None,
    name_affiliations: dict[str, str] | None = None,
) -> dict[str, list[tuple[str, float]]]:
    """学校 → [(表示名, スコア秒)] を速い順で返す。"""
    smap = school_map or load_arato_school_map()
    aff_by_name = name_affiliations if name_affiliations is not None else load_name_affiliations()
    max_projected = load_graduated_school_names(gender)
    pools: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for key, ath in sb_index.items():
        aff = aff_by_name.get(key) or ""
        if not aff:
            continue
        if _should_exclude_athlete(ath.name, aff, smap):
            continue
        school = resolve_analysis_school(
            aff,
            ath.name,
            affiliation_overrides=smap["affiliation_overrides"],
            athlete_overrides=smap["athlete_overrides"],
        )
        if not school or school in CLUB_AFFILIATION_HINTS:
            # 未マッピングのクラブ所属は校プールに入れない
            continue
        if is_excluded_graduate(
            ath.name, school=school, graduated_keys=max_projected
        ):
            continue
        if any(h in school for h in CLUB_AFFILIATION_HINTS):
            continue
        score = athlete_ekiden_score(gender, ath)
        if score is None:
            continue
        pools[school].append((ath.name, score))
    for school, rows in pools.items():
        rows.sort(key=lambda x: (x[1], nagomi.norm_name(x[0])))
        # 同名・近似同名（漢字1文字差等）は最速のみ
        uniq: list[tuple[str, float]] = []
        for name, score in rows:
            if any(is_same_athlete(name, existing) for existing, _ in uniq):
                continue
            uniq.append((name, score))
        pools[school] = uniq
    return merge_prior_year_into_pools(dict(pools), gender)


# 表記ゆれ（異体字）を潰したうえで、1文字差の同長氏名は同一選手とみなす
_NAME_VARIANT_TRANS = str.maketrans(
    {
        "惠": "恵",
        "來": "来",
        "髙": "高",
        "﨑": "崎",
        "邉": "辺",
        "濱": "浜",
        "濵": "浜",
    }
)


def canonicalize_athlete_name(name: str) -> str:
    return nagomi.norm_name(str(name)).translate(_NAME_VARIANT_TRANS)


def is_same_athlete(a: str, b: str) -> bool:
    """同一選手か（完全一致・異体字・同長1文字差のOCR揺れ）。"""
    ca = canonicalize_athlete_name(a)
    cb = canonicalize_athlete_name(b)
    if not ca or not cb:
        return False
    if ca == cb:
        return True
    if len(ca) == len(cb) and len(ca) >= 3:
        return sum(x != y for x, y in zip(ca, cb)) <= 1
    return False


def dedupe_ranked_athletes(ranked: list[str]) -> list[str]:
    """順位付きリストから同一／近似同名を除いたユニーク列。"""
    uniq: list[str] = []
    for name in ranked:
        raw = str(name).strip()
        if not raw:
            continue
        if any(is_same_athlete(raw, existing) for existing in uniq):
            continue
        uniq.append(raw)
    return uniq


def legs_from_ranked_athletes(
    ranked: list[str],
    n_legs: int,
    *,
    women_aces: bool,
) -> list[str]:
    """速い順リストから区間配置。同一選手の複数区間は禁止（不足は空＝欠測）。

    候補が区間数より多い場合は**最速の n_legs 名だけ**を出走枠にする
    （全プールの最遅を2/5区に誤配置しない）。
    女子は1区・アンカーに上位2名（足りなければ空）。
    男子は最速を1区、最遅を5区、次点遅を2区、残りを若い区間番号から埋める
    （岱明などロック校は呼び出し側で除外する）。
    異体字・OCR1文字差（例: 河野壮大／壮太、森絢恵／惠）も同一扱い。
    """
    uniq = dedupe_ranked_athletes(ranked)
    if not uniq:
        return [""] * n_legs
    # 出走枠は最速 n_legs 名のみ（プール全体の最遅を載せない）
    starters = uniq[:n_legs]
    if women_aces and n_legs >= 2:
        best = starters[0]
        second = starters[1] if len(starters) >= 2 else ""
        mid = starters[2:] if len(starters) > 2 else []
        out: list[str] = [best]
        for i in range(n_legs - 2):
            out.append(mid[i] if i < len(mid) else "")
        out.append(second)
        return out
    # 男子（および women_aces=False）: 遅→5・次遅→2・最速→1
    out = [""] * n_legs
    pool = list(starters)
    out[0] = pool.pop(0)
    if n_legs >= 5 and pool:
        out[4] = pool.pop()  # 出走枠内の最遅 → 5区
    if n_legs >= 2 and pool:
        out[1] = pool.pop()  # 次点遅 → 2区
    for i in range(n_legs):
        if out[i] == "" and pool:
            out[i] = pool.pop(0)
    return out


def _apply_men_slow_leg_placement(row: dict[str, Any], n_legs: int) -> dict[str, Any]:
    """男子仮オーダーを遅→5・次遅→2に並べ替える（岱明は対象外）。"""
    team = str(row.get("team") or "")
    if "岱明" in team:
        return row
    filled = [str(n).strip() for n in (row.get("legs") or []) if str(n).strip()]
    out = dict(row)
    out["legs"] = legs_from_ranked_athletes(filled, n_legs, women_aces=False)
    return out


def sanitize_order_legs(legs: list[str], n_legs: int, *, women_aces: bool = False) -> list[str]:
    """区間順を保ったまま、同一／近似同名の再出だけを空欄にする。

    ※ women_aces は後方互換用（無視）。並べ替えはしない。
    """
    del women_aces  # unused; positional sanitize only
    out: list[str] = []
    kept: list[str] = []
    for i in range(n_legs):
        name = str(legs[i]).strip() if i < len(legs) else ""
        if not name:
            out.append("")
            continue
        if any(is_same_athlete(name, existing) for existing in kept):
            out.append("")
            continue
        kept.append(name)
        out.append(name)
    return out


def _seed_by_team(gender: str) -> dict[str, dict[str, Any]]:
    return {row["team"]: dict(row) for row in PROVISIONAL_ORDERS[gender]}


def get_provisional_orders(
    gender: str,
    sb_index: dict | None = None,
    *,
    school_map: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """シード＋学校マッピング分配で仮オーダーを組み立てる。

    sb_index が無いときはシードのみ（後方互換）。いずれの経路でも同一／近似同名の
    複数区間配置は除去する（区間順は維持し、再出は空欄）。
    """
    inject_prior_year_race_marks(gender)
    seeds = _seed_by_team(gender)
    n_legs = len(WOMEN_DISTANCES_KM if gender == "女子" else MEN_DISTANCES_KM)
    women_aces = gender == "女子"

    def _sanitize_row(row: dict[str, Any]) -> dict[str, Any]:
        out = dict(row)
        out["legs"] = sanitize_order_legs(list(out.get("legs") or []), n_legs)
        return out

    if not sb_index:
        rows = []
        for row in PROVISIONAL_ORDERS[gender]:
            r = _sanitize_row(row)
            if gender == "男子":
                r = _apply_men_slow_leg_placement(r, n_legs)
            rows.append(r)
        return rows

    smap = school_map or load_arato_school_map()
    pools = build_school_athlete_pools(gender, sb_index, school_map=smap)
    locked = LOCKED_ORDER_TEAMS.get(gender, set())

    used_names: list[str] = []

    def _is_used(name: str) -> bool:
        return any(is_same_athlete(name, u) for u in used_names)

    def _mark_used(name: str) -> None:
        if name and not _is_used(name):
            used_names.append(str(name))

    built: dict[str, dict[str, Any]] = {}
    for team in locked:
        seed = seeds.get(team)
        if not seed:
            continue
        row = _sanitize_row(seed)
        if gender == "男子":
            row = _apply_men_slow_leg_placement(row, n_legs)
        built[team] = row
        for name in row.get("legs") or []:
            _mark_used(str(name))

    for team in TEAM_DISPLAY_ORDER.get(gender, []):
        if team in built:
            continue
        pool = [
            (name, score)
            for name, score in pools.get(team, [])
            if not _is_used(name)
        ]
        seed = seeds.get(team)
        min_unique = MIN_UNIQUE_FOR_SCHOOL_MAP.get(gender, 2)
        if pool and len(pool) >= min_unique:
            ranked_names = [n for n, _ in pool]
            legs = legs_from_ranked_athletes(
                ranked_names, n_legs, women_aces=women_aces
            )
            notes = (
                f"`arato_tamana_report.yaml` の所属／選手マッピング後の校内SB上位"
                f"（{len(ranked_names)}名プール）"
            )
            built[team] = {
                "team": team,
                "source": "school_mapped_sb",
                "legs": legs,
                "notes": notes,
            }
            for name in legs:
                _mark_used(name)
        elif seed:
            ranked: list[str] = []
            for name in seed.get("legs") or []:
                if name and not _is_used(str(name)) and not any(
                    is_same_athlete(str(name), r) for r in ranked
                ):
                    ranked.append(str(name))
            for name, _ in pool:
                if not _is_used(name) and not any(
                    is_same_athlete(name, r) for r in ranked
                ):
                    ranked.append(name)
            legs = legs_from_ranked_athletes(
                ranked, n_legs, women_aces=women_aces
            )
            row = dict(seed)
            row["legs"] = legs
            row["notes"] = (
                f"{seed.get('notes', '')} / 同一選手複数区間禁止"
            ).strip(" /")
            built[team] = row
            for name in legs:
                _mark_used(name)

    for team, seed in seeds.items():
        if team in built:
            continue
        row = _sanitize_row(seed)
        if gender == "男子":
            row = _apply_men_slow_leg_placement(row, n_legs)
        built[team] = row

    for team, row in list(built.items()):
        built[team] = _sanitize_row(row)

    ordered: list[dict[str, Any]] = []
    seen_teams: set[str] = set()
    for team in TEAM_DISPLAY_ORDER.get(gender, []):
        if team not in built:
            continue
        row = dict(built[team])
        row["no"] = len(ordered) + 1
        ordered.append(row)
        seen_teams.add(team)
    for team, row in built.items():
        if team in seen_teams:
            continue
        out = dict(row)
        out["no"] = len(ordered) + 1
        ordered.append(out)
    return ordered


# 直近駅伝実績（距離比例後、イベント日からの減衰でトラックSBとブレンド）
# km / sec は当該大会の区間距離と区間タイム。キーは norm_name 済み。
# なごみ女子は各区2.0km、ジュニア女子は1区2.7km・2–4区2.3km（オープンは2.3km扱い）。
_RECENT_EKIDEN_MARKS_RAW: dict[str, list[dict[str, Any]]] = {
    # ---- 男子 ----
    "今村 昇磨": [
        {"date": "2026-09-26", "km": 2.6, "sec": 8 * 60 + 27, "meet": "ジュニアCS"},
        {"date": "2026-09-20", "km": 3.0, "sec": 10 * 60 + 7, "meet": "なごみ"},
    ],
    "田上 颯人": [
        {"date": "2026-09-26", "km": 2.6, "sec": 8 * 60 + 26, "meet": "ジュニアCS"},
        {"date": "2026-09-20", "km": 3.0, "sec": 9 * 60 + 54, "meet": "なごみ"},
    ],
    "松野 凛空": [
        {"date": "2026-09-26", "km": 3.0, "sec": 9 * 60 + 41, "meet": "ジュニアCS"},
    ],
    "山本 哲瑠": [
        {"date": "2026-09-26", "km": 2.6, "sec": 8 * 60 + 34, "meet": "ジュニアCS"},
        {"date": "2026-09-20", "km": 3.0, "sec": 10 * 60 + 11, "meet": "なごみ"},
    ],
    "中尾 快叶": [
        {"date": "2026-09-26", "km": 2.6, "sec": 9 * 60 + 15, "meet": "ジュニアCS"},
        {"date": "2026-09-20", "km": 3.0, "sec": 11 * 60 + 3, "meet": "なごみ"},
    ],
    "松本 空羽": [
        {"date": "2026-09-20", "km": 3.0, "sec": 11 * 60 + 31, "meet": "なごみ"},
    ],
    "隈部 侑成": [
        {"date": "2026-09-20", "km": 3.0, "sec": 9 * 60 + 17, "meet": "なごみ"},
    ],
    "松浦 眞大": [
        {"date": "2026-09-20", "km": 3.0, "sec": 9 * 60 + 26, "meet": "なごみ"},
    ],
    "津口 晃誠": [
        {"date": "2026-09-20", "km": 3.0, "sec": 9 * 60 + 44, "meet": "なごみ"},
    ],
    # なごみ2区10:30は不調レース。Jr CS 4区8:48を実力線とする（なごみは注入しない）
    "小倉 由宇": [
        {"date": "2026-09-26", "km": 2.6, "sec": 8 * 60 + 48, "meet": "ジュニアCS"},
    ],
    # 荒尾第四・なごみOP（トラックSBなしでも区間予想の根拠）
    "藤井 祐吏": [
        {"date": "2026-09-20", "km": 3.0, "sec": 10 * 60 + 15, "meet": "なごみ"},
    ],
    "松岡 颯希": [
        {"date": "2026-09-20", "km": 3.0, "sec": 12 * 60 + 7, "meet": "なごみ"},
    ],
    "浦本 崇彦": [
        {"date": "2026-09-20", "km": 3.0, "sec": 15 * 60 + 3, "meet": "なごみ"},
    ],
    # ---- 女子（荒玉はトラック楽観が強いため直近駅伝を主にする）----
    "村上 咲稀": [
        {"date": "2026-09-26", "km": 2.7, "sec": 9 * 60 + 58, "meet": "ジュニアCS"},
        {"date": "2026-09-20", "km": 2.0, "sec": 7 * 60 + 7, "meet": "なごみ"},
    ],
    "高田 麻由": [
        {"date": "2026-09-26", "km": 2.3, "sec": 8 * 60 + 49, "meet": "ジュニアCS"},
    ],
    "増岡 里俐": [
        {"date": "2026-09-26", "km": 2.3, "sec": 9 * 60 + 0, "meet": "ジュニアCS"},
        {"date": "2026-09-20", "km": 2.0, "sec": 7 * 60 + 45, "meet": "なごみ"},
    ],
    "山﨑 莉奈": [
        {"date": "2026-09-26", "km": 2.3, "sec": 9 * 60 + 5, "meet": "ジュニアCS"},
        {"date": "2026-09-20", "km": 2.0, "sec": 7 * 60 + 38, "meet": "なごみ"},
    ],
    "角田 亜美": [
        {"date": "2026-09-26", "km": 2.3, "sec": 9 * 60 + 2, "meet": "ジュニアOP"},
        {"date": "2026-09-20", "km": 2.0, "sec": 7 * 60 + 48, "meet": "なごみ"},
    ],
    "塚原 優衣": [
        {"date": "2026-09-26", "km": 2.3, "sec": 9 * 60 + 13, "meet": "ジュニアOP"},
        {"date": "2026-09-20", "km": 2.0, "sec": 8 * 60 + 12, "meet": "なごみ"},
    ],
    "柴尾 希乃": [
        {"date": "2026-09-26", "km": 2.3, "sec": 9 * 60 + 41, "meet": "ジュニアOP"},
        {"date": "2026-09-20", "km": 2.0, "sec": 8 * 60 + 43, "meet": "なごみ"},
    ],
    "福山 結衣": [
        {"date": "2026-09-26", "km": 2.3, "sec": 8 * 60 + 51, "meet": "ジュニアCS"},
        {"date": "2026-09-20", "km": 2.0, "sec": 7 * 60 + 0, "meet": "なごみ"},
    ],
    "米田 美空": [
        {"date": "2026-09-26", "km": 2.3, "sec": 8 * 60 + 22, "meet": "ジュニアCS"},
        {"date": "2026-09-20", "km": 2.0, "sec": 8 * 60 + 1, "meet": "なごみ"},
    ],
    "堀田 稔々": [
        {"date": "2026-09-26", "km": 2.7, "sec": 9 * 60 + 27, "meet": "ジュニアCS"},
        {"date": "2026-09-20", "km": 2.0, "sec": 7 * 60 + 17, "meet": "なごみ"},
    ],
    "平山 結菜": [
        {"date": "2026-09-26", "km": 2.3, "sec": 8 * 60 + 47, "meet": "ジュニアCS"},
        {"date": "2026-09-20", "km": 2.0, "sec": 7 * 60 + 42, "meet": "なごみ"},
    ],
    "原賀 美和": [
        # なごみ南関β 2区。SBなしでも荒玉短中継の控え本命（南関α控え・Jrスタートリスト）
        {"date": "2026-09-20", "km": 2.0, "sec": 7 * 60 + 53, "meet": "なごみ"},
    ],
    "猿渡 愛梨": [
        # ATRCなごみ2区6:55。直近3000mもあり長洲1区本命
        {"date": "2026-09-20", "km": 2.0, "sec": 6 * 60 + 55, "meet": "なごみ"},
    ],
    "庄山 瑠那": [
        # 金栗PROJECT A なごみ2区6:28（区間1位）。荒尾三1区本命
        {"date": "2026-09-20", "km": 2.0, "sec": 6 * 60 + 28, "meet": "なごみ"},
    ],
    "井口 舞桜": [
        {"date": "2026-09-26", "km": 2.3, "sec": 8 * 60 + 58, "meet": "ジュニアOP"},
        {"date": "2026-09-20", "km": 2.0, "sec": 8 * 60 + 3, "meet": "なごみ"},
    ],
    "稗島 琴都": [
        {"date": "2026-09-26", "km": 2.3, "sec": 10 * 60 + 8, "meet": "ジュニアOP"},
        {"date": "2026-09-20", "km": 2.0, "sec": 9 * 60 + 7, "meet": "なごみ"},
    ],
}
RECENT_EKIDEN_MARKS = {
    nagomi.norm_name(k): v for k, v in _RECENT_EKIDEN_MARKS_RAW.items()
}

# 荒玉当日を基準に、半減期21日で直近実績の重みを減衰（新しいほど大きい）
FORM_HALF_LIFE_DAYS = 21.0
# 女子はトラックSBが楽観寄りのため、直近駅伝があるとき SB 重みを大幅に抑える
WOMEN_SB_WEIGHT_SCALE = 0.15
# 男子も直近駅伝があるときは SB を抑え、ロード実績を主にする（2–4区の楽観不足対策）
MEN_SB_WEIGHT_SCALE = 0.20
# 前年荒玉（同学年コース）は半減期では消えすぎるため固定重みで残す
PRIOR_YEAR_COURSE_WEIGHT = 0.55
# 一昨年はプール補充が主目的。ブレンドでは弱めに効かせる
PRIOR_YEAR_MINUS_2_WEIGHT = 0.22
# 前年コース実績がある選手の学年アップ伸び（デフォルト 2%、上限 5%）
YOY_DEFAULT_IMPROVEMENT = 0.02
YOY_MAX_IMPROVEMENT = 0.05
# 今年フォームが前年コース比例より最大この割合まで遅くても「同程度」とみなし伸びを適用
YOY_FORM_SLOWER_TOLERANCE = 0.03
# 今年駅伝が無く前年コースのみの復帰者は控えめに伸ばす
YOY_PRIOR_ONLY_IMPROVEMENT = 0.015
# 男子1区（3.0km）はトラック換算の楽観を抑え、現実的な下限を置く
MEN_LEG1_FLOOR_SEC = 8 * 60 + 50.0
# 男子3000mトラックSBがある場合、予想がそれより遅いならトラック基準へ引き上げる
# （ロードはトラックより少し遅い想定の加算。前年駅伝が古い／距離比例で過大に遅くなるのを防ぐ）
MEN_TRACK_3000_ROAD_ADD_SEC = 5.0

PRIOR_YEAR_TRANSCRIPT: dict[str, Path] = {
    "男子": ROOT / "input/idaten-corpus/aragyoku/transcripts/2025-男子.json",
    "女子": ROOT / "input/idaten-corpus/aragyoku/transcripts/2025-女子.json",
}
# 去年・一昨年の transcript（復帰候補の正本）
PRIOR_YEAR_TRANSCRIPTS: dict[str, list[Path]] = {
    "男子": [
        ROOT / "input/idaten-corpus/aragyoku/transcripts/2025-男子.json",
        ROOT / "input/idaten-corpus/aragyoku/transcripts/2024-男子.json",
    ],
    "女子": [
        ROOT / "input/idaten-corpus/aragyoku/transcripts/2025-女子.json",
        ROOT / "input/idaten-corpus/aragyoku/transcripts/2024-女子.json",
    ],
}
EVENT_YEAR = 2026
ARAGYOKU_TRANSCRIPT_DIR = ROOT / "input/idaten-corpus/aragyoku/transcripts"
# 卒業済みの明示除外（成績表の学年誤記でも漏れる場合の人間オーバーライド）
EXCLUDED_GRADUATES: frozenset[str] = frozenset(
    {
        nagomi.norm_name("山本悠斗"),  # 天水。2023(3)→卒業済。2025成績表は誤って(1)
    }
)
# 今年度推定学年の証拠を遡る年数（同校・同名の学年逆転誤記耐性。世代重複を抑えるため短め）
GRADUATION_EVIDENCE_LOOKBACK_YEARS = 3

# 公式A成績に無い前年Bチーム実績（人間ヒアリング）。meet=荒玉{year}B で注入。
# grade_was は大会当時の学年。名前未確認は姓または名のみ可。
PRIOR_YEAR_B_TEAM_RETURNERS: list[dict[str, Any]] = [
    # ---- 玉名中 女子 ----
    {
        "name": "清藤 結唯",
        "school": "玉名中",
        "gender": "女子",
        "grade_was": 1,
        "leg": 1,
        "km": 3.0,
        "sec": 11 * 60 + 15,
        "year": 2025,
        "date": "2025-10-15",
        "meet": "荒玉2025B",
        "team_raw": "玉名B",
    },
    {
        "name": "亀木",
        "school": "玉名中",
        "gender": "女子",
        "grade_was": 1,
        "leg": 3,
        "km": 2.0,
        "sec": 7 * 60 + 12,
        "year": 2025,
        "date": "2025-10-15",
        "meet": "荒玉2025B",
        "team_raw": "玉名B",
    },
    {
        "name": "結菜",
        "school": "玉名中",
        "gender": "女子",
        "grade_was": 2,
        "leg": 4,
        "km": 2.0,
        "sec": 7 * 60 + 28,
        "year": 2025,
        "date": "2025-10-15",
        "meet": "荒玉2025B",
        "team_raw": "玉名B",
    },
    # ---- 荒尾三中 女子 B ----
    {
        "name": "小山",
        "school": "荒尾三中",
        "gender": "女子",
        "grade_was": 1,
        "leg": 1,
        "km": 3.0,
        "sec": 12 * 60 + 23,
        "year": 2025,
        "date": "2025-10-15",
        "meet": "荒玉2025B",
        "team_raw": "荒尾三B",
    },
    {
        "name": "竹下",
        "school": "荒尾三中",
        "gender": "女子",
        "grade_was": 1,
        "leg": 5,
        "km": 3.0,
        "sec": 12 * 60 + 47,
        "year": 2025,
        "date": "2025-10-15",
        "meet": "荒玉2025B",
        "team_raw": "荒尾三B",
    },
]

# transcript の短縮校名 → 荒玉予想の学校名
PRIOR_TEAM_TO_SCHOOL: dict[str, str] = {
    "岱明": "岱明中",
    "菊水": "菊水中",
    "玉陵": "玉陵中",
    "南関": "南関中",
    "天水": "天水中",
    "長洲": "長洲中",
    "玉名": "玉名中",
    "玉名高附": "玉名高附",
    "玉高附属": "玉名高附",
    "玉名附": "玉名高附",
    "荒尾三": "荒尾三中",
    "荒尾第三": "荒尾三中",
    "荒尾第四": "荒尾第四中",
    "荒尾四": "荒尾第四中",
    "荒尾海陽": "荒尾海陽中",
    "海陽": "荒尾海陽中",
    "有明": "有明中",
    "玉東": "玉東中",
    "玉南": "玉南中",
    "三加和": "三加和中",
}


def prior_year_leg_km(gender: str, leg_no: int) -> float:
    distances = WOMEN_DISTANCES_KM if gender == "女子" else MEN_DISTANCES_KM
    if 1 <= leg_no <= len(distances):
        return distances[leg_no - 1]
    return distances[0]


def normalize_prior_team_to_school(team: str) -> str | None:
    t = (team or "").strip()
    if not t:
        return None
    if t in PRIOR_TEAM_TO_SCHOOL:
        return PRIOR_TEAM_TO_SCHOOL[t]
    for alias, school in PRIOR_TEAM_TO_SCHOOL.items():
        if alias in t or t in alias:
            return school
    if t.endswith("中"):
        return t
    return f"{t}中"


def eligible_max_grade_in_meet_year(
    meet_year: int, *, event_year: int = EVENT_YEAR
) -> int:
    """当該大会年の学年上限。event_year 時点で中3以下に残る選手だけ。

    例: 2025→学年1–2、2024→学年1のみ。
    """
    return 3 - (event_year - meet_year)


def projected_current_grade(
    grade_was: int, meet_year: int, *, event_year: int = EVENT_YEAR
) -> int:
    """大会当時の学年から、event_year 時点の推定学年を返す。"""
    return int(grade_was) + (event_year - int(meet_year))


def is_current_middle_schooler(
    grade_was: int, meet_year: int, *, event_year: int = EVENT_YEAR
) -> bool:
    """今年度も中学在籍（推定学年 1–3）か。"""
    g = projected_current_grade(grade_was, meet_year, event_year=event_year)
    return 1 <= g <= 3


def load_grade_history(gender: str) -> dict[str, list[tuple[int, int]]]:
    """過去成績表から「学校|氏名」→[(年, 学年), ...]（昇順）。"""
    out: dict[str, list[tuple[int, int]]] = {}
    start = EVENT_YEAR - GRADUATION_EVIDENCE_LOOKBACK_YEARS
    for year in range(start, EVENT_YEAR):
        path = ARAGYOKU_TRANSCRIPT_DIR / f"{year}-{gender}.json"
        if not path.exists():
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        for team_row in raw.get("teams") or []:
            school = normalize_prior_team_to_school(str(team_row.get("team") or ""))
            if not school:
                continue
            for leg in team_row.get("legs") or []:
                name = str(leg.get("name") or "").strip()
                if not name or name.lower() == "unknown":
                    continue
                try:
                    grade_i = int(leg.get("grade"))
                except (TypeError, ValueError):
                    continue
                if grade_i < 1 or grade_i > 3:
                    continue
                key = f"{school}|{nagomi.norm_name(name)}"
                out.setdefault(key, []).append((year, grade_i))
    for key, rows in out.items():
        rows.sort()
        # 同年複数区間は最大学年を残す
        by_year: dict[int, int] = {}
        for y, g in rows:
            by_year[y] = max(by_year.get(y, 0), g)
        out[key] = sorted(by_year.items())
    return out


def is_graduated_by_grade_history(
    history: list[tuple[int, int]], *, event_year: int = EVENT_YEAR
) -> bool:
    """学年履歴から今年度卒業済み／幽霊データかを判定。

    - 最新出場の学年を今年度へ繰り上げて 3 超 → 卒業
    - それ以前の学年から見て、最新出場時点で既に中学卒業相当 → 幽霊（誤記）として除外
    """
    if not history:
        return False
    y_recent, g_recent = history[-1]
    if projected_current_grade(g_recent, y_recent, event_year=event_year) > 3:
        return True
    for y, g in history[:-1]:
        implied_at_recent = int(g) + (int(y_recent) - int(y))
        if implied_at_recent > 3:
            return True
    return False


def load_graduated_school_names(gender: str) -> set[str]:
    """卒業済み（または幽霊）の「学校|氏名」集合。"""
    hist = load_grade_history(gender)
    return {k for k, rows in hist.items() if is_graduated_by_grade_history(rows)}


def is_excluded_graduate(
    name: str,
    *,
    school: str | None = None,
    graduated_keys: set[str] | None = None,
) -> bool:
    """卒業済み（明示リスト or 同校学年履歴）なら True。"""
    key = nagomi.norm_name(name)
    if key in EXCLUDED_GRADUATES:
        return True
    if graduated_keys is None or not school:
        return False
    return f"{school}|{key}" in graduated_keys


def load_prior_year_returners(gender: str) -> list[dict[str, Any]]:
    """去年・一昨年の荒玉で、今年度も在籍し得る学年だった選手を返す。

    陸上部トラックSBが無くても駅伝に出る可能性があるため、校プールと
    直近実績ブレンドの種にする。2025は学年1–2、2024は学年1のみ。
    学年誤記耐性: 同校同名の履歴で卒業／幽霊なら除外（例: 天水・山本悠斗）。
    """
    paths = list(PRIOR_YEAR_TRANSCRIPTS.get(gender) or [])
    if not paths:
        single = PRIOR_YEAR_TRANSCRIPT.get(gender)
        if single is not None:
            paths = [single]
    graduated_keys = load_graduated_school_names(gender)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        if path is None or not Path(path).exists():
            continue
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        year = int(raw.get("year") or 0)
        if year <= 0:
            continue
        max_grade = eligible_max_grade_in_meet_year(year)
        if max_grade < 1:
            continue
        meet_date = str(raw.get("date") or "") or f"{year}-10-15"
        for team_row in raw.get("teams") or []:
            school = normalize_prior_team_to_school(str(team_row.get("team") or ""))
            if not school:
                continue
            for leg in team_row.get("legs") or []:
                try:
                    grade_i = int(leg.get("grade"))
                except (TypeError, ValueError):
                    continue
                if grade_i < 1 or grade_i > max_grade:
                    continue
                if not is_current_middle_schooler(grade_i, year):
                    continue
                name = str(leg.get("name") or "").strip()
                if not name or name.lower() == "unknown":
                    continue
                if is_excluded_graduate(
                    name, school=school, graduated_keys=graduated_keys
                ):
                    continue
                split = nagomi.parse_seconds(leg.get("split"))
                if split is None:
                    continue
                leg_no = int(leg.get("leg") or 0)
                km = prior_year_leg_km(gender, leg_no)
                inj_key = f"{nagomi.norm_name(name)}|{year}|{km:.3f}"
                if inj_key in seen:
                    continue
                seen.add(inj_key)
                out.append(
                    {
                        "name": name,
                        "school": school,
                        "grade_was": grade_i,
                        "leg": leg_no,
                        "km": km,
                        "sec": float(split),
                        "date": meet_date,
                        "year": year,
                        "meet": f"荒玉{year}",
                        "team_raw": str(team_row.get("team") or ""),
                    }
                )
    # 人間ヒアリングの前年Bチーム（A成績表に無い層）
    for row in PRIOR_YEAR_B_TEAM_RETURNERS:
        if gender and row.get("gender") != gender:
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        school = str(row.get("school") or "")
        if is_excluded_graduate(
            name, school=school, graduated_keys=graduated_keys
        ):
            continue
        year = int(row.get("year") or 0)
        grade_was = int(row.get("grade_was") or 0)
        km = float(row.get("km") or 0)
        if year <= 0 or km <= 0:
            continue
        if grade_was >= 1 and not is_current_middle_schooler(grade_was, year):
            continue
        inj_key = f"{nagomi.norm_name(name)}|{year}|{km:.3f}|B"
        if inj_key in seen:
            continue
        seen.add(inj_key)
        out.append(
            {
                "name": name,
                "school": school,
                "grade_was": grade_was,
                "leg": int(row.get("leg") or 0),
                "km": km,
                "sec": float(row["sec"]),
                "date": str(row.get("date") or f"{year}-10-15"),
                "year": year,
                "meet": str(row.get("meet") or f"荒玉{year}B"),
                "team_raw": str(row.get("team_raw") or ""),
            }
        )
    return out


def inject_prior_year_race_marks(gender: str | None = None) -> int:
    """前年復帰選手の区間タイムを RECENT_EKIDEN_MARKS に注入（既存キーと結合）。"""
    genders = [gender] if gender else ["男子", "女子"]
    added = 0
    for g in genders:
        for row in load_prior_year_returners(g):
            key = nagomi.norm_name(row["name"])
            entry = {
                "date": row["date"],
                "km": row["km"],
                "sec": row["sec"],
                "meet": row["meet"],
            }
            cur = RECENT_EKIDEN_MARKS.setdefault(key, [])
            # 同大会・同距離が既にあればスキップ
            if any(
                str(m.get("meet")) == entry["meet"]
                and abs(float(m.get("km") or 0) - entry["km"]) < 1e-6
                for m in cur
            ):
                continue
            cur.append(entry)
            added += 1
    return added


def merge_prior_year_into_pools(
    pools: dict[str, list[tuple[str, float]]],
    gender: str,
    *,
    used_names: set[str] | None = None,
) -> dict[str, list[tuple[str, float]]]:
    """トラックSBが無い去年・一昨年復帰候補を、区間タイム換算で校プールへ追加。"""
    used = used_names or set()
    ref_km = 3.0 if gender == "男子" else 2.0
    by_school: dict[str, list[tuple[str, float]]] = {k: list(v) for k, v in pools.items()}
    present_names: dict[str, list[str]] = {
        school: [n for n, _ in rows] for school, rows in by_school.items()
    }
    # 同一選手が複数年にある場合は最速換算を採用
    best: dict[tuple[str, str], tuple[str, float]] = {}
    for row in load_prior_year_returners(gender):
        key = nagomi.norm_name(row["name"])
        if key in used:
            continue
        school = str(row["school"])
        if any(
            is_same_athlete(row["name"], existing)
            for existing in present_names.get(school, [])
        ):
            continue
        score = float(row["sec"]) * ref_km / float(row["km"])
        pk = (school, canonicalize_athlete_name(row["name"]))
        prev = best.get(pk)
        if prev is None or score < prev[1]:
            best[pk] = (str(row["name"]), score)
    for (school, _ck), (name, score) in best.items():
        if any(
            is_same_athlete(name, existing)
            for existing in present_names.get(school, [])
        ):
            continue
        by_school.setdefault(school, []).append((name, score))
        present_names.setdefault(school, []).append(name)
    for school, rows in by_school.items():
        rows.sort(key=lambda x: (x[1], nagomi.norm_name(x[0])))
        # 近似同名を再除去
        cleaned: list[tuple[str, float]] = []
        for name, score in rows:
            if any(is_same_athlete(name, e) for e, _ in cleaned):
                continue
            cleaned.append((name, score))
        by_school[school] = cleaned
    return by_school


def parse_mark_date(mark_date: str | None) -> date | None:
    if not mark_date:
        return None
    raw = str(mark_date).strip()[:10].replace("/", "-")
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def recency_weight(mark_date: str | None, event_date: date) -> float:
    """イベント日に近いほど大きい指数減衰重み。日付欠落は半減期×3相当。"""
    parsed = parse_mark_date(mark_date)
    if parsed is None:
        days = FORM_HALF_LIFE_DAYS * 3
    else:
        days = max(0.0, float((event_date - parsed).days))
    return 0.5 ** (days / FORM_HALF_LIFE_DAYS)


def sb_source_date(details: dict[str, Any], note: str) -> str | None:
    if "1500" in note and details.get("1500m") and details["1500m"].date:
        return details["1500m"].date
    if "800" in note and details.get("800m") and details["800m"].date:
        return details["800m"].date
    if "3000" in note and details.get("3000m") and details["3000m"].date:
        return details["3000m"].date
    for key in ("1500m", "3000m", "800m"):
        mark = details.get(key)
        if mark and mark.date:
            return mark.date
    return None


def aragyoku_meet_year(meet: str) -> int | None:
    m = re.search(r"荒玉(\d{4})", str(meet))
    return int(m.group(1)) if m else None


def prior_year_blend_weight(meet: str) -> float:
    """荒玉 transcript 由来マークのブレンド重み（去年強め・一昨年弱め）。"""
    year = aragyoku_meet_year(meet)
    if year is None:
        return PRIOR_YEAR_COURSE_WEIGHT
    age = EVENT_YEAR - year
    if age <= 1:
        return PRIOR_YEAR_COURSE_WEIGHT
    return PRIOR_YEAR_MINUS_2_WEIGHT


def fmt_race_fact(mark: dict[str, Any]) -> str:
    """駅伝マークを事実として短く書く（大会・実測・距離・日付）。"""
    meet = str(mark.get("meet") or "駅伝")
    sec = float(mark["sec"])
    km = float(mark["km"])
    d = str(mark.get("date") or "").strip()
    date_bit = f"({d})" if d else ""
    return f"{meet} {fmt_time(sec, 1)}@{km:.1f}km{date_bit}"


def fmt_sb_mark_fact(mark: Any) -> str:
    """トラックSBマークを事実として短く書く。"""
    if mark is None:
        return ""
    text = getattr(mark, "text", None) or fmt_time(float(getattr(mark, "seconds", 0)), 2)
    d = getattr(mark, "date", None) or ""
    return f"{text}@{d}" if d else str(text)


def blend_with_recent_form(
    name: str,
    distance_km: float,
    sb_pred: float | None,
    sb_date: str | None,
    *,
    event_date: date,
    gender: str = "男子",
) -> tuple[float | None, str]:
    """トラックSB予想と直近駅伝実績を減衰重みでブレンドする。

    直近駅伝がある場合は SB 重みを性別スケールで抑え、ロード実績を主にする。
    去年・一昨年の荒玉は半減期では消えすぎるため固定重みで残す（一昨年は弱め）。
    戻り値の note は大会名・実測タイム・距離・比例値・重みを含む事実エビデンス。
    """
    race_marks = list(RECENT_EKIDEN_MARKS.get(nagomi.norm_name(name), []))
    # 荒玉が複数年ある場合は最新年のみブレンド（一昨年はプール補充用）
    aragyoku_marks = [m for m in race_marks if str(m.get("meet") or "").startswith("荒玉")]
    other_marks = [m for m in race_marks if not str(m.get("meet") or "").startswith("荒玉")]
    if aragyoku_marks:
        best_y = max(aragyoku_meet_year(str(m.get("meet"))) or 0 for m in aragyoku_marks)
        aragyoku_marks = [
            m
            for m in aragyoku_marks
            if (aragyoku_meet_year(str(m.get("meet"))) or 0) == best_y
        ]
    race_marks = other_marks + aragyoku_marks
    only_prior_aragyoku = bool(race_marks) and all(
        str(m.get("meet") or "").startswith("荒玉") for m in race_marks
    )
    if gender == "女子" and race_marks:
        sb_scale = WOMEN_SB_WEIGHT_SCALE
    elif gender == "男子" and race_marks:
        # 前年荒玉のみ（今年なごみ/Jr無し）のとき、直近3000mトラックを抑えすぎない
        sb_scale = 1.0 if only_prior_aragyoku else MEN_SB_WEIGHT_SCALE
    else:
        sb_scale = 1.0
    # (weight, scaled_sec, evidence_label)
    samples: list[tuple[float, float, str]] = []
    if sb_pred is not None and sb_scale > 0:
        w_sb = recency_weight(sb_date, event_date) * sb_scale
        samples.append((w_sb, sb_pred, f"SB{fmt_time(sb_pred, 1)}"))
    for mark in race_marks:
        scaled = float(mark["sec"]) * distance_km / float(mark["km"])
        meet = str(mark.get("meet") or "")
        if meet.startswith("荒玉"):
            w = prior_year_blend_weight(meet)
        else:
            w = recency_weight(str(mark["date"]), event_date)
        samples.append(
            (w, scaled, f"{fmt_race_fact(mark)}→比例{fmt_time(scaled, 1)}")
        )
    if not samples:
        return sb_pred, ""
    total_w = sum(w for w, _, _ in samples)
    blended = sum(w * sec for w, sec, _ in samples) / total_w
    race_bits = [label for _, _, label in samples if not label.startswith("SB")]
    if not race_bits:
        return blended, ""
    parts = [f"{label}(w={w:.2f})" for w, _, label in samples]
    return blended, "駅伝加味:" + "+".join(parts) + f"→加重{fmt_time(blended, 1)}"


def _newest_aragyoku_marks(race_marks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aragyoku = [m for m in race_marks if str(m.get("meet") or "").startswith("荒玉")]
    if not aragyoku:
        return []
    best_y = max(aragyoku_meet_year(str(m.get("meet"))) or 0 for m in aragyoku)
    return [
        m
        for m in aragyoku
        if (aragyoku_meet_year(str(m.get("meet"))) or 0) == best_y
    ]


def apply_yoy_course_growth(
    name: str,
    distance_km: float,
    blended: float | None,
) -> tuple[float | None, str]:
    """前年荒玉コース実績をベースに、今年の学年アップ伸びを反映する。

    - 前年コース比例タイム × (1 − 伸び率) を成長予想とする。
    - 今年駅伝が前年より速い／同程度（許容内）ならデフォルト〜実測の伸びを適用。
    - 今年フォームが明らかに遅い場合は伸びを強制しない。
    - 最終は min(ブレンド, 成長予想)。すでにブレンドが速い場合はそのまま。
    """
    if blended is None:
        return None, ""
    race_marks = list(RECENT_EKIDEN_MARKS.get(nagomi.norm_name(name), []))
    aragyoku = _newest_aragyoku_marks(race_marks)
    if not aragyoku:
        return blended, ""
    prior_scaled = min(
        float(m["sec"]) * distance_km / float(m["km"]) for m in aragyoku
    )
    if prior_scaled <= 0:
        return blended, ""
    current = [m for m in race_marks if not str(m.get("meet") or "").startswith("荒玉")]
    best_y = aragyoku_meet_year(str(aragyoku[0].get("meet"))) or 0
    age = EVENT_YEAR - best_y if best_y else 1

    if current:
        # 前年／対象距離に近いマークを優先（距離比例の過大評価を抑える）
        prior_kms = [float(m["km"]) for m in aragyoku]
        preferred = [
            m
            for m in current
            if abs(float(m["km"]) - distance_km) <= 0.25
            or any(abs(float(m["km"]) - pk) <= 0.25 for pk in prior_kms)
        ]
        form_marks = preferred or current
        cur_scaled = min(
            float(m["sec"]) * distance_km / float(m["km"]) for m in form_marks
        )
        ratio = cur_scaled / prior_scaled
        if ratio < 1.0:
            measured = 1.0 - ratio
            improvement = min(
                max(measured, YOY_DEFAULT_IMPROVEMENT),
                YOY_MAX_IMPROVEMENT,
            )
        elif ratio <= 1.0 + YOY_FORM_SLOWER_TOLERANCE:
            improvement = YOY_DEFAULT_IMPROVEMENT
        else:
            return blended, ""
    else:
        # 前年のみ: 一昨年復帰は少し多め、去年復帰は控えめ
        improvement = (
            YOY_PRIOR_ONLY_IMPROVEMENT * 1.5
            if age >= 2
            else YOY_PRIOR_ONLY_IMPROVEMENT
        )

    grown = prior_scaled * (1.0 - improvement)
    if grown >= blended - 0.05:
        return blended, ""
    pct = improvement * 100.0
    prior_mark = min(
        aragyoku,
        key=lambda m: float(m["sec"]) * distance_km / float(m["km"]),
    )
    return grown, (
        f"前年伸び:{fmt_race_fact(prior_mark)}→比例{fmt_time(prior_scaled, 1)}"
        f"×-{pct:.0f}%→{fmt_time(grown, 1)}採用"
        f"（ブレンド{fmt_time(blended, 1)}より速い）"
    )


def apply_men_leg1_floor(pred: float | None, gender: str, leg_no: int) -> tuple[float | None, str]:
    if pred is None or gender != "男子" or leg_no != 1:
        return pred, ""
    if pred < MEN_LEG1_FLOOR_SEC:
        return (
            MEN_LEG1_FLOOR_SEC,
            f"1区下限:計算{fmt_time(pred, 1)}→{fmt_time(MEN_LEG1_FLOOR_SEC, 1)}",
        )
    return pred, ""


def apply_men_track_3000m_cap(
    pred: float | None,
    gender: str,
    marks: dict[str, Any],
    distance_km: float,
    *,
    road_add_sec: float = MEN_TRACK_3000_ROAD_ADD_SEC,
) -> tuple[float | None, str]:
    """男子で3000mトラックSBがあるとき、予想がトラック比例より遅すぎる場合は引き上げる。

    前年荒玉の距離比例や区間バイアスで、直近3000m（例: 9:14）より大幅に遅い
    予想（例: 9:55）になるのを防ぐ。ロードはトラックより少し遅い想定で加算する。
    すでにトラック基準より速い予想（直近駅伝など）はそのまま。
    """
    if pred is None or gender != "男子":
        return pred, ""
    m3000 = marks.get("3000m") if marks else None
    if m3000 is None:
        return pred, ""
    track_scaled = float(m3000.seconds) * distance_km / 3.0
    cap = track_scaled + float(road_add_sec)
    if pred <= cap + 0.05:
        return pred, ""
    return cap, (
        f"3000mトラック優先:{fmt_sb_mark_fact(m3000)}"
        f"→区間{distance_km:g}km比例{fmt_time(track_scaled, 1)}"
        f"+{road_add_sec:.0f}s={fmt_time(cap, 1)}"
        f"（計算{fmt_time(pred, 1)}より速い）"
    )


def human_notes_paths(gender: str) -> list[Path]:
    name = HUMAN_NOTES_FILENAME[gender]
    return [MEET_DIR / name, CORPUS_MEET / name]


def empty_human_notes(gender: str) -> dict[str, Any]:
    return {
        "gender": gender,
        "updated": "",
        "memo": "",
        "adjustments": [],
    }


def load_human_notes(gender: str, *, path: Path | None = None) -> dict[str, Any]:
    """人間考慮 YAML を読む。Drive 側を優先、なければコーパス、どちらも無ければ空。"""
    candidates = [path] if path is not None else human_notes_paths(gender)
    for p in candidates:
        if p is None or not p.exists():
            continue
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            continue
        notes = empty_human_notes(gender)
        notes["updated"] = str(raw.get("updated") or "")
        notes["memo"] = str(raw.get("memo") or "").strip()
        adj = raw.get("adjustments") or []
        notes["adjustments"] = [a for a in adj if isinstance(a, dict)]
        notes["_path"] = str(p)
        return notes
    return empty_human_notes(gender)


def _adj_matches(
    adj: dict[str, Any],
    *,
    athlete: str,
    team: str,
    leg_no: int,
) -> bool:
    ath = adj.get("athlete")
    tm = adj.get("team")
    leg = adj.get("leg")
    if ath:
        if nagomi.norm_name(str(ath)) != nagomi.norm_name(athlete):
            return False
        if tm and str(tm) not in team and team not in str(tm):
            return False
        if leg is not None and int(leg) != leg_no:
            return False
        return True
    if tm and leg is not None:
        return (str(tm) in team or team in str(tm)) and int(leg) == leg_no
    if tm:
        # team のみ → その校の全区間に適用（フォーム落ちなど校単位の人間考慮）
        return str(tm) in team or team in str(tm)
    return False


def apply_human_adjustments(
    pred: float | None,
    *,
    athlete: str,
    team: str,
    leg_no: int,
    notes: dict[str, Any] | None,
) -> tuple[float | None, str]:
    """人間考慮の adjustments を順に適用。set_sec > delta_sec → min/max。"""
    if pred is None or not notes:
        return pred, ""
    bits: list[str] = []
    out = float(pred)
    for adj in notes.get("adjustments") or []:
        if not _adj_matches(adj, athlete=athlete, team=team, leg_no=leg_no):
            continue
        reason = str(adj.get("reason") or "").strip() or "人間考慮"
        if adj.get("set_sec") is not None:
            out = float(adj["set_sec"])
            bits.append(f"人間set={fmt_time(out)}({reason})")
            continue
        if adj.get("delta_sec") is not None:
            delta = float(adj["delta_sec"])
            out += delta
            sign = f"{delta:+.0f}s"
            bits.append(f"人間{sign}({reason})")
        if adj.get("min_sec") is not None:
            floor = float(adj["min_sec"])
            if out < floor:
                out = floor
                bits.append(f"人間min={fmt_time(floor)}({reason})")
        if adj.get("max_sec") is not None:
            ceil = float(adj["max_sec"])
            if out > ceil:
                out = ceil
                bits.append(f"人間max={fmt_time(ceil)}({reason})")
    return out, " / ".join(bits)


def ensure_human_notes_files() -> None:
    """欠落時のみテンプレ YAML を dual-write（既存は上書きしない）。"""
    seeds = {
        "女子": {
            "gender": "女子",
            "updated": "2026-09-27",
            "memo": (
                "女子はトラックSBよりなごみ／ジュニア駅伝実績を主に予想する"
                f"（SB重み×{WOMEN_SB_WEIGHT_SCALE}）。"
                "Jrでスタミナ不足が露呈。南関A（Jr 35:27）をベンチマーク。"
                "人間加減は直近駅伝ブレンド後の微調整用。"
                "岱明・山﨑莉奈2区は6:50線。玉名・川原芽吹は今年フォーム落ちで1/5区外（3区）。"
            ),
            "adjustments": [
                {
                    "athlete": "山﨑 莉奈",
                    "team": "岱明中",
                    "leg": 2,
                    "set_sec": 6 * 60 + 50,
                    "reason": "2区は6:50でいける",
                },
                {
                    "athlete": "川原 芽吹",
                    "delta_sec": 45,
                    "reason": "今年フォーム落ち。前年A1区実績の伸びを打ち消し、直近トラック寄りに",
                },
            ],
        },
        "男子": {
            "gender": "男子",
            "updated": "2026-09-27",
            "memo": (
                "Jr実績は総合ほぼ一致。直近駅伝ブレンド済み。"
                "松野は本番9:20線。田上4区は9:40線。今村は昨年9:38以上を期待しつつ"
                "プレッシャーは掛けない。5–6人目は厳しい。"
                "菊水1区はトラック楽観を抑え、現実的な下限感を維持。"
                "玉名高附・小倉由宇: なごみ2区10:30は不調のみ。Jr CS 4区8:48を実力線"
                "（なごみはRECENT非注入）。"
                "南関男子は直近フォームが上がらず、校単位で+20s。"
            ),
            "adjustments": [
                {
                    "athlete": "松野 凛空",
                    "set_sec": 9 * 60 + 20,
                    "reason": "本番1区は9:20でいける",
                },
                {
                    "athlete": "田上 颯人",
                    "team": "岱明中",
                    "leg": 4,
                    "set_sec": 9 * 60 + 40,
                    "reason": "4区は9:40でいける",
                },
                {
                    "athlete": "今村 昇磨",
                    "delta_sec": -8,
                    "reason": "本番覚醒・殻破り期待（昨年9:38以上）",
                },
                {
                    "athlete": "山本 哲瑠",
                    "delta_sec": -3,
                    "reason": "なごみより上向き・競り合いで燃える",
                },
                {
                    "team": "菊水中",
                    "leg": 1,
                    "min_sec": 8 * 60 + 50,
                    "reason": "1区はどんなに速くても8:50前後が現実線",
                },
                {
                    "team": "南関中",
                    "delta_sec": 20,
                    "reason": "直近フォーム上がらず。Jr以降も調子が乗りきれていない",
                },
            ],
        },
    }
    for gender, payload in seeds.items():
        text = yaml.safe_dump(
            payload,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
        header = (
            f"# 荒玉2026 {gender} — 人間の考慮事項（編集可）\n"
            "# adjustments: athlete または team+leg を指定。\n"
            "#   delta_sec: 秒の加減（負=速く / 正=遅く）\n"
            "#   set_sec: 絶対秒で上書き\n"
            "#   min_sec / max_sec: 下限・上限\n"
            "# 再生成時、既存ファイルは上書きされない。\n"
        )
        for path in human_notes_paths(gender):
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                continue
            path.write_text(header + text, encoding="utf-8")


def predict_leg(
    name: str,
    gender: str,
    distance_km: float,
    sb_index: dict,
    *,
    bias_sec: float = 0.0,
) -> tuple[float | None, dict, str]:
    athlete = sb_index.get(nagomi.norm_name(name))
    marks = athlete.marks if athlete else {}
    details = {d: marks.get(d) for d in ("800m", "1500m", "3000m")}
    if gender == "女子":
        if details["1500m"]:
            base = details["1500m"].seconds * (2 / 1.5) + nagomi.WOMEN_1500_TO_2K_ADD
            formula = "1500m SB→2km式を距離比例"
            sb_fact = f"1500m {fmt_sb_mark_fact(details['1500m'])}"
        elif details["800m"]:
            m = details["800m"].seconds
            base = m * (2000 / 800) ** nagomi.RIEGEL * nagomi.WOMEN_800_TO_2K_COEF
            formula = "800m SB→2km式を距離比例"
            sb_fact = f"800m {fmt_sb_mark_fact(details['800m'])}"
        else:
            return None, details, "記録なし（5ヶ月窓内）"
        pred = base * distance_km / 2 + bias_sec
        note = f"SB:{sb_fact}→{formula}→区間{distance_km:g}km={fmt_time(pred, 1)}"
        if bias_sec:
            note += f"＋区間バイアス{bias_sec:+.0f}s"
        return pred, details, note

    m1500, m800, m3000 = details["1500m"], details["800m"], details["3000m"]
    from_1500 = m1500.seconds * 2 + nagomi.MEN_1500_TO_3K_ADD if m1500 else None
    from_800 = (
        m800.seconds * (3000 / 800) ** nagomi.RIEGEL * nagomi.MEN_800_TO_3K_COEF
        if m800
        else None
    )
    if m3000:
        if from_1500 is not None and m3000.seconds >= from_1500 + MEN_3000M_FALLBACK_THRESHOLD_SEC:
            base = from_1500
            formula = f"1500m SB→3km式（3000mが+{m3000.seconds - from_1500:.0f}s遅い）"
            sb_fact = f"1500m {fmt_sb_mark_fact(m1500)}（3000m {fmt_sb_mark_fact(m3000)}不採用）"
        elif (
            from_1500 is None
            and from_800 is not None
            and m3000.seconds >= from_800 + MEN_3000M_FALLBACK_THRESHOLD_SEC
        ):
            base = from_800
            formula = "800m SB→3km式（3000mが遅い）"
            sb_fact = f"800m {fmt_sb_mark_fact(m800)}（3000m {fmt_sb_mark_fact(m3000)}不採用）"
        else:
            base = m3000.seconds
            formula = "3000m SBを距離比例"
            sb_fact = f"3000m {fmt_sb_mark_fact(m3000)}"
    elif from_1500 is not None:
        base = from_1500
        formula = "1500m SB→3km式を距離比例"
        sb_fact = f"1500m {fmt_sb_mark_fact(m1500)}"
    elif from_800 is not None:
        base = from_800
        formula = "800m SB→3km式を距離比例"
        sb_fact = f"800m {fmt_sb_mark_fact(m800)}"
    else:
        return None, details, "記録なし（5ヶ月窓内）"
    pred = base * distance_km / 3 + bias_sec
    note = f"SB:{sb_fact}→{formula}→区間{distance_km:g}km={fmt_time(pred, 1)}"
    if bias_sec:
        note += f"＋区間バイアス{bias_sec:+.0f}s"
    return pred, details, note


def fmt_time(seconds: float | None, decimals: int = 1) -> str:
    if seconds is None:
        return "—"
    total = int(round(seconds * (10**decimals)))
    unit = 10**decimals
    mins, rem = divmod(total, 60 * unit)
    sec, frac = divmod(rem, unit)
    return f"{mins}:{sec:02d}" + (f".{frac:0{decimals}d}" if decimals else "")


def fmt_total(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    total = int(round(seconds))
    mins, sec = divmod(total, 60)
    return f"{mins}:{sec:02d}"


def mark_text(mark: nagomi.Mark | None) -> str:
    if not mark:
        return "—"
    date = f" @{mark.date}" if mark.date else ""
    return f"{mark.text}{date}"


def md_mark(mark: nagomi.Mark | None) -> str:
    if not mark:
        return ""
    return mark.text


def is_confirmed_leg(team: str, gender: str, leg_no: int) -> bool:
    if "岱明" not in team:
        return False
    known = TAIMEI_KNOWN_LEGS.get(gender, {})
    return leg_no in known


def build_team(
    row: dict[str, Any],
    gender: str,
    sb_index: dict,
    *,
    event_date: date | None = None,
    human_notes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    distances = WOMEN_DISTANCES_KM if gender == "女子" else MEN_DISTANCES_KM
    biases = LEG_BIAS_SEC[gender]
    names: list[str] = list(row["legs"])
    if len(names) != len(distances):
        raise ValueError(f"{row['team']} {gender}: expected {len(distances)} legs, got {len(names)}")
    as_of_event = event_date or date.fromisoformat(EVENT_DATE)
    notes = human_notes if human_notes is not None else load_human_notes(gender)

    details: list[dict[str, Any]] = []
    preds: list[float | None] = []
    for i, name in enumerate(names):
        leg_no = i + 1
        if not str(name).strip():
            preds.append(None)
            details.append(
                {
                    "leg": leg_no,
                    "name": "",
                    "km": distances[i],
                    "pred": None,
                    "marks": {},
                    "note": "※仮 / 候補不足（同一選手の複数区間は禁止）",
                    "confirmed": False,
                }
            )
            continue
        bias = biases[i] if i < len(biases) else 0.0
        # 直近駅伝がある選手はロード実績で補正するため区間バイアスを重ねない
        has_recent = nagomi.norm_name(name) in RECENT_EKIDEN_MARKS
        pred, marks, note = predict_leg(
            name,
            gender,
            distances[i],
            sb_index,
            bias_sec=0.0 if has_recent else bias,
        )
        if pred is None and has_recent:
            note = "SBなし（トラック5ヶ月窓内記録なし）"
        sb_date = sb_source_date(marks, note)
        pred, form_note = blend_with_recent_form(
            name,
            distances[i],
            pred,
            sb_date,
            event_date=as_of_event,
            gender=gender,
        )
        if form_note:
            note = f"{note} / {form_note}"
        pred, yoy_note = apply_yoy_course_growth(name, distances[i], pred)
        if yoy_note:
            note = f"{note} / {yoy_note}"
        pred, floor_note = apply_men_leg1_floor(pred, gender, leg_no)
        if floor_note:
            note = f"{note} / {floor_note}"
        pred, track_note = apply_men_track_3000m_cap(pred, gender, marks, distances[i])
        if track_note:
            note = f"{note} / {track_note}"
        pred, human_note = apply_human_adjustments(
            pred,
            athlete=name,
            team=row["team"],
            leg_no=leg_no,
            notes=notes,
        )
        if human_note:
            note = f"{note} / {human_note}"
        # 最終予想タイムをエビデンス末尾に明示（全選手共通）
        if pred is not None:
            note = f"{note} →予想{fmt_time(pred, 1)}"
        confirmed = is_confirmed_leg(row["team"], gender, leg_no)
        if not confirmed:
            note = f"※仮 / {note}"
        else:
            note = f"確定 / {note}"
        preds.append(pred)
        details.append(
            {
                "leg": leg_no,
                "name": name,
                "km": distances[i],
                "pred": pred,
                "marks": marks,
                "note": note,
                "confirmed": confirmed,
            }
        )
    known_n = sum(v is not None for v in preds)
    complete = known_n == len(distances)
    total = sum(v for v in preds if v is not None) if complete else None
    return {
        "no": row["no"],
        "team": row["team"],
        "source": row.get("source", ""),
        "order_notes": row.get("notes", ""),
        "legs": details,
        "preds": preds,
        "complete": complete,
        "total": total,
        "known_n": known_n,
        "reserves": [],
        "human_memo": notes.get("memo", ""),
        "human_updated": notes.get("updated", ""),
        "human_notes_path": notes.get("_path", ""),
    }


def build_taimei_team(gender: str, sb_index: dict) -> dict:
    """後方互換: 岱明行だけを仮オーダーから取り出す。"""
    for row in get_provisional_orders(gender, sb_index):
        if "岱明" in row["team"]:
            return build_team(row, gender, sb_index)
    raise KeyError("岱明中 not in provisional orders")


def attach_predicted_leg_ranks(
    teams: list[dict[str, Any]],
    n_legs: int,
    *,
    field_suffix: str = "",
) -> None:
    """実SB予想があるチームのみ、区間順位・通過順位を付ける（中央値補完なし）。"""
    if not teams:
        return
    suf = field_suffix
    usable: list[dict[str, Any]] = []
    for t in teams:
        parts: list[float] = []
        ok = True
        for det in t["legs"]:
            if det["pred"] is None:
                ok = False
                break
            parts.append(det["pred"])
        if not ok or len(parts) != n_legs:
            continue
        cum = 0.0
        for det, sec in zip(t["legs"], parts):
            cum += sec
            det[f"pred_used{suf}"] = sec
            det[f"pred_cum{suf}"] = cum
            det[f"pred_imputed_leg{suf}"] = False
        usable.append(t)

    for leg_i in range(n_legs):
        by_sec = sorted(usable, key=lambda t: t["legs"][leg_i][f"pred_used{suf}"])
        for rank, t in enumerate(by_sec, start=1):
            t["legs"][leg_i][f"pred_sec_rank{suf}"] = rank
        by_cum = sorted(usable, key=lambda t: t["legs"][leg_i][f"pred_cum{suf}"])
        for rank, t in enumerate(by_cum, start=1):
            t["legs"][leg_i][f"pred_cum_rank{suf}"] = rank


def fmt_leg_pred_cell(det: dict[str, Any], *, places: int = 1, field_suffix: str = "") -> str:
    """総合順位表の1セル。選手名＋(通過順)通過 / (区間順)区間。"""
    suf = field_suffix
    name = str(det.get("name") or "").strip().replace(" ", "")
    sec = det.get(f"pred_used{suf}")
    if sec is None:
        if det.get("pred") is not None:
            time_s = fmt_time(det["pred"], places)
            return f"{name} {time_s}".strip() if name else time_s
        return name
    cum = det.get(f"pred_cum{suf}")
    sec_r = det.get(f"pred_sec_rank{suf}")
    cum_r = det.get(f"pred_cum_rank{suf}")
    sec_s = fmt_time(sec, places)
    cum_s = fmt_time(cum, places) if cum is not None else ""
    if cum_r is not None and sec_r is not None and cum_s:
        body = f"({cum_r}){cum_s} / ({sec_r}){sec_s}"
    elif sec_r is not None:
        body = f"({sec_r}){sec_s}"
    else:
        body = sec_s
    return f"{name} {body}".strip() if name else body


def build_report(gender: str, sb_index: dict, *, as_of: str) -> dict[str, Any]:
    distances = WOMEN_DISTANCES_KM if gender == "女子" else MEN_DISTANCES_KM
    n_legs = len(distances)
    inject_prior_year_race_marks(gender)
    human_notes = load_human_notes(gender)
    order_rows = get_provisional_orders(gender, sb_index)
    teams_out = [
        build_team(row, gender, sb_index, human_notes=human_notes)
        for row in order_rows
    ]

    # 実SBのみ。欠測区間は補完しない（総合・順位対象外）。
    for t in teams_out:
        if t["complete"] and t["total"] is not None:
            t["total_ref"] = t["total"]
            t["imputed"] = False
        else:
            t["total_ref"] = None
            t["imputed"] = False

    ranked_complete = sorted(
        [t for t in teams_out if t["complete"] and t["total"] is not None],
        key=lambda t: t["total"],
    )
    for i, t in enumerate(ranked_complete, start=1):
        t["rank"] = i
        t["rank_ref"] = i
    for t in teams_out:
        if t not in ranked_complete:
            t["rank"] = None
            t["rank_ref"] = None

    attach_predicted_leg_ranks(ranked_complete, n_legs, field_suffix="")
    # _full は同じ集合（実データのみ）
    for t in ranked_complete:
        for det in t["legs"]:
            det["pred_used_full"] = det.get("pred_used")
            det["pred_cum_full"] = det.get("pred_cum")
            det["pred_sec_rank_full"] = det.get("pred_sec_rank")
            det["pred_cum_rank_full"] = det.get("pred_cum_rank")
            det["pred_imputed_leg_full"] = False

    return {
        "gender": gender,
        "distances": distances,
        "teams": teams_out,
        "ranked": ranked_complete,
        "ranked_ref": ranked_complete,
        "median_fill": None,
        "leg_medians": None,
        "as_of": as_of,
        "event_date": EVENT_DATE,
        "human_notes": human_notes,
    }


def render_markdown(report: dict[str, Any], *, freshness: int | None) -> str:
    g = report["gender"]
    distances = report["distances"]
    n_legs = len(distances)
    leg_headers = [f"{i}区" for i in range(1, n_legs + 1)]
    lines: list[str] = []
    lines.append(f"# 荒玉中体連駅伝 2026 {g} 区間オーダー × SB予想（仮置き込み）")
    lines.append("")
    lines.append(
        f"as_of: {report['as_of']} / event_date: {report['event_date']} / "
        f"freshness_days: {freshness}"
    )
    lines.append("")
    hn = report.get("human_notes") or {}
    memo = str(hn.get("memo") or "").strip()
    if memo or hn.get("adjustments"):
        lines.append("## 人間考慮事項")
        lines.append("")
        src = hn.get("_path") or HUMAN_NOTES_FILENAME.get(g, "")
        try:
            src_disp = str(Path(src).name) if src else HUMAN_NOTES_FILENAME.get(g, "")
        except Exception:
            src_disp = HUMAN_NOTES_FILENAME.get(g, "")
        updated = hn.get("updated") or "—"
        lines.append(f"- 編集ファイル: `{src_disp}`（updated: {updated}）")
        lines.append(
            "- 調整キー: `delta_sec`（加減）/ `set_sec`（絶対）/ `min_sec`・`max_sec`（上下限）。"
            "`athlete` または `team`+`leg`"
        )
        if memo:
            lines.append("")
            lines.append(memo)
        adj = hn.get("adjustments") or []
        if adj:
            lines.append("")
            lines.append("| 対象 | 調整 | 理由 |")
            lines.append("| --- | --- | --- |")
            for a in adj:
                if a.get("athlete"):
                    target = str(a["athlete"])
                    if a.get("leg") is not None:
                        target += f" {a['leg']}区"
                else:
                    target = f"{a.get('team', '?')} {a.get('leg', '?')}区"
                parts: list[str] = []
                if a.get("set_sec") is not None:
                    parts.append(f"set {fmt_time(float(a['set_sec']))}")
                if a.get("delta_sec") is not None:
                    parts.append(f"{float(a['delta_sec']):+.0f}s")
                if a.get("min_sec") is not None:
                    parts.append(f"min {fmt_time(float(a['min_sec']))}")
                if a.get("max_sec") is not None:
                    parts.append(f"max {fmt_time(float(a['max_sec']))}")
                lines.append(
                    f"| {target} | {', '.join(parts) or '—'} | {a.get('reason', '')} |"
                )
        lines.append("")
        lines.append("---")
        lines.append("")
    lines.append("## 予測式")
    lines.append("")
    if g == "男子":
        lines.append(
            f"- **3km予想（1500m）**: `SB秒 × 2 + {nagomi.MEN_1500_TO_3K_ADD:.0f}` を距離比例"
        )
        lines.append(
            f"- **3km予想（800m）**: `SB秒 × (3000/800)^{nagomi.RIEGEL} × {nagomi.MEN_800_TO_3K_COEF}`"
        )
        lines.append(
            f"- **3000m SB**: 1500換算より **{MEN_3000M_FALLBACK_THRESHOLD_SEC:.0f}秒以上遅い** 場合は1500換算"
        )
    else:
        lines.append(
            f"- **2km予想（1500m）**: `SB秒 × (2/1.5) + {nagomi.WOMEN_1500_TO_2K_ADD:.0f}` を距離比例"
        )
        lines.append(
            f"- **2km予想（800m）**: `SB秒 × (2000/800)^{nagomi.RIEGEL} × {nagomi.WOMEN_800_TO_2K_COEF}`"
        )
    lines.append(
        "- SBは2026採用SB・Notion・玉名郡ナイター（SB明記）のうち as_of以前かつ freshness 以内のみ"
    )
    lines.append("- 区間バイアス: `LEG_BIAS_SEC`（歴代荒玉キャリブ。直近駅伝がある選手は未適用）")
    lines.append(
        f"- **直近駅伝ブレンド**: なごみ／ジュニア実績を距離比例し、"
        f"イベント日からの半減期{FORM_HALF_LIFE_DAYS:.0f}日でトラックSBと加重平均（新しいほど重い）"
    )
    lines.append(
        f"- **前年コース伸び**: 荒玉前年実績がある選手は前年比例×(1−伸び率)を下限に適用"
        f"（デフォルト{YOY_DEFAULT_IMPROVEMENT * 100:.0f}%、今年フォームが同程度〜良い場合。"
        f"明らかに後退している場合は未適用）"
    )
    if g == "女子":
        lines.append(
            f"- **女子のSB重み**: 直近駅伝がある選手はトラックSBを×{WOMEN_SB_WEIGHT_SCALE}"
            "（なごみ／ジュニア主・トラック従）"
        )
    else:
        lines.append(
            f"- **男子のSB重み**: 直近駅伝がある選手はトラックSBを×{MEN_SB_WEIGHT_SCALE}"
            f"（前年荒玉は固定重み×{PRIOR_YEAR_COURSE_WEIGHT}）"
        )
    lines.append(
        "- **人間考慮**: `人間考慮_女子.yaml` / `人間考慮_男子.yaml` のメモと adjustments を最終適用"
    )
    if g == "男子":
        lines.append(
            f"- **1区下限**: {fmt_time(MEN_LEG1_FLOOR_SEC)}（トラック換算の楽観抑制）"
        )
        lines.append(
            f"- **3000mトラック優先**: 男子で3000m SBがあるとき、予想が区間比例"
            f"+{MEN_TRACK_3000_ROAD_ADD_SEC:.0f}s より遅い場合はトラック基準へ引き上げ"
            "（前年駅伝の距離比例で遅くなりすぎるのを防ぐ）"
        )
    lines.append(
        "- **オーダー**: 公式未着のためジュニア／所属SB上位で**全区間仮置き**。"
        "岱明女子・男子1–4のみ監督確定。エビデンス列の「※仮」が仮置き"
    )
    lines.append(
        "- **総合順位**: 全区間に**実SBまたは直近駅伝由来**の予想があるチームのみ（中央値・欠測補完なし）"
    )
    lines.append(
        "- **各区セル**: `選手名 (通過順)通過予想 / (区間順)区間記録`（名は空白除去）"
    )
    lines.append(f"- 区間距離(km): {', '.join(str(d) for d in distances)}")
    lines.append(
        "- クラブ→学校: `input/arato_tamana_report.yaml` の所属／選手マッピング"
        "（金栗PROJECT→菊水、アスリーツ→玉陵、ATRCは選手別など）で校プールを再分配"
    )
    lines.append(
        "- **前年復帰**: 荒玉2025（学年1–2）・2024（学年1）の選手は陸上部SBが無くても校プール／直近実績に反映"
        f"（去年コース固定重み×{PRIOR_YEAR_COURSE_WEIGHT}、一昨年×{PRIOR_YEAR_MINUS_2_WEIGHT}）。"
        "同一選手の複数区間配置は禁止（不足区間は欠測）"
    )
    lines.append("- 校別シナリオ: [校別展開予想.md](校別展開予想.md)")
    lines.append("")
    lines.append("## 総合順位（実SBのみ・全区間そろったチーム）")
    lines.append("")
    header = "| 順位 | No. | チーム | 総合予想 | " + " | ".join(leg_headers) + " |"
    lines.append(header)
    lines.append("| --- | --- | --- | --- | " + " | ".join(["---"] * n_legs) + " |")
    for t in report["ranked"]:
        cells = [
            str(t["rank"]),
            str(t["no"]),
            t["team"],
            fmt_total(t["total"]),
        ]
        for det in t["legs"]:
            cells.append(fmt_leg_pred_cell(det, field_suffix=""))
        lines.append("| " + " | ".join(cells) + " |")
    if not report["ranked"]:
        lines.append("| （該当なし） |  |  |  | " + " | ".join([""] * n_legs) + " |")
    lines.append("")
    lines.append("## チーム別詳細")
    lines.append("")
    for t in report["teams"]:
        if t.get("rank"):
            rank_s = f"{t['rank']}位"
        else:
            rank_s = "順位対象外（実SB欠測区間あり）"
        total_s = fmt_total(t.get("total")) if t.get("total") is not None else "—"
        lines.append(f"### {t['no']}. {t['team']}（総合 {total_s} / {rank_s}）")
        lines.append("")
        lines.append(f"- オーダー根拠: `{t.get('source', '')}` — {t.get('order_notes', '')}")
        lines.append("")
        cols = ["区間", "km", "選手", "800m", "1500m", "3000m", "SB予想", "通過予想", "通過順", "区間順", "エビデンス"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for det in t["legs"]:
            cum_s = (
                fmt_time(det.get("pred_cum"), 1) if det.get("pred_cum") is not None else ""
            )
            pred_cell = fmt_time(det["pred"], 1) if det["pred"] is not None else "—"
            row = [
                f"{det['leg']}区",
                str(det["km"]),
                det["name"] or "",
                md_mark(det["marks"].get("800m")),
                md_mark(det["marks"].get("1500m")),
                md_mark(det["marks"].get("3000m")),
                pred_cell,
                cum_s,
                str(det["pred_cum_rank"]) if det.get("pred_cum_rank") is not None else "",
                str(det["pred_sec_rank"]) if det.get("pred_sec_rank") is not None else "",
                det["note"],
            ]
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    lines.append("## 注意")
    lines.append("")
    lines.append(
        "各選手の**エビデンス**列は、予想タイムに使った事実（トラックSBの種目・記録・日付、"
        "駅伝の大会名・実測・距離・比例値・重み、前年荒玉からの伸び率）を記載する。"
        "推測・印象だけの文言は入れない。"
    )
    lines.append(
        "トラックSBと駅伝は路面・気象・タスキ条件が異なります。"
        "他校オーダーは**公式未着の仮置き**であり、当日出走とは一致しません。"
        "欠測区間は埋めず順位対象外とします。公式スタートリスト到着後に再生成してください。"
    )
    lines.append("")
    return "\n".join(lines)


def coverage_rows(gender: str, report: dict[str, Any], as_of: str, freshness: int | None) -> list[dict]:
    rows = []
    for t in report["teams"]:
        for d in t["legs"]:
            marks = d["marks"] or {}
            rows.append(
                {
                    "gender": gender,
                    "team": t["team"],
                    "leg": d["leg"],
                    "km": d["km"],
                    "name": d["name"],
                    "pred_sec": "" if d["pred"] is None else round(d["pred"], 1),
                    "pred": fmt_time(d["pred"]),
                    "sb_800": mark_text(marks.get("800m")),
                    "sb_1500": mark_text(marks.get("1500m")),
                    "sb_3000": mark_text(marks.get("3000m")),
                    "note": d["note"],
                    "source": t.get("source", ""),
                    "as_of": as_of,
                    "freshness_days": freshness if freshness is not None else "",
                }
            )
    return rows


def write_coverage(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _leg_cell(name: str, *, provisional_mark: bool = False) -> str:
    n = str(name or "").strip()
    if not n:
        return "（欠）"
    compact = n.replace(" ", "")
    if provisional_mark:
        return f"※{compact}"
    return compact


def render_provisional_orders_md(
    women_orders: list[dict[str, Any]],
    men_orders: list[dict[str, Any]],
    *,
    as_of: str,
) -> str:
    """仮区間オーダー一覧（dual-write 用）。"""
    lines: list[str] = [
        "# 荒玉中体連駅伝 2026 仮区間オーダー",
        "",
        f"更新: {as_of}",
        "状態: **公式スタートリスト未着**のため仮置き。予想タイムは**実SB／直近駅伝のみ**（中央値補完なし）。",
        "生成: `python3 scripts/generate_aragyoku_ekiden_sb_preview.py`",
        "正本出力: [区間オーダー_SB予想.md](区間オーダー_SB予想.md)",
        "",
        "## 規則",
        "",
        "| 区分 | 扱い |",
        "| --- | --- |",
        "| 岱明女子 1–5 | **監督確定** |",
        "| 岱明男子 1–4 | **監督確定** |",
        "| 岱明男子 5–6 | ジュニア／SB次点で**仮置き** |",
        "| クラブ所属 | `input/arato_tamana_report.yaml` の所属／**選手別**学校マッピングで各校へ分配 |",
        "| **同一選手** | **複数区間に置かない**（異体字・OCR1文字差も同一扱い）。不足は空欄（欠測） |",
        "| 復帰候補 | 荒玉**2025（学年1–2）**・**2024（学年1）**＋**Bチーム実績**を校プール／固定オーダーに反映 |",
        "| 欠測区間 | 埋めない。そのチームは総合順位対象外 |",
        "",
        "## 女子（5区）",
        "",
        "| No | チーム | 1区 | 2区 | 3区 | 4区 | 5区 | 根拠 |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, row in enumerate(women_orders, start=1):
        legs = list(row.get("legs") or [])
        while len(legs) < 5:
            legs.append("")
        src = str(row.get("source") or "")
        note = str(row.get("notes") or "").split("。")[0]
        reason = "**確定**" if src == "confirmed" else (note or src)
        cells = [_leg_cell(legs[j]) for j in range(5)]
        lines.append(
            f"| {i} | {row['team']} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {cells[4]} | {reason} |"
        )
    lines += [
        "",
        "## 男子（6区）",
        "",
        "| No | チーム | 1 | 2 | 3 | 4 | 5 | 6 | 根拠 |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, row in enumerate(men_orders, start=1):
        legs = list(row.get("legs") or [])
        while len(legs) < 6:
            legs.append("")
        src = str(row.get("source") or "")
        note = str(row.get("notes") or "").split("。")[0]
        reason = (
            "1–4確定（5–6仮）"
            if "岱明" in str(row.get("team")) and "confirmed" in src
            else (note or src)
        )
        cells = []
        for j in range(6):
            mark = "岱明" in str(row.get("team")) and j >= 4 and bool(legs[j])
            cells.append(_leg_cell(legs[j], provisional_mark=mark))
        lines.append(
            f"| {i} | {row['team']} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {cells[4]} | {cells[5]} | {reason} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def parse_clock_to_sec(text: str | None) -> float | None:
    """'56:17' / '1:02:03' / '9:14.5' → 秒。解釈できない場合は None。"""
    if text is None:
        return None
    s = str(text).strip().replace("．", ".")
    if not s or s in {"—", "-", "DNF", "DNS"}:
        return None
    parts = s.split(":")
    try:
        if len(parts) == 2:
            mins = int(parts[0])
            sec = float(parts[1])
            return mins * 60.0 + sec
        if len(parts) == 3:
            hours = int(parts[0])
            mins = int(parts[1])
            sec = float(parts[2])
            return hours * 3600.0 + mins * 60.0 + sec
    except ValueError:
        return None
    return None


def fmt_signed_clock(delta_sec: float | None) -> str:
    """秒差を +M:SS / -M:SS 形式に。None は —。"""
    if delta_sec is None:
        return "—"
    if abs(delta_sec) <= 0.05:
        return "±0:00"
    sign = "+" if delta_sec > 0 else "-"
    total = int(round(abs(delta_sec)))
    mins, sec = divmod(total, 60)
    return f"{sign}{mins}:{sec:02d}"


def load_prior_year_team_standings(gender: str) -> list[dict[str, Any]]:
    """前年荒玉の総合順位・総合タイム一覧（正規化校名付き）。"""
    paths = list(PRIOR_YEAR_TRANSCRIPTS.get(gender) or [])
    path = None
    for p in paths:
        if p.exists() and "2025" in p.name:
            path = p
            break
    if path is None:
        for p in paths:
            if p.exists():
                path = p
                break
    if path is None:
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []
    for row in raw.get("teams") or []:
        if not isinstance(row, dict) or row.get("rank") is None:
            continue
        team_raw = str(row.get("team") or "").strip()
        school = normalize_prior_team_to_school(team_raw) or team_raw
        total_text = str(row.get("total") or "").strip()
        total_sec = parse_clock_to_sec(total_text)
        if total_sec is None:
            continue
        out.append(
            {
                "rank": int(row["rank"]),
                "team_raw": team_raw,
                "school": school,
                "total_sec": total_sec,
                "total_text": total_text,
                "year": int(raw.get("year") or 2025),
            }
        )
    out.sort(key=lambda r: r["rank"])
    return out


def build_yoy_rank_rows(
    report: dict[str, Any],
    prior: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """今年の総合順位予想と、昨年同順位・同校実績の差を行化する。"""
    prior_by_rank = {int(r["rank"]): r for r in prior}
    prior_by_school: dict[str, dict[str, Any]] = {}
    for r in prior:
        prior_by_school.setdefault(r["school"], r)
    rows: list[dict[str, Any]] = []
    for t in report.get("ranked") or []:
        rank = t.get("rank")
        total = t.get("total")
        if rank is None or total is None:
            continue
        same_rank = prior_by_rank.get(int(rank))
        same_school = prior_by_school.get(t["team"])
        rows.append(
            {
                "rank": int(rank),
                "team": t["team"],
                "pred_sec": float(total),
                "pred_text": fmt_total(total),
                "prior_same_rank": same_rank,
                "vs_same_rank_sec": (
                    float(total) - float(same_rank["total_sec"]) if same_rank else None
                ),
                "prior_same_school": same_school,
                "vs_same_school_sec": (
                    float(total) - float(same_school["total_sec"])
                    if same_school
                    else None
                ),
                "legs": t.get("legs") or [],
            }
        )
    return rows


def _scenario_tone(gender: str, team: str, rank: int) -> str:
    if gender == "女子" and "南関" in team:
        return "ジュニア時点でも地区先頭寄り。荒玉でも優勝候補の一角。"
    if gender == "男子" and "玉陵" in team:
        return "直近3000mトラックが厚く、SB予想では先頭。本番ロード耐性が焦点。"
    if gender == "男子" and "菊水" in team:
        return "昨年優勝校。今年も上位本命だが、玉陵の3000m層との差が論点。"
    if "岱明" in team:
        if gender == "男子":
            return "確定オーダー中心。中盤勝負で附・南関にどこまで食らいつけるか。"
        return "ジュニア下振れ後の立て直し。1区とアンカーの耐が順位を決める。"
    if rank == 1:
        return "地区優勝候補の本命想定。"
    if rank <= 3:
        return "上位争いの中核。区間の取り合いで順位が動く。"
    if rank <= 5:
        return "中位上位。エース区間の爆発とアンカーの粘りが鍵。"
    return "層・SBカバレッジ次第。公式オーダーで大きく変わり得る。"


def _scenario_one_liner(gender: str, row: dict[str, Any]) -> str:
    rank = row["rank"]
    team = row["team"]
    bits = [f"SB総合予想 {rank}位 {row['pred_text']}"]
    if row["prior_same_rank"]:
        pr = row["prior_same_rank"]
        bits.append(
            f"昨年{rank}位（{pr['team_raw']} {pr['total_text']}）との差 "
            f"{fmt_signed_clock(row['vs_same_rank_sec'])}"
            "（負=昨年同順位より速い）"
        )
    if row["prior_same_school"]:
        ps = row["prior_same_school"]
        bits.append(
            f"同校昨年{ps['rank']}位 {ps['total_text']} との差 "
            f"{fmt_signed_clock(row['vs_same_school_sec'])}"
        )
    else:
        bits.append("同校の昨年総合実績なし（新規上位 or 成績表未掲載）")
    tone = _scenario_tone(gender, team, rank)
    return " / ".join(bits) + f" → **今年の見立て**: {tone}"


def _yoy_table_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| 今年順位 | 校 | 今年予想 | 昨年同順位（校・タイム） | 同順位差 | 同校昨年 | 同校差 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    if not rows:
        lines.append("| （順位対象チームなし） |  |  |  |  |  |  |")
        return lines
    for r in rows:
        same = r["prior_same_rank"]
        same_s = (
            f"{same['rank']}位 {same['team_raw']} {same['total_text']}" if same else "—"
        )
        school = r["prior_same_school"]
        school_s = f"{school['rank']}位 {school['total_text']}" if school else "—"
        lines.append(
            f"| {r['rank']} | {r['team']} | {r['pred_text']} | {same_s} | "
            f"{fmt_signed_clock(r['vs_same_rank_sec'])} | {school_s} | "
            f"{fmt_signed_clock(r['vs_same_school_sec'])} |"
        )
    return lines


def _school_detail_lines(gender: str, rows: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for r in rows:
        lines.append(f"### {r['rank']}. {r['team']}")
        lines.append("")
        lines.append(_scenario_one_liner(gender, r))
        lines.append("")
        leg_bits = []
        for det in r["legs"]:
            name = det.get("name") or "—"
            pred = (
                fmt_time(det.get("pred"), 1) if det.get("pred") is not None else "—"
            )
            leg_bits.append(f"{det.get('leg')}区{name} {pred}")
        if leg_bits:
            lines.append("- 区間予想: " + " / ".join(leg_bits))
            lines.append("")
    return lines


def render_school_scenario_md(
    women: dict[str, Any],
    men: dict[str, Any],
    *,
    as_of: str,
) -> str:
    """校別展開予想.md（昨年同順位差＋今年予想）を生成する。"""
    prior_w = load_prior_year_team_standings("女子")
    prior_m = load_prior_year_team_standings("男子")
    rows_w = build_yoy_rank_rows(women, prior_w)
    rows_m = build_yoy_rank_rows(men, prior_m)
    if prior_m:
        prior_year = int(prior_m[0]["year"])
    elif prior_w:
        prior_year = int(prior_w[0]["year"])
    else:
        prior_year = 2025
    prior_m_by_rank = {int(x["rank"]): x for x in prior_m}
    prior_w_by_rank = {int(x["rank"]): x for x in prior_w}

    lines: list[str] = [
        "# 荒玉中体連駅伝 2026 校別展開予想",
        "",
        f"更新: {as_of}（SB区間予想＋{prior_year}年成績の自動生成）",
        f"開催: {EVENT_DATE}（予備日あり）",
        "根拠: [区間オーダー_SB予想.md](区間オーダー_SB予想.md) / "
        f"`input/idaten-corpus/aragyoku/transcripts/{prior_year}-*.json` / "
        "ジュニア結果・岱明確定オーダー",
        "距離: 男子 3.00 / 2.855 / 3.00 / 3.00 / 2.855 / 3.00 km、"
        "女子 3.00 / 1.855 / 2.00 / 2.00 / 3.00 km（2024年以降定義）",
        "",
        "**注意**: 他校オーダーは公式未着の仮置き。数値はトラックSB・直近駅伝・前年コースに基づく予想。"
        "「昨年同順位差」は今年N位の予想総合 − 昨年N位の実績総合"
        "（負＝昨年の同順位より速い＝レベルアップ）。",
        "",
        "---",
        "",
        f"## 昨年同順位とのレベル差（{prior_year} → 2026予想）",
        "",
        "### 男子",
        "",
    ]
    lines.extend(_yoy_table_lines(rows_m))
    lines.extend(["", "### 女子", ""])
    lines.extend(_yoy_table_lines(rows_w))

    lines.extend(
        [
            "",
            "---",
            "",
            "## 今年どうなるか（SB総合の見立て）",
            "",
            "### 男子",
            "",
        ]
    )
    if rows_m:
        top = "、".join(
            f"{r['rank']}位 {r['team']}（{r['pred_text']}）" for r in rows_m[:3]
        )
        lines.append(f"- 先頭帯: {top}")
        if len(rows_m) >= 2:
            gap = rows_m[1]["pred_sec"] - rows_m[0]["pred_sec"]
            gap_s = fmt_signed_clock(gap).lstrip("+")
            lines.append(
                f"- 1–2位差: {gap_s}（SB上）。本番はロード耐性・区間配置で前後し得る。"
            )
        if 1 in prior_m_by_rank:
            p1 = prior_m_by_rank[1]
            lines.append(
                f"- 昨年優勝（{p1['team_raw']} {p1['total_text']}）に対し、"
                f"今年1位予想は {fmt_signed_clock(rows_m[0]['vs_same_rank_sec'])}。"
            )
    else:
        lines.append("- 実SBが揃うチームが少ないため、総合順位は公式オーダー待ち。")

    lines.extend(["", "### 女子", ""])
    if rows_w:
        top = "、".join(
            f"{r['rank']}位 {r['team']}（{r['pred_text']}）" for r in rows_w[:3]
        )
        lines.append(f"- 先頭帯: {top}")
        if 1 in prior_w_by_rank:
            p1 = prior_w_by_rank[1]
            lines.append(
                f"- 昨年優勝（{p1['team_raw']} {p1['total_text']}）に対し、"
                f"今年1位予想は {fmt_signed_clock(rows_w[0]['vs_same_rank_sec'])}。"
            )
        lines.append(
            "- ジュニアでは南関が岱明より先行。荒玉距離では1・5区（各3km）のスタミナが順位を左右する。"
        )
    else:
        lines.append("- 実SBが揃うチームが少ないため、総合順位は公式オーダー待ち。")

    lines.extend(["", "---", "", "## 校別（男子）", ""])
    lines.extend(_school_detail_lines("男子", rows_m))
    lines.extend(["## 校別（女子）", ""])
    lines.extend(_school_detail_lines("女子", rows_w))
    lines.extend(
        [
            "---",
            "",
            "## 補足（ジュニア・確定オーダー）",
            "",
            "- 岱明女子確定: 1村上 / 2山﨑 / 3角田 / 4増岡 / 5高田",
            "- 岱明男子1–4確定: 1松野 / 2山本 / 3今村 / 4田上（5–6は仮置き）",
            "- ジュニア結果の詳細は地区ジュニアフォルダの抜粋・岱明結果を参照。",
            "- 数値の正本は [区間オーダー_SB予想.md](区間オーダー_SB予想.md) / "
            "[仮区間オーダー.md](仮区間オーダー.md)。",
            "",
            "## 更新履歴",
            "",
            "| 日付 | 内容 |",
            "| --- | --- |",
            f"| {as_of} | SB予想＋{prior_year}年同順位／同校差を自動生成 |",
            "| 2026-09-27 | ジュニア紙面ベースの第一版（以降は本スクリプトが更新） |",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="荒玉駅伝 SB区間予想（多校・全区間仮置き）")
    parser.add_argument("--as-of", default=DEFAULT_AS_OF, help="SB カットオフ日 YYYY-MM-DD")
    parser.add_argument(
        "--freshness-days",
        type=int,
        default=SB_FRESHNESS_DAYS,
        help="SB鮮度窓（日）。0で無効",
    )
    args = parser.parse_args()
    freshness = None if args.freshness_days <= 0 else args.freshness_days

    ensure_human_notes_files()

    women_sb, _ = nagomi.load_sb_index(
        as_of=args.as_of, gender="女子", freshness_days=freshness
    )
    men_sb, _ = nagomi.load_sb_index(
        as_of=args.as_of, gender="男子", freshness_days=freshness
    )
    women = build_report("女子", women_sb, as_of=args.as_of)
    men = build_report("男子", men_sb, as_of=args.as_of)
    women_orders = get_provisional_orders("女子", women_sb)
    men_orders = get_provisional_orders("男子", men_sb)
    provisional_md = render_provisional_orders_md(
        women_orders, men_orders, as_of=args.as_of
    )
    scenario_md = render_school_scenario_md(women, men, as_of=args.as_of)

    women_md = render_markdown(women, freshness=freshness)
    men_md = render_markdown(men, freshness=freshness)
    combined = (
        "# 荒玉中体連駅伝 2026年度SB・区間予想（多校・全区間仮置き）\n\n"
        f"as_of: {args.as_of} / event_date: {EVENT_DATE} / freshness_days: {freshness}\n\n"
        "女子・男子それぞれの総合順位・通過順・チーム詳細は下記。\n"
        "オーダーは公式未着のためジュニア／SB上位で全区間を仮置き（岱明女・男1–4のみ確定）。\n\n"
        "---\n\n"
        + women_md
        + "\n---\n\n"
        + men_md
    )
    rows = coverage_rows("女子", women, args.as_of, freshness) + coverage_rows(
        "男子", men, args.as_of, freshness
    )

    for out_dir in (MEET_DIR, CORPUS_MEET):
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / "区間オーダー_SB予想.md"
        md_path.write_text(combined, encoding="utf-8")
        (out_dir / "女子区間オーダー_SB予想.md").write_text(women_md, encoding="utf-8")
        (out_dir / "男子区間オーダー_SB予想.md").write_text(men_md, encoding="utf-8")
        write_coverage(out_dir / "区間オーダー_SB予想_coverage.csv", rows)
        write_coverage(
            out_dir / "女子区間オーダー_SB予想_coverage.csv",
            [r for r in rows if r["gender"] == "女子"],
        )
        write_coverage(
            out_dir / "男子区間オーダー_SB予想_coverage.csv",
            [r for r in rows if r["gender"] == "男子"],
        )
        (out_dir / "仮区間オーダー.md").write_text(provisional_md, encoding="utf-8")
        (out_dir / "校別展開予想.md").write_text(scenario_md, encoding="utf-8")
        print(f"wrote {md_path}")
        print(f"wrote {out_dir / '校別展開予想.md'}")
        if women["ranked_ref"]:
            top_w = women["ranked_ref"][0]
            print(f"  women top: {top_w['team']} {fmt_total(top_w['total_ref'])}")
        if men["ranked_ref"]:
            top_m = men["ranked_ref"][0]
            print(f"  men top: {top_m['team']} {fmt_total(top_m['total_ref'])}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
