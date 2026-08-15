"""Unified practice menu parser."""

from __future__ import annotations

import re
from typing import Any

import yaml

from practice_models import LAP_M, LegacyItem, ParseResult, empty_practice
from practice_renderer import HTML_COMMENT_RE
from practice_utils import extract_absentees_from_text, parse_absentees_line

# --- k/pace helpers (from convert_practice_pace) ---


def fmt_kpace(sec_per_km: float) -> str:
    s = int(round(sec_per_km))
    return f"k/{s // 60}:{s % 60:02d}"


def kpace(dist_m: float, sec: float) -> str:
    return fmt_kpace(sec / (dist_m / 1000.0))


def parse_kpace(s: str) -> str | None:
    m = re.search(r"k/(\d+)[:''](\d{1,2})", s)
    return f"k/{int(m.group(1))}:{int(m.group(2)):02d}" if m else None


def laps_dist(n: int) -> str:
    km = n * LAP_M / 1000
    return f"{km:.2f}km".rstrip("0").rstrip(".") + f" ({n}周)"


class LegacySession:
    def __init__(self) -> None:
        self.items: list[LegacyItem] = []
        self.skipped: list[str] = []

    def add(self, menu: str, distance: str, pace: str) -> None:
        key = (menu, distance, pace)
        if not any((i.menu, i.distance, i.pace) == key for i in self.items):
            self.items.append(LegacyItem(menu, distance, pace))


def convert_description(session: LegacySession, desc: str) -> None:
    """Legacy regex converter (migrated from convert_practice_pace.convert)."""
    d = desc.replace("''", "'")

    for m in re.finditer(r"（(\d+\.?\d*)km、\s*(k/\d+[:'']\d{1,2})", d):
        laps = re.search(r"(\d+)周", d)
        label = f"ジョグ {laps.group(1)}周" if laps else "ジョグ"
        session.add(label, f"{m.group(1)}km", parse_kpace(m.group(2)) or "")

    m = re.search(
        r"男子(\d+)周、女子(\d+)周\s+1周(\d+)[':](\d{2})〜(\d+)[':](\d{2})",
        d,
    )
    if m:
        lo = int(m.group(3)) * 60 + int(m.group(4))
        hi = int(m.group(5)) * 60 + int(m.group(6))
        sec = (lo + hi) / 2
        session.add("ジョグ 男子", laps_dist(int(m.group(1))), kpace(LAP_M, sec))
        session.add("ジョグ 女子", laps_dist(int(m.group(2))), kpace(LAP_M, sec))

    def one_lap_range(text: str) -> float | None:
        m = re.search(r"1周(\d+)[':](\d{2})〜(?:(\d+)[':])?(\d{2})", text)
        if not m:
            return None
        lo = int(m.group(1)) * 60 + int(m.group(2))
        hi_min = int(m.group(3)) if m.group(3) else int(m.group(1))
        hi = hi_min * 60 + int(m.group(4))
        return (lo + hi) / 2

    m = re.search(r"ジョグ\s*男子(\d+)周、女子(\d+)周", d)
    if m:
        sec = one_lap_range(d)
        if sec:
            session.add("ジョグ 男子", laps_dist(int(m.group(1))), kpace(LAP_M, sec))
            session.add("ジョグ 女子", laps_dist(int(m.group(2))), kpace(LAP_M, sec))

    m = re.search(
        r"男子(\d+)周、女子(\d+)周\s+1周男子(\d+)[':](\d{2})、女子(\d+)[':](\d{2})",
        d,
    )
    if m:
        session.add(
            "ジョグ 男子",
            laps_dist(int(m.group(1))),
            kpace(LAP_M, int(m.group(3)) * 60 + int(m.group(4))),
        )
        session.add(
            "ジョグ 女子",
            laps_dist(int(m.group(2))),
            kpace(LAP_M, int(m.group(5)) * 60 + int(m.group(6))),
        )

    # k/ lines already normalized
    for line in d.splitlines():
        line = line.strip()
        m = re.match(
            r"^(ジョグ|ロングジョグ|男子|女子|800m組|1500m组|1500m組|3000m組|B組|A組|600m|900m|300m|200m)?\s*"
            r"(.+?)\s+(k/\d+:\d{2}(?:〜k/\d+:\d{2})?)$",
            line,
        )
        if m and "本目" not in line:
            menu = (m.group(1) or "").strip() or m.group(2).split()[0]
            dist_part = m.group(2).strip()
            pace_part = m.group(3).strip()
            session.add(menu, dist_part, pace_part)

    for m in re.finditer(
        r"(男子900m|女子600m|900m|600m|300m)\s*(\d+)?本目\s+(\d+m)\s+(k/\d+:\d{2})",
        d,
    ):
        menu = m.group(1) + (f" {m.group(2)}本目" if m.group(2) else "")
        session.add(menu.strip(), m.group(3), m.group(4))

    for m in re.finditer(r"(800m組|1500m組|3000m組)\s+(\S+)\s+(\S+\s+k/[\d:]+\s*/\s*\S+\s+k/[\d:]+)", d):
        session.add(m.group(1), m.group(2), m.group(3).split(" ", 1)[-1])

    paces = [f"k/{int(a)}:{int(b):02d}" for a, b in re.findall(r"k/(\d+)[:''](\d{1,2})", d)]
    if "800m組 600m+300m" in d and len(paces) >= 2:
        session.add("800m組", "600m+300m", f"600m {paces[1]} / 300m {paces[0]}")
    if "1500m組 900m+600m" in d and len(paces) >= 2:
        session.add("1500m組", "900m+600m", f"900m {paces[1]} / 600m {paces[0]}")
    if "1500m組 600m+300m" in d and len(paces) >= 2:
        session.add("1500m組", "600m+300m", f"600m {paces[1]} / 300m {paces[0]}")

    m = re.search(r"560m\s*2[:']40.*?男子(\d+)周([\d.]+)km・女子(\d+)周([\d.]+)km[、,]?\s*(k/\d+[:'']\d{1,2})", d)
    if m:
        p = parse_kpace(m.group(5)) or ""
        session.add("ジョグ 男子", f"{m.group(2)}km ({m.group(1)}周)", p)
        session.add("ジョグ 女子", f"{m.group(4)}km ({m.group(3)}周)", p)

    m = re.search(r"900m1本（300m(\d+)・(\d+)・(\d+)ペース組", d)
    if m:
        for sec in map(int, m.groups()):
            session.add(f"900m（300m{sec}秒組）", "900m", kpace(300, sec))

    if "600m2本（1500mRP" in d or "600m×2（1500mRP" in d:
        session.skipped.append("600m×2（1500mRP）— 個人RPのため未換算")
    if "1500mペース+10秒" in d:
        session.skipped.append("1500mRP+10秒/km — 個人RPのため未換算")
    for kw in ("200m2本", "100m流し", "流し2本", "流し4本", "500m1本", "坂道走", "2.5km×2", "2km×2"):
        if kw in d:
            session.skipped.append(f"{kw} — ペース未記載")


NOTE_LINE_RE = re.compile(
    r"^(動きづくり|流し|スピード練習|欠席者|間は|※|各自アップ|各自ジョグ)",
)


def extract_note_lines(desc: str) -> list[str]:
    notes: list[str] = []
    for line in desc.splitlines():
        s = line.strip()
        if not s or s.startswith("<!--"):
            continue
        if NOTE_LINE_RE.match(s) or ("。" in s and len(s) >= 20):
            notes.append(s)
    return notes


def _practice_dict(
    *,
    warmup: str | None = None,
    notes: str | None = None,
    absentees: list[str] | None = None,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    practice: dict[str, Any] = {"items": items}
    if warmup:
        practice["warmup"] = warmup
    if notes:
        practice["notes"] = notes
    if absentees is not None:
        practice["absentees"] = absentees
    return practice


def parse_practice_field(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not raw or not isinstance(raw, dict):
        return None
    items = raw.get("items")
    if not items:
        return None
    absentees = raw.get("absentees")
    if absentees is not None:
        absentees = list(absentees)
    return _practice_dict(
        warmup=raw.get("warmup"),
        notes=raw.get("notes"),
        absentees=absentees,
        items=list(items),
    )


def parse_html_comment(desc: str) -> dict[str, Any] | None:
    m = HTML_COMMENT_RE.search(desc)
    if not m:
        return None
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict) or not data.get("items"):
        return None
    absentees = data.get("absentees")
    if absentees is not None:
        absentees = list(absentees)
    return _practice_dict(
        warmup=data.get("warmup"),
        notes=data.get("notes"),
        absentees=absentees,
        items=list(data["items"]),
    )


def _parse_distance_m(dist: str) -> int | None:
    m = re.search(r"(\d+)m", dist)
    if m:
        return int(m.group(1))
    m = re.search(r"([\d.]+)km", dist)
    if m:
        return int(float(m.group(1)) * 1000)
    m = re.search(r"(\d+)周", dist)
    if m:
        return int(m.group(1)) * LAP_M
    return None


def _parse_laps(dist: str) -> int | None:
    m = re.search(r"(\d+)周", dist)
    return int(m.group(1)) if m else None


def legacy_item_to_practice(item: LegacyItem) -> dict[str, Any]:
    menu = item.menu
    dist = item.distance
    pace = item.pace or None
    group = None
    if menu.startswith("ジョグ 男子") or menu == "男子":
        group = "男子"
    elif menu.startswith("ジョグ 女子") or menu == "女子":
        group = "女子"
    elif menu.startswith("B組"):
        group = "B組"
    elif menu.startswith("A組"):
        group = "A組"

    if "ジョグ" in menu or menu.startswith("ロングジョグ"):
        entry: dict[str, Any] = {"type": "jog", "group": group}
        laps = _parse_laps(dist)
        if laps:
            entry["laps"] = laps
        km = re.search(r"([\d.]+)km", dist)
        if km:
            entry["distance_km"] = float(km.group(1))
        if pace and "〜" in pace:
            parts = re.findall(r"k/\d+:\d{2}", pace)
            if len(parts) == 2:
                entry["pace_min"], entry["pace_max"] = parts
        elif pace:
            entry["pace"] = parse_kpace(pace) or pace
        return entry

    if "+" in dist or "/" in item.pace:
        segs = []
        for part in re.split(r"\s*\+\s*|\s*/\s*", dist):
            dm = _parse_distance_m(part)
            if dm:
                segs.append({"distance_m": dm})
        if segs:
            return {"type": "set", "group": group, "segments": segs, "label": f"{menu} {dist} {pace}".strip()}

    dm = _parse_distance_m(dist)
    reps_m = re.search(r"×(\d+)", dist)
    entry = {"type": "interval", "group": group, "label": menu}
    if dm:
        entry["distance_m"] = dm
    if reps_m:
        entry["reps"] = int(reps_m.group(1))
    if pace:
        entry["pace"] = parse_kpace(pace.split()[0]) if " " in pace else (parse_kpace(pace) or pace)
    return entry


def regex_practice_items(desc: str) -> list[dict[str, Any]]:
    """Extract structured items from common Japanese menu patterns."""
    items: list[dict[str, Any]] = []
    d = desc.replace("''", "'")

    for m in re.finditer(
        r"(300m|600m|900m|200m|800m|1000m|500m|2100m|1200m|2000m)×(\d+(?:〜\d+)?)"
        r"（([^）]+)）",
        d,
    ):
        dist = int(re.search(r"(\d+)", m.group(1)).group(1))
        intensity = None
        rest_sec = None
        meta = m.group(3)
        for label in ("1500mRP", "3000mRP", "RP", "GZ"):
            if label in meta:
                intensity = label
        rm = re.search(r"レスト(\d+)分", meta)
        if rm:
            rest_sec = int(rm.group(1)) * 60
        rm = re.search(r"[rR=](\d+)分", meta)
        if rm:
            rest_sec = int(rm.group(1)) * 60
        items.append(
            {
                "type": "interval",
                "distance_m": dist,
                "reps": m.group(2),
                "intensity": intensity,
                "rest_sec": rest_sec,
            }
        )

    for m in re.finditer(r"ジョグ\s*男子\s*([\d.]+)〜([\d.]+)km\s*(k/[\d:]+)〜(k/[\d:]+)", d):
        items.append(
            {
                "type": "jog",
                "group": "男子",
                "distance_km_min": float(m.group(1)),
                "distance_km_max": float(m.group(2)),
                "pace_min": parse_kpace(m.group(3)),
                "pace_max": parse_kpace(m.group(4)),
            }
        )

    for m in re.finditer(r"ジョグ\s*女子\s*([\d.]+)〜([\d.]+)km\s*(k/[\d:]+)〜(k/[\d:]+)", d):
        items.append(
            {
                "type": "jog",
                "group": "女子",
                "distance_km_min": float(m.group(1)),
                "distance_km_max": float(m.group(2)),
                "pace_min": parse_kpace(m.group(3)),
                "pace_max": parse_kpace(m.group(4)),
            }
        )

    if re.search(r"男子\s*2100m\+900m", d):
        items.append({"type": "set", "group": "男子", "segments": [{"distance_m": 2100}, {"distance_m": 900}]})
    if re.search(r"女子\s*1200m\+900m", d):
        items.append({"type": "set", "group": "女子", "segments": [{"distance_m": 1200}, {"distance_m": 900}]})
    if re.search(r"男子\s*2000m\+1000m", d):
        items.append({"type": "set", "group": "男子", "segments": [{"distance_m": 2000}, {"distance_m": 1000}]})
    if re.search(r"女子\s*1000m×2", d):
        items.append({"type": "interval", "group": "女子", "distance_m": 1000, "reps": 2})

    return items


def description_to_practice(desc: str) -> ParseResult:
    notes = extract_note_lines(desc)
    absentees = extract_absentees_from_text(desc)
    filtered_notes: list[str] = []
    for n in notes:
        if parse_absentees_line(n) is not None:
            continue
        filtered_notes.append(n)
    legacy = LegacySession()
    convert_description(legacy, desc)
    regex_items = regex_practice_items(desc)
    practice_items = [legacy_item_to_practice(i) for i in legacy.items]
    if regex_items:
        practice_items.extend(regex_items)

    warmup = None
    for n in filtered_notes:
        if n in {"動きづくり", "流し", "スピード練習"}:
            warmup = n
            break

    confidence = "none"
    if practice_items and legacy.items:
        confidence = "full" if not legacy.skipped else "partial"
    elif practice_items:
        confidence = "partial" if legacy.skipped else "full"
    elif legacy.skipped:
        confidence = "partial"

    practice = _practice_dict(
        warmup=warmup,
        absentees=absentees,
        items=practice_items,
    )

    return ParseResult(
        practice=practice,
        legacy_items=legacy.items,
        skipped=legacy.skipped,
        source="description",
        confidence=confidence,
        note_lines=[n for n in filtered_notes if n != warmup],
    )


def parse_event(ev: dict) -> ParseResult:
    if ev.get("practice"):
        pf = parse_practice_field(ev["practice"])
        if pf:
            if pf.get("absentees") is None:
                extracted = extract_absentees_from_text(ev.get("description") or "")
                if extracted is not None:
                    pf["absentees"] = extracted
            note_lines = extract_note_lines(ev.get("description") or "")
            note_lines = [n for n in note_lines if parse_absentees_line(n) is None]
            return ParseResult(
                practice=pf,
                source="practice_field",
                confidence="full",
                note_lines=note_lines,
            )

    desc = (ev.get("description") or "").strip()
    if desc:
        hc = parse_html_comment(desc)
        if hc:
            return ParseResult(
                practice=hc,
                source="html_comment",
                confidence="full",
                note_lines=extract_note_lines(HTML_COMMENT_RE.sub("", desc)),
            )
        if len(desc) <= 8000:
            return description_to_practice(desc)

    return ParseResult(practice=empty_practice(), source="none", confidence="none")
