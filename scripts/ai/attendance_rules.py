"""いだてん岱明がどの予定に出るか（負荷・疲労判定用）。"""

from __future__ import annotations

import yaml

from .config import RULES_PATH

# YAML が読めないときの既定: 練習会は負荷に数えない
_DEFAULT_PRACTICE_MEETS_AFFECT_LOAD = False


def practice_meets_affect_load(*, rules_path=None) -> bool:
    path = rules_path or RULES_PATH
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        return _DEFAULT_PRACTICE_MEETS_AFFECT_LOAD
    daiming = data.get("daiming") or {}
    return bool(daiming.get("practice_meets_affect_load", _DEFAULT_PRACTICE_MEETS_AFFECT_LOAD))


def is_practice_meet(title: str) -> bool:
    return "練習会" in title


def counts_as_load_meet(title: str, *, rules_path=None) -> bool:
    """True if yesterday/tomorrow this event should change practice load."""
    if not is_practice_meet(title):
        return False
    return practice_meets_affect_load(rules_path=rules_path)
