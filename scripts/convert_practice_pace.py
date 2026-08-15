#!/usr/bin/env python3
"""岱明練習メニューを k/M:SS 表記に変換して一覧出力・YAML反映する。

- トラック1周 = 560m
- 距離と時間の両方が判明する項目のみ変換
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

LAP_M = 560
ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "input"
OUTPUT_PATH = ROOT / "out" / "daiming-practice-menus-kpace.md"
PRACTICE_YEARS = [2020, 2022, 2023, 2024, 2025, 2026, 2027]


@dataclass
class Item:
    menu: str
    distance: str
    pace: str


@dataclass
class Session:
    date: str
    title: str
    year: int
    items: list[Item] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


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


def lap_sec(text: str) -> float | None:
    t = text.strip().replace("''", ":")
    m = re.fullmatch(r"(\d+):(\d{1,2})", t)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def add(session: Session, menu: str, distance: str, pace: str) -> None:
    key = (menu, distance, pace)
    if not any((i.menu, i.distance, i.pace) == key for i in session.items):
        session.items.append(Item(menu, distance, pace))


def convert(session: Session, desc: str) -> None:
    d = desc.replace("''", "'")

    # --- 計測済みジョグ（総距離 + k/） ---
    for m in re.finditer(r"（(\d+\.?\d*)km、\s*(k/\d+[:'']\d{1,2})", d):
        laps = re.search(r"(\d+)周", d)
        label = f"ジョグ {laps.group(1)}周" if laps else "ジョグ"
        add(session, label, f"{m.group(1)}km", parse_kpace(m.group(2)) or "")

    # --- 周数 + 1周タイム ---
    m = re.search(
        r"男子(\d+)周、女子(\d+)周\s+1周(\d+)[':](\d{2})〜(\d+)[':](\d{2})",
        d,
    )
    if m:
        lo = int(m.group(3)) * 60 + int(m.group(4))
        hi = int(m.group(5)) * 60 + int(m.group(6))
        sec = (lo + hi) / 2
        add(session, "ジョグ 男子", laps_dist(int(m.group(1))), kpace(LAP_M, sec))
        add(session, "ジョグ 女子", laps_dist(int(m.group(2))), kpace(LAP_M, sec))

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
            add(session, "ジョグ 男子", laps_dist(int(m.group(1))), kpace(LAP_M, sec))
            add(session, "ジョグ 女子", laps_dist(int(m.group(2))), kpace(LAP_M, sec))

    m = re.search(
        r"男子(\d+)周、女子(\d+)周\s+1周男子(\d+)[':](\d{2})、女子(\d+)[':](\d{2})",
        d,
    )
    if m:
        add(
            session,
            "ジョグ 男子",
            laps_dist(int(m.group(1))),
            kpace(LAP_M, int(m.group(3)) * 60 + int(m.group(4))),
        )
        add(
            session,
            "ジョグ 女子",
            laps_dist(int(m.group(2))),
            kpace(LAP_M, int(m.group(5)) * 60 + int(m.group(6))),
        )

    m = re.search(r"男子5kmを1周(\d+)[':](\d{2})、女子4kmを1周(\d+)[':](\d{2})", d)
    if m:
        add(session, "ジョグ 男子（クロカン）", "5km", kpace(LAP_M, int(m.group(1)) * 60 + int(m.group(2))))
        add(session, "ジョグ 女子（クロカン）", "4km", kpace(LAP_M, int(m.group(3)) * 60 + int(m.group(4))))

    # --- 300m 記録（秒のみの列） ---
    d300 = re.sub(
        r"(\d):(\d{2})-(\d{2})-(\d{2})-(\d{2})",
        lambda m: f"{int(m.group(1)) * 60 + int(m.group(2))}-{m.group(3)}-{m.group(4)}-{m.group(5)}",
        d,
    )
    m = re.search(r"300m[\s\S]*?(?<![\d:])(\d{2,3})-(\d{2})-(\d{2})-(\d{2})", d300)
    if m:
        times = [int(x) for x in m.groups()]
        if all(40 <= t <= 120 for t in times):
            for i, t in enumerate(times, 1):
                add(session, f"300m {i}本目", "300m", kpace(300, t))

    # --- ラップ列のみ（平均ラップ→k/） ---
    if not re.search(r"k/\d", d) and "300m 男子" not in d:
        laps_n = re.search(r"(\d+)周", d)
        splits = re.findall(r"(?<!\d)(\d+)[:'](\d{2})(?!\d)", d)
        if laps_n and splits and len(splits) >= 3:
            avg = sum(int(a) * 60 + int(b) for a, b in splits) / len(splits)
            add(session, f"ジョグ {laps_n.group(1)}周", laps_dist(int(laps_n.group(1))), kpace(LAP_M, avg))

    # --- セット練 + k/リスト ---
    paces = [f"k/{int(a)}:{int(b):02d}" for a, b in re.findall(r"k/(\d+)[:''](\d{1,2})", d)]
    if "800m組 600m+300m" in d and len(paces) >= 2:
        add(session, "800m組", "600m+300m", f"600m {paces[1]} / 300m {paces[0]}")
    if "1500m組 900m+600m" in d and len(paces) >= 2:
        add(session, "1500m組", "900m+600m", f"900m {paces[1]} / 600m {paces[0]}")
    if "1500m組 600m+300m" in d and len(paces) >= 2:
        add(session, "1500m組", "600m+300m", f"600m {paces[1]} / 300m {paces[0]}")
    if "800m組 300m+300m" in d and paces:
        add(session, "800m組", "300m+300m", paces[0])
    if "3000m 900m+300m" in d and len(paces) >= 3:
        add(session, "3000m組", "900m+300m", f"900m {paces[2]} / 300m {paces[0]}")

    # --- 300m秒数 → 600m k/ ---
    m = re.search(r"1周300m(\d+)秒と(\d+)秒組", d)
    if m:
        for s in map(int, m.groups()):
            add(session, f"600m（300m{s}秒/300m組）", "600m", kpace(300, s))
    m = re.search(r"600m2本（300m(\d+)秒、(\d+)秒、(\d+)秒、(\d+)秒の4グループ）", d)
    if m:
        for s in map(int, m.groups()):
            add(session, f"600m×2（{s}秒/300m組）", "600m×2", kpace(300, s))
    m = re.search(r"600m1本\s*(\d+)組、(\d+)組、(\d+)組", d)
    if m:
        for s in map(int, m.groups()):
            add(session, f"600m×1（{s}秒/300m組）", "600m", kpace(300, s))
    m = re.search(r"600m\+300m（(\d+)秒と(\d+)組）", d)
    if m:
        s1, s2 = int(m.group(1)), int(m.group(2))
        add(session, "600m+300m", "900m", f"600m {kpace(300, s1)} / 300m {kpace(300, s2)}")

    # --- 300m 記録 ---
    if "300m1本" in d:
        m = re.search(r"(\d+)秒〜(\d+)秒", d)
        if m:
            add(session, "300m×1", "300m", f"{kpace(300, int(m.group(1)))}〜{kpace(300, int(m.group(2)))}")

    if "300m5本" in d:
        for n, t in re.findall(r"(\d+)本目:\s*(\d+\.?\d*)", d):
            add(session, f"300m {n}本目", "300m", kpace(300, float(t)))

    # --- 900m/600m x3 ---
    if "男子900m、女子600mを3本" in d:
        rep = [(1, 72), (2, 69), (3, 66)]
        if "1本目は300m72" in d:
            for n, t in rep:
                add(session, f"男子900m {n}本目", "900m", kpace(300, t))
                add(session, f"女子600m {n}本目", "600m", kpace(300, t))

    # --- 200m ---
    m = re.search(r"200m5本[\s\S]*?男子(\d+)〜(\d+)、女子(\d+)〜(\d+)", d)
    if m:
        add(session, "200m×5 男子", "200m×5", f"{kpace(200, int(m.group(1)))}〜{kpace(200, int(m.group(2)))}")
        add(session, "200m×5 女子", "200m×5", f"{kpace(200, int(m.group(3)))}〜{kpace(200, int(m.group(4)))}")

    # --- 1000+500 ---
    m = re.search(r"男子1000m \+500m（(\d+):(\d+)-(\d+):(\d+)）", d)
    if m:
        add(session, "男子", "1000m+500m",
            f"1000m {kpace(1000, int(m.group(1))*60+int(m.group(2)))} / 500m {kpace(500, int(m.group(3))*60+int(m.group(4)))}")
    m = re.search(r"女子500m \+500m（(\d+):(\d+)-(\d+):(\d+)）", d)
    if m:
        add(session, "女子", "500m+500m",
            f"1本目 {kpace(500, int(m.group(1))*60+int(m.group(2)))} / 2本目 {kpace(500, int(m.group(3))*60+int(m.group(4)))}")

    # --- 2100+900 ---
    if "2100m + 900m" in d:
        mb = re.search(r"B\s*\d+:\d+-\d+:\d+\s*1周(\d+)秒", d)
        ma = re.search(r"A\s*\d+:\d+-\d+:\d+\s*1周(\d+)秒.*?(\d+)秒", d)
        if mb:
            add(session, "B組 2100m", "2100m", kpace(300, int(mb.group(1))))
            add(session, "B組 900m", "900m", kpace(300, 69))
        ma2 = re.search(r"A\s*\d+:\d+-\d+:\d+\s*1周(\d+)秒ペースと(\d+)秒", d)
        if ma2:
            add(session, "A組 2100m", "2100m", kpace(300, int(ma2.group(1))))
            add(session, "A組 900m", "900m", kpace(300, int(ma2.group(2))))

    # --- 900m 300m splits ---
    for n, block in re.findall(r"(\d+)本目\s+([\d.\-]+)", d):
        if "900m" in d or "900m4本" in d:
            for t in block.split("-"):
                add(session, f"900m {n}本目（300m通過）", "300m", kpace(300, float(t)))

    # --- 1680+1120 ---
    m = re.search(r"1周(\d+)[':](\d{2})秒組と(\d+)[':](\d{2})秒組", d)
    if "1680m" in d and m:
        t1 = int(m.group(1)) * 60 + int(m.group(2))
        t2 = int(m.group(3)) * 60 + int(m.group(4))
        add(session, "男子 1680m+1120m", "2800m", f"2:10組 {kpace(LAP_M, t1)} / 1:55組 {kpace(LAP_M, t2)}")
        add(session, "女子 1120m+560m", "1680m", f"2:10組 {kpace(LAP_M, t1)} / 1:55組 {kpace(LAP_M, t2)}")

    # --- 2026-08-14 ---
    m = re.search(r"560m\s*2[:']40.*?男子(\d+)周([\d.]+)km・女子(\d+)周([\d.]+)km[、,]?\s*(k/\d+[:'']\d{1,2})", d)
    if m:
        p = parse_kpace(m.group(5)) or ""
        add(session, "ジョグ 男子", f"{m.group(2)}km ({m.group(1)}周)", p)
        add(session, "ジョグ 女子", f"{m.group(4)}km ({m.group(3)}周)", p)
    m = re.search(r"900m1本（300m(\d+)・(\d+)・(\d+)ペース組", d)
    if m:
        for sec in map(int, m.groups()):
            add(session, f"900m（300m{sec}秒組）", "900m", kpace(300, sec))

    # --- ロングジョグ ---
    m = re.search(
        r"ロングジョグ女子(\d+)周([\d.]+)km、男子(\d+)周([\d.]+)km（[^、,]+[、,]\s*(k/\d+[:'']\d{1,2})）",
        d,
    )
    if m:
        p = parse_kpace(m.group(5)) or ""
        add(session, "ロングジョグ 女子", f"{m.group(2)}km ({m.group(1)}周)", p)
        add(session, "ロングジョグ 男子", f"{m.group(4)}km ({m.group(3)}周)", p)

    # --- 校内駅伝 ---
    m = re.search(r"校内駅伝コース3周[\s\S]*?（(\d+\.?\d*)km、\s*(k/\d+[:'']\d{1,2})）", d)
    if m and not any(i.menu.startswith("ジョグ") for i in session.items):
        add(session, "校内駅伝コース ジョグ", f"{m.group(1)}km (3周)", parse_kpace(m.group(2)) or "")

    # --- 2025-09-15 ---
    if "1周1:50" in d:
        add(session, "男子 追加2周（設定）", laps_dist(2), kpace(LAP_M, 110))
        add(session, "男子 追加2周（実際）", laps_dist(2), kpace(LAP_M, 105))
    if "1周2:10" in d and "実際は2:00" in d:
        add(session, "女子 追加2周（設定）", laps_dist(2), kpace(LAP_M, 130))
        add(session, "女子 追加2周（実際）", laps_dist(2), kpace(LAP_M, 120))

    # --- skipped notes ---
    if "600m2本（1500mRP" in d:
        session.skipped.append("600m×2（1500mRP）— 個人RPのため未換算")
    if "1500mペース+10秒" in d:
        session.skipped.append("1500mRP+10秒/km — 個人RPのため未換算")
    for kw in ("200m2本", "100m流し", "流し2本", "流し4本", "500m1本", "坂道走", "2.5km×2", "2km×2"):
        if kw in d:
            session.skipped.append(f"{kw} — ペース未記載")


APPLY_YEARS = [2025, 2026]

PACE_DATA_RE = re.compile(
    r"(\d+[:']\d{2}(?:-\d+[:']\d{2})+)|"
    r"(\d+\.?\d*km)|"
    r"(300m|600m|900m|200m|800m|1500m|3000m|500m|1000m|2100m|1120m|1680m)|"
    r"(800m組|1500m組|3000m組)|"
    r"(ペース)|"
    r"(1周)|"
    r"(ジョグ)|"
    r"(\d+周)|"
    r"(土山のラップ)|"
    r"(^\d+本目)|"
    r"(^[\d:\.\'-]+$)|"
    r"(各自アップ)|"
    r"(各自ジョグ)|"
    r"(^B\s+\d)|"
    r"(^A\s+\d)|"
    r"(560m\s*2[:']40)|"
    r"(スピード練習)",
    re.MULTILINE,
)


def is_pace_data_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if "。" in s and len(s) >= 25:
        return False
    if re.fullmatch(r"(200m\d+本|100m流し\d+本|流し\d+本|500m\d+本|各自アップ.*|各自ジョグ.*)", s):
        return False
    if PACE_DATA_RE.search(s):
        return True
    if re.fullmatch(r"\d+本目:\s*[\d.]+", s):
        return True
    if re.fullmatch(r"[\d.\-]+", s):
        return True
    return False


def is_note_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s in {"動きづくり", "流し", "スピード練習"}:
        return True
    if s.startswith("欠席者"):
        return True
    if s.startswith("間は") or s.startswith("※"):
        return True
    if "。" in s and len(s) >= 20:
        return True
    if any(k in s for k in ("キロ4で", "みかん", "ケガ", "小学生", "リタイア", "完走", "休み明け")):
        return True
    # 距離のみ・ペース未記載のメニュー
    if re.fullmatch(r"(各自アップ|各自ジョグ|200m\d+本|100m流し\d+本|流し\d+本|500m\d+本|"
                    r"男子\d+周|女子\d+周|男子\d+周、.*|600m2本.*|300m.*本.*|"
                    r"動きづくり.*|2\.5km×2|2km×2).*", s):
        return not is_pace_data_line(s) or "RP" in s or "ペース" in s
    return False


def format_item_line(item: Item) -> str:
    return f"{item.menu} {item.distance} {item.pace}"


def build_description(session: Session, original: str) -> str:
    notes: list[str] = []
    for line in original.splitlines():
        s = line.strip()
        if not s:
            continue
        if is_note_line(s) or ("。" in s and len(s) >= 20):
            if not is_pace_data_line(s):
                notes.append(s)

    lines: list[str] = list(notes)
    if session.items:
        if lines:
            lines.append("")
        lines.extend(format_item_line(i) for i in session.items)

    for line in original.splitlines():
        s = line.strip()
        if not s or s in lines:
            continue
        if is_pace_data_line(s) or ("。" in s and len(s) >= 20):
            continue
        if re.search(r"(200m|100m流し|流し\d|500m|2\.5km|2km|600m2本|300m\d|各自|坂道)", s):
            if s not in lines:
                lines.append(s)

    for sk in session.skipped:
        plain = sk.split("—")[0].strip()
        if plain and plain not in lines and plain not in original:
            lines.append(plain)

    return "\n".join(lines).strip()


def apply_to_yaml(years: list[int] | None = None) -> int:
    years = years or APPLY_YEARS
    updated = 0
    for year in years:
        path = INPUT_DIR / f"events.{year}.yaml"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        for ev in data.get("events", []):
            if not is_practice(ev):
                continue
            desc = (ev.get("description") or "").strip()
            if not desc or len(desc) > 8000:
                continue
            session = Session(ev.get("date") or "", ev.get("title", ""), year)
            convert(session, desc)
            if not session.items and not session.skipped:
                continue
            new_desc = build_description(session, desc)
            if new_desc and new_desc != desc:
                ev["description"] = new_desc
                updated += 1
        write_events_yaml(path, data)
        print(f"Updated {path}")
    print(f"Descriptions updated: {updated}")
    return updated


def yaml_scalar(value: str) -> str:
    s = str(value)
    if "\n" in s or ":" in s or s.startswith("'") or s.startswith('"'):
        return "'" + s.replace("'", "''") + "'"
    return s


def dump_event(ev: dict) -> str:
    lines = [f"- title: {yaml_scalar(ev['title'])}"]
    for key in [
        "date", "end_date", "all_day", "category", "status",
        "start_time", "end_time", "location", "description", "tags", "urls",
    ]:
        if key not in ev:
            continue
        val = ev[key]
        if key == "tags":
            lines.append("  tags:")
            for t in val:
                lines.append(f"  - {t}")
        elif key == "urls":
            lines.append("  urls:")
            for u in val:
                lines.append(f"  - {u}")
        elif key == "description":
            s = str(val)
            if "\n" in s:
                lines.append("  description: |")
                for row in s.splitlines():
                    lines.append(f"    {row}")
            elif ":" in s or "'" in s:
                lines.append(f"  description: '{s.replace(chr(39), chr(39) * 2)}'")
            else:
                lines.append(f"  description: {s}")
        elif isinstance(val, bool):
            lines.append(f"  {key}: {'true' if val else 'false'}")
        elif key in {"date", "end_date", "start_time", "end_time"}:
            lines.append(f"  {key}: '{val}'")
        else:
            lines.append(f"  {key}: {yaml_scalar(str(val))}")
    return "\n".join(lines)


def write_events_yaml(path: Path, data: dict) -> None:
    text = path.read_text(encoding="utf-8")
    header_match = re.match(r"((?:#.*\n)*)", text)
    header = header_match.group(1) if header_match else ""
    count = len(data["events"])
    header = re.sub(r"^# 件数: \d+", f"# 件数: {count}", header, count=1, flags=re.MULTILINE)
    body = ["events:"]
    body.extend(dump_event(ev) for ev in data["events"])
    path.write_text(header + "year: " + str(data["year"]) + "\n" + "\n".join(body) + "\n", encoding="utf-8")


def is_practice(ev: dict) -> bool:
    title = ev.get("title", "")
    tags = ev.get("tags") or []
    return (
        "いだてん岱明練習" in tags
        or title in ("岱明夕練", "岱明朝練")
        or (("岱明" in title or "いだてん" in title) and "練習" in title)
    )


def load_all() -> list[Session]:
    out: list[Session] = []
    for year in PRACTICE_YEARS:
        path = INPUT_DIR / f"events.{year}.yaml"
        if not path.exists():
            continue
        with open(path) as f:
            doc = yaml.safe_load(f)
        for ev in doc.get("events", []):
            if not is_practice(ev):
                continue
            desc = (ev.get("description") or "").strip()
            if not desc or len(desc) > 8000:
                continue
            s = Session(ev.get("date") or "", ev.get("title", ""), year)
            convert(s, desc)
            if s.items or s.skipped:
                out.append(s)
    return sorted(out, key=lambda x: (x.date or "9999", x.title))


def render(sessions: list[Session]) -> str:
    by_year: dict[int, list[Session]] = {}
    for s in sessions:
        by_year.setdefault(s.year, []).append(s)

    lines = [
        "# 岱明練習メニュー一覧（k/表記）",
        "",
        "- トラック1周 = **560m**",
        "- 距離と時間の両方が判明する項目のみ k/M:SS に変換",
        "- 300m○○秒 → その300m通過タイムから k/ を算出",
        "",
    ]
    for year in PRACTICE_YEARS:
        lines += ["", f"## {year}年", ""]
        year_sessions = by_year.get(year, [])
        if not year_sessions:
            lines += ["（岱明練習メニューの記録なし）", ""]
            continue
        for s in sorted(year_sessions, key=lambda x: (x.date or "9999", x.title)):
            lines += [f"### {s.date} {s.title}", ""]
            if s.items:
                lines += ["| メニュー | 距離 | ペース |", "|---|---|---|"]
                for i in s.items:
                    lines.append(f"| {i.menu} | {i.distance} | {i.pace} |")
            for sk in s.skipped:
                lines.append(f"- ※ {sk}")
            if not s.items and not s.skipped:
                lines.append("（換算対象なし）")
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="岱明練習メニューを k/表記に変換")
    parser.add_argument("--apply", action="store_true", help="input/events.*.yaml の description を更新")
    parser.add_argument("--year", type=int, action="append", help="--apply 時の対象年（省略時 2025,2026）")
    args = parser.parse_args()

    if args.apply:
        apply_to_yaml(args.year or APPLY_YEARS)

    sessions = load_all()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render(sessions), encoding="utf-8")
    print(f"{OUTPUT_PATH}: {len(sessions)} sessions, {sum(len(s.items) for s in sessions)} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
