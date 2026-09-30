#!/usr/bin/env python3
"""Generate prepared FAQ for 荒玉駅伝 course points (ADR 059).

正本: input/aragyoku/course-points.json / course-points.md（コース解説画像に基づく史実）。
区間のスタート・中継・各地点対応を自然な言い回しでカバーする。

Usage:
  python3 scripts/generate_prepared_qa_course_points.py
  python3 scripts/generate_prepared_qa_course_points.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import entry  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
COURSE_JSON = ROOT / "input" / "aragyoku" / "course-points.json"
SOURCES = [
    "input/aragyoku/course-points.json",
    "input/aragyoku/course-points.md",
    "input/aragyoku/course-points/aragyoku-course-common-points.png",
]
ID_PREFIX = "course-leg-"


def load_faq() -> dict:
    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise SystemExit("invalid FAQ yaml")
    return data


def save_faq(data: dict) -> None:
    data["total"] = len(data["entries"])
    FAQ.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def point_label(pid: str, label: str) -> str:
    if pid == "bridge_1km":
        return "女子1区の1km地点（橋の上）"
    if pid in {"A", "B", "C", "D", "E"}:
        return f"{pid}地点"
    return label or pid


def invert_roles(points: list[dict]) -> dict[str, dict[int, dict[str, str]]]:
    """gender -> leg -> {start|relay|marks: point_id/label/role}"""
    out: dict[str, dict[int, dict[str, object]]] = {
        "女子": {},
        "男子": {},
    }
    for pt in points:
        pid = pt["id"]
        plabel = point_label(pid, pt.get("label") or pid)
        for gender_key, gender in (("women", "女子"), ("men", "男子")):
            for leg_s, role in (pt.get(gender_key) or {}).items():
                leg = int(leg_s)
                slot = out[gender].setdefault(leg, {"marks": []})
                role_s = str(role)
                if role_s == "スタート":
                    slot["start"] = {"id": pid, "label": plabel, "role": role_s}
                elif "中継" in role_s:
                    slot["relay"] = {"id": pid, "label": plabel, "role": role_s}
                else:
                    marks = slot["marks"]
                    assert isinstance(marks, list)
                    marks.append({"id": pid, "label": plabel, "role": role_s})
    return out  # type: ignore[return-value]


def leg_start_entries(roles: dict, drive: str) -> list[dict]:
    out: list[dict] = []
    # 男子1区は地点テーブル上「スタート」ではなく C の145m手前
    out.append(
        entry(
            f"{ID_PREFIX}男子1-start",
            [
                "荒玉駅伝の男子1区は何地点から？",
                "荒玉の男子1区は何地点から？",
                "男子1区は何地点から？",
                "男子1区のスタート地点は？",
                "男子1区はどこから？",
                "男子1区のスタートはどこ？",
                "荒玉男子1区はどこから走る？",
                "荒玉駅伝男子1区スタート地点",
                "男子1区スタートはCの手前？",
                "荒玉男子スタートはC地点の手前何m？",
                "男子スタートはどこから？",
            ],
            (
                "荒玉駅伝男子1区のスタートは、C地点の145m手前（男子スタート）です。"
                " C地点通過時は0.145km地点になります。"
                f" コース図: {drive}"
            ),
            SOURCES,
            ["aragyoku", "course", "男子", "1区"],
        )
    )
    for gender, legs in roles.items():
        for leg, info in sorted(legs.items()):
            start = info.get("start")
            if not isinstance(start, dict):
                continue
            plabel = str(start["label"])
            eid = f"{ID_PREFIX}{gender}{leg}-start"
            qs = [
                f"荒玉駅伝の{gender}{leg}区は何地点から？",
                f"荒玉の{gender}{leg}区は何地点から？",
                f"{gender}{leg}区は何地点から？",
                f"{gender}{leg}区のスタート地点は？",
                f"{gender}{leg}区はどこから？",
                f"{gender}{leg}区のスタートはどこ？",
                f"荒玉{gender}{leg}区はどこから走る？",
                f"荒玉駅伝{gender}{leg}区スタート地点",
                f"{gender}{leg}区は{plabel}から？",
            ]
            ans = (
                f"荒玉駅伝{gender}{leg}区のスタートは{plabel}です。"
                f" 共通ポイント図（A/B/C/D/E・橋）に基づく現行コースです。"
                f" コース図: {drive}"
            )
            out.append(entry(eid, qs, ans, SOURCES, ["aragyoku", "course", gender, f"{leg}区"]))
    return out


def leg_relay_entries(roles: dict, drive: str) -> list[dict]:
    out: list[dict] = []
    for gender, legs in roles.items():
        for leg, info in sorted(legs.items()):
            relay = info.get("relay")
            if not isinstance(relay, dict):
                continue
            plabel = str(relay["label"])
            role = str(relay["role"])
            next_leg = leg + 1
            eid = f"{ID_PREFIX}{gender}{leg}-relay"
            qs = [
                f"荒玉駅伝の{gender}{leg}区の中継所はどこ？",
                f"{gender}{leg}区の中継は何地点？",
                f"{gender}{leg}区はどこで中継？",
                f"{gender}{leg}区のゴール地点は？",
                f"{gender}{leg}区はどこまで？",
                f"{gender}{leg}→{next_leg}区の中継所は？",
                f"荒玉{gender}{leg}区の中継地点は？",
            ]
            ans = (
                f"荒玉駅伝{gender}{leg}区の中継（区間終点）は{plabel}です（{role}）。"
                f" 次の{gender}{next_leg}区は同じ地点からスタートします。"
                f" コース図: {drive}"
            )
            out.append(entry(eid, qs, ans, SOURCES, ["aragyoku", "course", gender, f"{leg}区", "中継"]))
    return out


def point_overview_entries(points: list[dict], drive: str) -> list[dict]:
    out: list[dict] = []
    for pt in points:
        pid = pt["id"]
        plabel = point_label(pid, pt.get("label") or pid)
        note = (pt.get("location_note") or "").strip()
        wbits = [f"女子{k}区={v}" for k, v in sorted((pt.get("women") or {}).items(), key=lambda x: int(x[0]))]
        mbits = [f"男子{k}区={v}" for k, v in sorted((pt.get("men") or {}).items(), key=lambda x: int(x[0]))]
        eid = f"course-point-{pid}"
        qs = [
            f"荒玉の{plabel}はどこ？",
            f"荒玉コースの{plabel}",
            f"{plabel}は何区の何km？",
            f"荒玉駅伝の{plabel}は？",
        ]
        if pid in {"A", "B", "C", "D", "E"}:
            qs.extend(
                [
                    f"荒玉の{pid}地点は？",
                    f"{pid}地点は女子何区？",
                    f"{pid}地点は男子何区？",
                    f"荒玉駅伝{pid}地点の対応は？",
                ]
            )
        if pid == "bridge_1km":
            qs.extend(
                [
                    "橋の上は何区の何km？",
                    "荒玉の橋は何地点？",
                    "1km地点の橋はどの区間？",
                ]
            )
        ans = f"荒玉駅伝コースの{plabel}です。"
        if note:
            ans += f" {note}"
            if not ans.endswith("。"):
                ans += "。"
        if wbits:
            ans += " " + "、".join(wbits) + "。"
        if mbits:
            ans += " " + "、".join(mbits) + "。"
        ans += f" コース図: {drive}"
        out.append(entry(eid, qs, ans, SOURCES, ["aragyoku", "course", pid]))
    return out


def finish_leg_entries(drive: str) -> list[dict]:
    """最終区は中継ではなくゴール。"""
    out: list[dict] = []
    for gender, leg in (("女子", 5), ("男子", 6)):
        eid = f"{ID_PREFIX}{gender}{leg}-finish"
        qs = [
            f"荒玉駅伝の{gender}{leg}区はどこまで？",
            f"{gender}{leg}区のゴール地点は？",
            f"{gender}{leg}区はどこで終わる？",
            f"{gender}{leg}区のフィニッシュは？",
        ]
        ans = (
            f"荒玉駅伝{gender}{leg}区はC地点スタートで、EとAの間から南へ分かれた先のゴールでフィニッシュします。"
            f" 女子5区と男子6区のゴールは共通です。"
            f" コース図: {drive}"
        )
        out.append(entry(eid, qs, ans, SOURCES, ["aragyoku", "course", gender, f"{leg}区", "ゴール"]))
    return out


def special_fact_entries(data: dict, drive: str) -> list[dict]:
    out: list[dict] = []
    out.append(
        entry(
            "course-relay-women4-men5-same-C",
            [
                "女子4区と男子5区の中継所は同じ？",
                "女子4→5区と男子5→6区の中継は同じ地点？",
                "C地点は女子何区と男子何区の中継？",
                "荒玉の中継所Cはどの区間？",
            ],
            (
                "女子4→5区と男子5→6区の中継所は同じC地点です。"
                " 女子5区と男子6区はいずれもC地点スタート。"
                f" コース図: {drive}"
            ),
            SOURCES,
            ["aragyoku", "course", "C", "中継"],
        )
    )
    out.append(
        entry(
            "course-women4-starts-at-A",
            [
                "女子4区はA地点から？",
                "荒玉女子4区スタートはA？",
                "A地点は女子4区のスタート？",
                "女子4区スタート地点はA地点ですか？",
            ],
            (
                "はい。荒玉駅伝女子4区のスタートはA地点です。"
                " 女子4区はA→B（1.0km）→C（2.0km・中継）で、Cで女子5区へつなぎます。"
                f" コース図: {drive}"
            ),
            SOURCES,
            ["aragyoku", "course", "女子", "4区", "A"],
        )
    )
    lap = data.get("lap_metres")
    out.append(
        entry(
            "course-points-lap-and-order",
            [
                "荒玉コースの進行順は？",
                "共通ポイントの周回順は？",
                "Dからどう進む？",
            ],
            (
                f"荒玉駅伝の共通ポイント進行順は D → 1km（橋） → E → A → B → C → D です。"
                f" 1周は{lap}m（4.855km）。"
                f" コース図: {drive}"
            ),
            SOURCES,
            ["aragyoku", "course"],
        )
    )
    goal = data.get("overview_goal") or {}
    if goal:
        out.append(
            entry(
                "course-goal-women5-men6",
                [
                    "荒玉のゴールはどこ？",
                    "女子5区のゴール地点は？",
                    "男子6区のゴールはどこ？",
                    "荒玉駅伝のフィニッシュは？",
                ],
                (
                    "荒玉駅伝のゴールは女子5区・男子6区共通で、EとAの間で南へ分かれた先です。"
                    f" {goal.get('location_note') or ''}"
                    f" コース図: {drive}"
                ).strip(),
                SOURCES,
                ["aragyoku", "course", "ゴール"],
            )
        )
    return out


def build_entries(data: dict) -> list[dict]:
    drive = str(data.get("drive_url") or "")
    points = list(data.get("points") or [])
    roles = invert_roles(points)
    entries: list[dict] = []
    entries.extend(leg_start_entries(roles, drive))
    entries.extend(leg_relay_entries(roles, drive))
    entries.extend(finish_leg_entries(drive))
    entries.extend(point_overview_entries(points, drive))
    entries.extend(special_fact_entries(data, drive))
    return entries


def upsert(existing: list[dict], new_entries: list[dict]) -> tuple[int, int]:
    by_id = {e["id"]: i for i, e in enumerate(existing)}
    added = updated = 0
    for e in new_entries:
        eid = e["id"]
        if eid in by_id:
            existing[by_id[eid]] = e
            updated += 1
        else:
            existing.append(e)
            by_id[eid] = len(existing) - 1
            added += 1
    return added, updated


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    course = json.loads(COURSE_JSON.read_text(encoding="utf-8"))
    new_entries = build_entries(course)
    print(f"generated {len(new_entries)} course-point Q&A entries")

    # sanity: women 4 start must be A
    w4 = next(e for e in new_entries if e["id"] == "course-leg-女子4-start")
    assert "A地点" in w4["answer"], w4["answer"]
    assert any("何地点から" in q for q in w4["questions"])

    if args.dry_run:
        for e in new_entries[:8]:
            print("-", e["id"], e["questions"][0], "->", e["answer"][:80])
        return 0

    data = load_faq()
    # drop previous generated course-leg / course-point-* (except hand-written facts)
    keep_ids = {
        "aragyoku-course-image",
        "aragyoku-course-points-facts",
        "course-loop-4855",
        "course-men-start-145",
        "course-bridge-1km",
        "course-points-order",
    }
    before = len(data["entries"])
    data["entries"] = [
        e
        for e in data["entries"]
        if not (
            str(e.get("id", "")).startswith(ID_PREFIX)
            or (
                str(e.get("id", "")).startswith("course-point-")
                and e.get("id") not in keep_ids
            )
            or e.get("id")
            in {
                "course-relay-women4-men5-same-C",
                "course-women4-starts-at-A",
                "course-points-lap-and-order",
                "course-goal-women5-men6",
                "course-points-overview",
            }
            or re.match(r"course-leg-(女子|男子)\d+-finish$", str(e.get("id", "")))
        )
    ]
    removed = before - len(data["entries"])
    added, updated = upsert(data["entries"], new_entries)
    save_faq(data)
    print(f"removed stale {removed}; added {added}; updated {updated}; total {len(data['entries'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
