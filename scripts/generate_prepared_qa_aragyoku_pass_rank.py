#!/usr/bin/env python3
"""Generate Aragyoku 2026 through-leg / overall rank-prediction prepared FAQ.

Answers「今年の荒玉駅伝の女子2区までの順位予想」等 from
`区間オーダー_数式予想.json` の cumulative_sec / passing_rank。

Usage:
  python3 scripts/generate_prepared_qa_aragyoku_pass_rank.py --dry-run
  python3 scripts/generate_prepared_qa_aragyoku_pass_rank.py
  python3 scripts/generate_prepared_qa_aragyoku_pass_rank.py && python3 scripts/sync_prepared_qa.py
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
FORMULA_JSON = (
    ROOT
    / "input"
    / "external"
    / "drive"
    / "shared"
    / "大会"
    / "2026年度"
    / "1014-1015_荒玉中体連駅伝"
    / "区間オーダー_数式予想.json"
)
EXPAND_MD = (
    "input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝/校別展開_数式予想.md"
)
FORMULA_JSON_CORPUS = (
    "input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝/区間オーダー_数式予想.json"
)
FOLDER = "https://drive.google.com/drive/folders/1G8IlaBp9xVmXUynBAjV9ZZQPfFqzj4Yi"
ID_PREFIX = "aragyoku-2026-pass-rank-"


def fmt_clock(sec: float | int) -> str:
    sec_i = int(round(float(sec)))
    return f"{sec_i // 60}:{sec_i % 60:02d}"


def load_faq() -> dict:
    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise SystemExit("invalid FAQ yaml")
    return data


def upsert(existing: list[dict], new_entries: list[dict]) -> tuple[int, int]:
    by_id = {e["id"]: i for i, e in enumerate(existing)}
    claimed = {q for e in existing for q in (e.get("questions") or [])}
    added = updated = 0
    for e in new_entries:
        eid = e["id"]
        qs = []
        for q in e["questions"]:
            if q in claimed and (
                eid not in by_id or q not in (existing[by_id[eid]].get("questions") or [])
            ):
                continue
            qs.append(q)
            claimed.add(q)
        if not qs:
            continue
        e["questions"] = qs
        if eid in by_id:
            old = existing[by_id[eid]]
            merged_q = list(old.get("questions") or [])
            for q in qs:
                if q not in merged_q:
                    merged_q.append(q)
            old["questions"] = merged_q
            old["answer"] = e["answer"]
            old["sources"] = e["sources"]
            tags = list(old.get("tags") or [])
            for t in e.get("tags") or []:
                if t not in tags:
                    tags.append(t)
            old["tags"] = tags
            updated += 1
        else:
            existing.append(e)
            by_id[eid] = len(existing) - 1
            added += 1
    return added, updated


def through_rows(teams: list[dict], through: int) -> list[tuple[int, str, float]]:
    rows: list[tuple[float, str]] = []
    for t in teams:
        if not t.get("complete"):
            continue
        legs = t.get("legs") or []
        if len(legs) < through:
            continue
        cum = legs[through - 1].get("cumulative_sec")
        if cum is None:
            continue
        rows.append((float(cum), str(t["team"])))
    rows.sort(key=lambda x: (x[0], x[1]))
    return [(i + 1, name, cum) for i, (cum, name) in enumerate(rows)]


def top_summary(ranked: list[tuple[int, str, float]], limit: int = 8) -> str:
    return "、".join(f"{r}位{name}（{fmt_clock(cum)}）" for r, name, cum in ranked[:limit])


def team_line(ranked: list[tuple[int, str, float]], team_key: str) -> str | None:
    for r, name, cum in ranked:
        if team_key in name or name in team_key:
            return f"{name}は{r}位予想（累計{fmt_clock(cum)}）"
    return None


def through_questions(gender: str, through: int, max_leg: int) -> list[str]:
    g = gender
    n = through
    qs = [
        f"今年の荒玉駅伝の{g}{n}区までの順位予想",
        f"今年の荒玉駅伝の{g}{n}区までの順位予想は？",
        f"今年の荒玉{g}{n}区までの通過順位予想",
        f"今年の荒玉{g}{n}区までの順位予想",
        f"2026年荒玉駅伝{g}{n}区までの順位予想は？",
        f"2026年荒玉駅伝{g}{n}区までの通過順位予想",
        f"2026年の荒玉{g}{n}区までの順位予想",
        f"荒玉駅伝{g}{n}区までの順位予想",
        f"荒玉駅伝の{g}{n}区までの順位予想は？",
        f"荒玉{g}の{n}区までの順位予想",
        f"荒玉{g}{n}区までの通過順位予想は？",
        f"{g}{n}区までの荒玉順位予想",
        f"荒玉中体連駅伝{g}{n}区までの順位予想",
        f"今年の荒玉中体連{g}{n}区までの予想順位",
    ]
    if n == max_leg:
        qs.extend(
            [
                f"今年の荒玉駅伝の{g}の順位予想",
                f"今年の荒玉駅伝{g}の総合順位予想は？",
                f"今年の荒玉{g}の順位予想は？",
                f"2026年荒玉駅伝{g}の順位予想",
                f"2026年荒玉{g}総合順位予想",
                f"荒玉駅伝{g}の順位予想は？",
                f"荒玉{g}の総合予想順位",
                f"荒玉駅伝{g}の優勝校予想は？",
                f"今年の荒玉{g}優勝予想",
            ]
        )
    if n == 1:
        qs.extend(
            [
                f"今年の荒玉駅伝{g}1区後の順位予想",
                f"荒玉{g}1区通過順位予想",
            ]
        )
    return qs


def overall_gender_questions(gender: str) -> list[str]:
    # Extra short asks without「まで」 that still mean full ranking.
    return [
        f"今年の荒玉の{gender}順位予想",
        f"荒玉{gender}順位予想2026",
        f"{gender}荒玉の予想順位は？",
        f"今年の荒玉駅伝{gender}は誰が勝つ？",
        f"2026荒玉{gender}優勝校は？（予想）",
    ]


def team_through_questions(gender: str, through: int, team: str) -> list[str]:
    return [
        f"今年の荒玉駅伝{gender}{through}区までの{team}の順位予想",
        f"今年の荒玉{gender}{through}区まで{team}は何位予想？",
        f"2026年荒玉{gender}{through}区までの{team}順位予想",
        f"荒玉駅伝{gender}{through}区まで{team}は何位？",
        f"{team}の荒玉{gender}{through}区までの順位予想",
    ]


def gen_entries() -> list[dict]:
    """Read-only rebuild for audit_prepared_qa_facts source_projection."""
    if not FORMULA_JSON.exists():
        raise FileNotFoundError(FORMULA_JSON)
    return build_entries(json.loads(FORMULA_JSON.read_text(encoding="utf-8")))


def build_entries(data: dict) -> list[dict]:
    as_of = data.get("as_of", "2026-09-27")
    event_date = data.get("event_date", "2026-10-14")
    sources = [FORMULA_JSON_CORPUS, EXPAND_MD]
    out: list[dict] = []
    disclaimer = (
        f"数式予想（基準日{as_of}、大会{event_date}、公式オーダー未着）の通過順位目安です。"
        " 確定オーダーではありません。"
        f" 資料: {FOLDER}"
    )

    for gender, max_leg in (("女子", 5), ("男子", 6)):
        teams = data["teams"][gender]
        for through in range(1, max_leg + 1):
            ranked = through_rows(teams, through)
            if not ranked:
                continue
            summary = top_summary(ranked, limit=8)
            if through == max_leg:
                head = f"2026年荒玉駅伝{gender}の総合順位予想です。"
                label = "総合"
            else:
                head = f"2026年荒玉駅伝{gender}の{through}区までの通過順位予想です。"
                label = f"{through}区まで"
            ans = f"{head} {label}: {summary}。 {disclaimer}"
            eid = f"{ID_PREFIX}{gender}-through{through}"
            qs = through_questions(gender, through, max_leg)
            if through == max_leg:
                qs.extend(overall_gender_questions(gender))
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    sources,
                    ["aragyoku", "formula", "preview", "2026", gender, "pass-rank"],
                )
            )

            # Focus-team asks for this through-leg
            for team in ("岱明中", "南関中", "玉名中", "荒尾三中", "玉陵中"):
                tip = team_line(ranked, team)
                if not tip:
                    continue
                short = team.replace("中", "")
                t_ans = (
                    f"2026年荒玉駅伝{gender}・{label}の数式予想では、{tip}です。"
                    f" 上位目安: {summary}。 {disclaimer}"
                )
                out.append(
                    entry(
                        f"{ID_PREFIX}{gender}-through{through}-{short}",
                        team_through_questions(gender, through, short)
                        + team_through_questions(gender, through, team),
                        t_ans,
                        sources,
                        ["aragyoku", "formula", "preview", "2026", gender, "pass-rank", short],
                    )
                )

        # Gender-free「順位予想」that still names gender in answer is covered above.
        # Add「男女の順位予想」overview.
    men = through_rows(data["teams"]["男子"], 6)
    women = through_rows(data["teams"]["女子"], 5)
    if men and women:
        out.append(
            entry(
                f"{ID_PREFIX}both-overall",
                [
                    "今年の荒玉駅伝の順位予想",
                    "今年の荒玉駅伝の順位予想は？",
                    "2026年荒玉駅伝の順位予想",
                    "荒玉駅伝の順位予想は？",
                    "今年の荒玉の総合順位予想",
                    "荒玉2026の優勝校予想",
                    "今年の荒玉誰が勝つ？",
                ],
                (
                    "2026年荒玉駅伝の総合順位予想（数式）です。"
                    f" 男子: {top_summary(men, 6)}。"
                    f" 女子: {top_summary(women, 6)}。"
                    f" {disclaimer}"
                ),
                sources,
                ["aragyoku", "formula", "preview", "2026", "pass-rank"],
            )
        )
    return out


def existing_ids_and_questions(text: str) -> tuple[set[str], set[str]]:
    """Scan FAQ text lightly so we can append without a full rewrite."""
    ids = set(re.findall(r"(?m)^- id:\s*(\S+)\s*$", text))
    qs = set()
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("- ") and not s.startswith("- id:") and ":" not in s[2:40]:
            # question list item under questions:
            q = s[2:].strip().strip("'\"")
            if q and not q.startswith("input/") and not q.startswith("out/"):
                qs.add(q)
    return ids, qs


def append_entries(new_entries: list[dict]) -> tuple[int, int]:
    text = FAQ.read_text(encoding="utf-8")
    ids, claimed = existing_ids_and_questions(text)
    added = updated = 0
    chunks: list[str] = []
    for e in new_entries:
        eid = e["id"]
        if eid in ids:
            updated += 1
            continue
        qs = [q for q in e["questions"] if q not in claimed]
        if not qs:
            continue
        for q in qs:
            claimed.add(q)
        e["questions"] = qs
        # Dump a single mapping under entries list style ("- id:")
        block = yaml.safe_dump(e, allow_unicode=True, sort_keys=False, width=1000)
        # indent as list item
        lines = block.splitlines()
        if not lines:
            continue
        chunks.append("- " + lines[0] + "\n")
        for line in lines[1:]:
            chunks.append("  " + line + "\n")
        ids.add(eid)
        added += 1
    if not chunks:
        print("no new entries to append")
        return added, updated
    marker = "aragyoku-pass-rank-2026"
    if marker not in text:
        text = text.replace(
            "note: |",
            "note: |\n  aragyoku-pass-rank-2026: 荒玉2026数式予想のN区まで通過順位・総合順位を想定Q&A化。",
            1,
        )
    if not text.endswith("\n"):
        text += "\n"
    text += "".join(chunks)
    FAQ.write_text(text, encoding="utf-8")
    return added, updated


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--rewrite",
        action="store_true",
        help="Full YAML rewrite (slow/large diff). Default appends new ids only.",
    )
    args = ap.parse_args()
    if not FORMULA_JSON.exists():
        raise SystemExit(f"missing {FORMULA_JSON}")
    data = json.loads(FORMULA_JSON.read_text(encoding="utf-8"))
    new_entries = build_entries(data)
    print(f"generated {len(new_entries)} entries")
    if args.dry_run:
        for e in new_entries[:5]:
            print("-", e["id"], len(e["questions"]), "qs")
            print(" ", e["answer"][:180].replace("\n", " "))
        sample = next(e for e in new_entries if e["id"].endswith("女子-through2"))
        print("SAMPLE", sample["id"])
        print(sample["answer"])
        return 0
    if args.rewrite:
        faq = load_faq()
        added, updated = upsert(faq["entries"], new_entries)
        note = faq.get("note") or ""
        marker = "aragyoku-pass-rank-2026"
        if marker not in note:
            faq["note"] = (
                note.rstrip()
                + "\naragyoku-pass-rank-2026: 荒玉2026数式予想のN区まで通過順位・総合順位を想定Q&A化。\n"
            )
        FAQ.write_text(
            yaml.safe_dump(faq, allow_unicode=True, sort_keys=False, width=1000),
            encoding="utf-8",
        )
    else:
        added, updated = append_entries(new_entries)
    print(f"wrote {FAQ} (+{added} / skip-existing {updated})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
