"""Render practice dict to human-readable description."""

from __future__ import annotations

import json
import re
from typing import Any

from practice_models import LAP_M, LegacyItem

HTML_COMMENT_RE = re.compile(
    r"<!--\s*practice-menu:v1\s*\n([\s\S]*?)\n\s*-->",
    re.MULTILINE,
)


def fmt_km(km: float) -> str:
    s = f"{km:.2f}km".rstrip("0").rstrip(".")
    if not s.endswith("km"):
        s += "km"
    return s


def laps_dist(n: int) -> str:
    km = n * LAP_M / 1000
    return fmt_km(km) + f" ({n}周)"


def render_item_line(item: dict[str, Any]) -> str:
    itype = item.get("type", "other")
    group = item.get("group")
    label = item.get("label")
    prefix = label or (f"{group} " if group else "")

    if itype == "jog":
        dist = ""
        if item.get("laps"):
            dist = laps_dist(int(item["laps"]))
        elif item.get("distance_km"):
            dist = fmt_km(float(item["distance_km"]))
        elif item.get("distance_km_min") and item.get("distance_km_max"):
            dist = f"{item['distance_km_min']}〜{item['distance_km_max']}km"
        elif item.get("distance_m"):
            dist = f"{int(item['distance_m'])}m"
        pace = item.get("pace") or ""
        if item.get("pace_min") and item.get("pace_max"):
            pace = f"{item['pace_min']}〜{item['pace_max']}"
        return f"ジョグ {prefix}{dist} {pace}".strip()

    if itype == "interval":
        dist_m = item.get("distance_m")
        reps = item.get("reps", 1)
        rep_s = f"×{reps}" if reps and reps != 1 else ""
        dist_s = f"{int(dist_m)}m" if dist_m else ""
        intensity = item.get("intensity")
        pace = item.get("pace") or ""
        rest = ""
        if item.get("rest_sec"):
            rest = f"、レスト{item['rest_sec'] // 60}分" if item["rest_sec"] >= 60 else f"、レスト{item['rest_sec']}秒"
        elif item.get("rest"):
            rest = f"、{item['rest']}"
        inten = f"（{intensity}）" if intensity else ""
        if isinstance(reps, str) and "-" in str(reps):
            return f"{dist_s}{rep_s}{inten}{rest}".strip()
        if pace and dist_s:
            n = item.get("rep_index")
            if n:
                return f"{dist_s} {n}本目 {dist_s} {pace}"
            return f"{prefix}{dist_s}{rep_s} {dist_s} {pace}".strip()
        return f"{prefix}{dist_s}{rep_s}{inten}{rest}".strip()

    if itype == "set" and item.get("segments"):
        parts = []
        for seg in item["segments"]:
            d = seg.get("distance_m")
            p = seg.get("pace") or ""
            parts.append(f"{int(d)}m {p}".strip() if d else p)
        joined = " / ".join(parts)
        return f"{prefix}{joined}".strip()

    if label:
        return label
    return json.dumps(item, ensure_ascii=False)


def render_legacy_item(item: LegacyItem) -> str:
    return f"{item.menu} {item.distance} {item.pace}".strip()


def strip_html_comment(description: str) -> str:
    return HTML_COMMENT_RE.sub("", description).strip()


def embed_html_comment(practice: dict[str, Any], description: str) -> str:
    body = description.strip()
    payload = {"warmup": practice.get("warmup"), "items": practice.get("items") or []}
    if practice.get("notes"):
        payload["notes"] = practice["notes"]
    comment_lines = ["<!-- practice-menu:v1"]
    import yaml as _yaml

    block = _yaml.dump(payload, allow_unicode=True, default_flow_style=False, sort_keys=False).strip()
    comment_lines.append(block)
    comment_lines.append("-->")
    comment = "\n".join(comment_lines)
    if body:
        return f"{comment}\n\n{body}"
    return comment


def render_description(
    practice: dict[str, Any],
    *,
    note_lines: list[str] | None = None,
    legacy_items: list[LegacyItem] | None = None,
    embed_comment: bool = False,
) -> str:
    lines: list[str] = []
    warmup = practice.get("warmup")
    if warmup:
        lines.append(warmup)
    if note_lines:
        if lines:
            lines.append("")
        lines.extend(note_lines)
    items = practice.get("items") or []
    rendered_items: list[str] = []
    if items:
        for item in items:
            rendered_items.append(render_item_line(item))
    elif legacy_items:
        rendered_items = [render_legacy_item(i) for i in legacy_items]
    if rendered_items:
        if lines:
            lines.append("")
        lines.extend(rendered_items)
    notes = practice.get("notes")
    if notes and notes not in lines:
        if lines:
            lines.append("")
        lines.append(notes)
    body = "\n".join(lines).strip()
    if embed_comment and items:
        return embed_html_comment(practice, body)
    return body
