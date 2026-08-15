"""Practice event utilities: detection, tag normalization, absentees."""

from __future__ import annotations

import re

PRACTICE_TAGS = ["ランニング", "いだてん岱明練習"]

PRACTICE_TITLES = {
    "岱明朝練",
    "岱明夕練",
    "岱明朝練休み",
    "岱明夕練休み",
    "岱明練習休み",
    "岱明朝練と夕練",
}


def tags_list(ev: dict) -> list[str]:
    raw = ev.get("tags") or []
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    return list(raw)


def is_practice_event(ev: dict) -> bool:
    title = ev.get("title", "")
    tags = tags_list(ev)
    if "いだてん岱明練習" in tags:
        return True
    if title in {"岱明夕練", "岱明朝練"}:
        return True
    if title in PRACTICE_TITLES:
        return True
    if ("岱明" in title or "いだてん" in title) and "練習" in title:
        return True
    if "自分の練習" in tags:
        return True
    return False


def infer_session_tag(title: str) -> str | None:
    if "朝練" in title:
        return "session:morning"
    if "夕練" in title:
        return "session:evening"
    return None


def infer_practice_tag(ev: dict) -> str | None:
    tags = tags_list(ev)
    title = ev.get("title", "")
    if "自分の練習" in tags:
        return "practice:personal"
    if "いだてん岱明練習" in tags or title in PRACTICE_TITLES or (
        ("岱明" in title or "いだてん" in title) and "練習" in title
    ):
        return "practice:daiming"
    return None


def normalize_tags(ev: dict) -> list[str]:
    tags = tags_list(ev)
    seen = set(tags)
    for tag in (infer_practice_tag(ev), infer_session_tag(ev.get("title", ""))):
        if tag and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tags


def parse_absentees_line(line: str) -> list[str] | None:
    """Parse a 欠席者 line. None if the line is not an absentee list."""
    s = line.strip()
    if s == "欠席者なし":
        return []
    m = re.match(r"^欠席者\s+(.+)$", s)
    if not m:
        return None
    names_part = m.group(1).strip()
    if "。" in names_part or len(names_part) > 50:
        return None
    names = [n.strip() for n in re.split(r"[、,]", names_part) if n.strip()]
    return names if names else None


def format_absentees(absentees: list[str] | None) -> str | None:
    if absentees is None:
        return None
    if not absentees:
        return "欠席者なし"
    return "欠席者 " + "、".join(absentees)


def extract_absentees_from_text(text: str) -> list[str] | None:
    for line in text.splitlines():
        parsed = parse_absentees_line(line.strip())
        if parsed is not None:
            return parsed
    return None


def normalize_event_tags(ev: dict) -> bool:
    new_tags = normalize_tags(ev)
    old_tags = tags_list(ev)
    if new_tags != old_tags:
        ev["tags"] = new_tags
        return True
    return False
