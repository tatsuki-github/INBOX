"""大会翌日の休練・自主練E上限（いだてん岱明）。"""

from __future__ import annotations

import yaml

from .config import RULES_PATH
from .pre_race_stimulus import RACE_NEGATIVE, is_championship_race

_DEFAULT_ENABLED = True
_DEFAULT_TEAM_PRACTICE = "rest"
_DEFAULT_SELF_PRACTICE_MAX = "E"

SKIP_OVERRIDE_TOKENS = ("例外グループ",)


def load_post_race_config(*, rules_path=None) -> dict:
    path = rules_path or RULES_PATH
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        data = {}
    daiming = data.get("daiming") or {}
    post = daiming.get("post_race") or {}
    return {
        "enabled": bool(post.get("enabled", _DEFAULT_ENABLED)),
        "team_practice": str(post.get("team_practice", _DEFAULT_TEAM_PRACTICE)),
        "self_practice_max": str(post.get("self_practice_max", _DEFAULT_SELF_PRACTICE_MAX)),
    }


def is_daiming_race_event(title: str, description: str = "") -> bool:
    """出場負荷を伴う大会・記録会・駅伝（練習会等は除外）。"""
    if any(token in title for token in RACE_NEGATIVE):
        return False
    if is_championship_race(title, description):
        return True
    if "駅伝" in title:
        return True
    if "ナイター" in title:
        return True
    return False


def should_apply_post_race_rest(
    *,
    prev_race: bool,
    query: str = "",
    rules_path=None,
) -> bool:
    if not prev_race:
        return False
    cfg = load_post_race_config(rules_path=rules_path)
    if not cfg["enabled"]:
        return False
    if any(token in query for token in SKIP_OVERRIDE_TOKENS):
        return False
    return True


def post_race_notes(*, prev_race_title: str | None = None, rules_path=None) -> str:
    cfg = load_post_race_config(rules_path=rules_path)
    race = prev_race_title or "大会"
    lines = [
        f"前日（{race}）のため、いだてん岱明の練習は基本休み。",
        f"自主練する場合も{cfg['self_practice_max']}（会話しながら）まで。ポイント・閾値・RPは禁止。",
    ]
    return "".join(lines)


def build_post_race_rest_practice(*, prev_race_title: str | None = None, rules_path=None) -> dict:
    return {
        "warmup": None,
        "notes": post_race_notes(prev_race_title=prev_race_title, rules_path=rules_path),
        "items": [],
    }
