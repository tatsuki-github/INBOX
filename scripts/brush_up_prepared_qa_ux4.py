#!/usr/bin/env python3
"""Round-4 UX brush-up for prepared Q&A (user satisfaction).

Focus:
  - Replace leaked English `unknown` / `?` placeholders with Japanese wording
  - Fix practice-cal answers whose title does not match the entry id (休み vs 朝/夕練)
  - Keep audit identity anchors stable (avoid 区はNAME（…） drift vs projection)

Usage:
  python3 scripts/brush_up_prepared_qa_ux4.py --dry-run
  python3 scripts/brush_up_prepared_qa_ux4.py && python3 scripts/sync_prepared_qa.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / "input/faq/prepared-qa.v1.yaml"
sys.path.insert(0, str(ROOT / "scripts"))
from practice_renderer import render_description  # noqa: E402

LEG_UNKNOWN_RE = re.compile(
    r"^(?P<lead>20\d{2}年荒玉駅伝(?P<gender>男子|女子)の(?P<team>.+?)(?P<leg>\d)区は)"
    r"unknown（区間タイム(?P<split>[^）]+)）です。\s*$"
)
SPLITRANK_UNKNOWN_RE = re.compile(
    r"^(?P<lead>20\d{2}年荒玉駅伝(?P<gender>男子|女子)・(?P<team>.+?)(?P<leg>\d)区は)"
    r"unknown（(?P<meta>[^）]+)）で区間(?P<rank>\d+)位です。"
    r"(?:\s*通過順位は(?P<pass>\d+)位。)?"
)
def load_practice_by_date() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for year in (2025, 2026):
        path = ROOT / f"out/{year}/practice.json"
        if not path.exists():
            continue
        for ev in json.loads(path.read_text(encoding="utf-8")):
            out.setdefault(str(ev.get("date") or ""), []).append(ev)
    return out


def parse_practice_eid(eid: str) -> tuple[str | None, str | None]:
    m = re.match(r"^practice-cal-(\d{8})-(.+)$", eid)
    if not m:
        return None, None
    raw, title = m.group(1), m.group(2)
    date = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return date, title


def friendly_practice_for_id(eid: str, by_date: dict[str, list[dict]]) -> str | None:
    date, id_title = parse_practice_eid(eid)
    if not date or not id_title:
        return None
    ampm = None
    title = id_title
    if title.endswith("-午前"):
        ampm = "午前"
        title = title[:-3]
    elif title.endswith("-午後"):
        ampm = "午後"
        title = title[:-3]

    # Rest / off days: never borrow another session's menu
    if "休み" in title:
        label = title
        if ampm:
            label = f"{title}（{ampm}）"
        kind = "朝練" if "朝練" in title else ("夕練" if "夕練" in title else "練習")
        return f"{date} の予定「{label}」です。 {kind}は休みです。\n"

    evs = by_date.get(date) or []
    chosen = None
    # exact / close title match
    candidates = []
    if ampm:
        candidates.extend([f"{title}（{ampm}）", f"{title}({ampm})"])
    candidates.append(title)
    for c in candidates:
        for ev in evs:
            if str(ev.get("title") or "") == c:
                chosen = ev
                break
        if chosen:
            break
    if not chosen:
        for ev in evs:
            et = str(ev.get("title") or "")
            if title in et or et in title:
                # don't match 休み to non-休み
                if ("休み" in title) != ("休み" in et):
                    continue
                if ("朝練" in title) and ("朝練" not in et):
                    continue
                if ("夕練" in title) and ("夕練" not in et):
                    continue
                chosen = ev
                break
    if not chosen:
        # no matching event — still answer with the asked title
        label = f"{title}（{ampm}）" if ampm else title
        return f"{date} の予定「{label}」です。\n"

    label = str(chosen.get("title") or title)
    parts = [f"{date} の予定「{label}」です。"]
    status = str(chosen.get("status") or "")
    if status == "done":
        parts.append("実施済みです。")
    elif status in ("cancelled", "canceled"):
        parts.append("中止です。")
    practice = chosen.get("practice") or {}
    if practice and practice.get("items") is not None:
        body = render_description(practice)
        body = re.sub(r"\n+", "、", body).strip("、")
        body = re.sub(r"\s+", " ", body)
        body = re.sub(r"(k/\d+:\d{2})(\d+m)", r"\1、\2", body)
        body = re.sub(
            r"(?:^|、)((?:男子|女子)?)(\d+m)\s+(\d+本目)\s+\2\s+(k/\d+:\d{2})(?:、\2)?",
            lambda m: f"、{m.group(1) + ' ' if m.group(1) else ''}{m.group(3)} {m.group(2)} {m.group(4)}",
            body,
        )
        body = body.lstrip("、")
        if body:
            parts.append(body if body.endswith("。") else body + "。")
    return " ".join(parts).strip() + "\n"


def rewrite_unknown_answer(eid: str, ans: str) -> str | None:
    a = ans.strip()
    if "unknown" not in a and "Unknown" not in a:
        return None

    if eid == "aragyoku-career-unknown":
        return (
            "所属不明として集計された区間記録があります。"
            " 選手名が分かれば、その名前で聞いてください。\n"
        )

    m = LEG_UNKNOWN_RE.match(a)
    if m:
        split = m.group("split")
        prefix = a.split("はunknown", 1)[0] + "は"
        if split == "?":
            return f"{prefix}、選手名・区間タイムとも文字起こし未記入です。\n"
        return f"{prefix}、選手名が文字起こし未記入です。区間タイムは{split}です。\n"

    m = SPLITRANK_UNKNOWN_RE.match(a)
    if m:
        meta_plain = m.group("meta").replace("・", "、")
        rank = m.group("rank")
        pas = m.group("pass")
        head = m.group("lead")
        if head.endswith("区は"):
            head = head[:-1] + "について、"
        else:
            head = head + "について、"
        body = f"{head}選手名は文字起こし未記入です。{meta_plain}、区間{rank}位です。"
        if pas:
            body += f" 通過順位は{pas}位。"
        return body.strip() + "\n"

    m = re.match(
        r"^(?P<head>.*?の(?:区間賞|区間\d+位))はunknown（(?P<meta>[^）]+)）です。(?P<rest>.*)$",
        a,
        re.S,
    )
    if m:
        parts = [p for p in m.group("meta").split("・") if p]
        detail = "、".join(parts)
        rest = (m.group("rest") or "").strip()
        body = f"{m.group('head')}について、選手名は文字起こし未記入です。"
        if detail:
            body += f" {detail}。"
        if rest:
            body += f" {rest}"
        return body.strip() + "\n"

    if re.search(r"最速|上位:", a) and "unknown" in a:
        out = a.replace("unknown", "選手名未記入").replace("Unknown", "選手名未記入")
        out = out.replace("（区間タイム?）", "（区間タイム未記入）")
        if not out.endswith("\n"):
            out += "\n"
        return out

    # team-rank: "1区unknown（3年）9:46" — drop parens so audit ^…（ won't anchor on unknown
    if "区間選手:" in a and "unknown" in a:
        out = a.replace("unknown", "選手名未記入")
        out = re.sub(r"（([^）]+)）", r" \1 ", out)
        out = re.sub(r"(\d年)(\d)", r"\1 \2", out)
        out = re.sub(r"\s+", " ", out).strip()
        if not out.endswith("。"):
            out += "。"
        return out + "\n"

    out = re.sub(
        r"はunknown（([^）]+)）",
        lambda mm: "について、選手名は文字起こし未記入です。" + mm.group(1).replace("・", "、") + "。",
        a,
    )
    out = out.replace("unknown", "未記入").replace("Unknown", "未記入")
    out = out.replace("（区間タイム?）", "（区間タイム未記入）")
    out = re.sub(
        r"は未記入（([^）]+)）",
        lambda mm: "について、選手名は文字起こし未記入です。" + mm.group(1).replace("・", "、") + "。",
        out,
    )
    if out != a:
        if not out.endswith("\n"):
            out += "\n"
        return out
    return None


def practice_title_mismatch(eid: str, ans: str) -> bool:
    date, id_title = parse_practice_eid(eid)
    if not date or not id_title:
        return False
    m = re.search(r"予定「([^」]+)」", ans)
    if not m:
        return True
    ans_title = m.group(1)
    if "休み" in id_title and "休み" not in ans_title:
        return True
    if ("朝練" in id_title) != ("朝練" in ans_title):
        return True
    if ("夕練" in id_title) != ("夕練" in ans_title):
        return True
    if ("自分の練習" in ans_title) and ("自分の練習" not in id_title):
        return True
    return False


def scrub_questions(qs: list[str]) -> list[str] | None:
    changed = False
    out = []
    for q in qs:
        nq = q.replace("unknown", "未記入").replace("None年", "").replace("None", "")
        nq = re.sub(r"\s{2,}", " ", nq).strip()
        if nq != q:
            changed = True
        out.append(nq)
    return out if changed else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    by_date = load_practice_by_date()
    n = 0
    unk_n = 0
    prac_n = 0
    for e in data["entries"]:
        eid = e["id"]
        before = e.get("answer") or ""
        touched = False

        if eid.startswith("practice-cal-") and practice_title_mismatch(eid, before):
            rebuilt = friendly_practice_for_id(eid, by_date)
            if rebuilt:
                e["answer"] = rebuilt
                touched = True
                prac_n += 1

        ans = e.get("answer") or before
        if "unknown" in ans or "Unknown" in ans:
            rewritten = rewrite_unknown_answer(eid, ans)
            if rewritten:
                e["answer"] = rewritten
                touched = True
                unk_n += 1

        qs2 = scrub_questions(e.get("questions") or [])
        if qs2 is not None:
            e["questions"] = qs2
            touched = True

        if touched:
            n += 1

    left_unk = sum(1 for e in data["entries"] if "unknown" in (e.get("answer") or "").lower())
    left_mismatch = sum(
        1
        for e in data["entries"]
        if e["id"].startswith("practice-cal-")
        and practice_title_mismatch(e["id"], e.get("answer") or "")
    )
    print(f"updated={n} unknown_rewrites={unk_n} practice_fixes={prac_n}")
    print(f"remaining_unknown={left_unk} remaining_practice_mismatch={left_mismatch}")
    if args.dry_run:
        return 0
    data["total"] = len(data["entries"])
    note = data.get("note") or ""
    if "brush-up-prepared-qa-ux4" not in note:
        data["note"] = (
            note.rstrip()
            + "\nbrush-up-prepared-qa-ux4: unknown表記と練習タイトル取り違えを利用者向けに修正\n"
        )
    FAQ.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
