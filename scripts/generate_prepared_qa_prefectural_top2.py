#!/usr/bin/env python3
"""Generate prepared FAQ: 荒玉駅伝 2位まで → 県駅伝出場（ADR 059）.

正本の前提は徹底対策ガイド 4.16:
「2位まで県駅伝に出場できる」。出場枠は年度の大会要項で再確認。

Usage:
  python3 scripts/generate_prepared_qa_prefectural_top2.py
  python3 scripts/generate_prepared_qa_prefectural_top2.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_prepared_qa_bulk import entry  # noqa: E402

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
ID_PREFIX = "aragyoku-pref-top2-"
SOURCES = [
    "input/aragyoku/guides/荒玉駅伝2026徹底対策.extracted.txt",
    "work/build_aragyoku_2026_pdf.py",
    "docs/adr/059-prepared-qa-answers.md",
]

CORE_ANSWER = (
    "県駅伝に出場できるのは、男女上位2校です。"
    " 荒玉駅伝（玉名荒尾中体連駅伝）では、男女とも総合2位までが県駅伝の出場圏です。"
)

NOT_3RD_ANSWER = (
    "県駅伝に出場できるのは、男女上位2校です。"
    " 原則として荒玉駅伝は総合2位までが県駅伝出場圏で、3位以下は出場圏外です。"
)

GENDER_ANSWER = (
    "県駅伝に出場できるのは、男女上位2校です。"
    " 男子も女子も同じで、荒玉駅伝の総合2位までが県駅伝出場圏です。"
    " 男女別々に、それぞれの総合順位で見ます。"
)

CONFIRM_ANSWER = (
    "県駅伝に出場できるのは、男女上位2校です。"
    " 荒玉駅伝では男女とも総合2位までが出場圏です。"
)

LINE_ANSWER = (
    "県駅伝出場圏（2位）を狙うときの到達ラインは、歴代2位チームの総合ペースを"
    "距離補正して見た参考値です。"
    " 必達タイムではなく、競技力・天候・人数・コース条件で変わります。"
    " 男子の中央値目安はおおよそ57:36前後、女子はおおよそ42:41前後"
    "（現行コース換算の参考総合）です。"
)

GOAL_ANSWER = (
    "県駅伝に出場できるのは、男女上位2校です。"
    " つまり荒玉駅伝で総合2位以内（優勝または準優勝）を取る必要があります。"
    " 3位では原則として出場圏外です。"
)


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


def _dedupe(qs: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for q in qs:
        q = " ".join(q.split()).strip()
        if not q or q in seen:
            continue
        seen.add(q)
        out.append(q)
    return out


def core_questions() -> list[str]:
    """~70 paraphrases of the core fact."""
    events = [
        "荒玉駅伝",
        "荒玉",
        "玉名荒尾中体連駅伝",
        "荒玉の駅伝",
        "荒玉大会",
    ]
    targets = [
        "県駅伝",
        "県の駅伝",
        "熊本県駅伝",
        "県大会の駅伝",
        "県駅伝大会",
    ]
    qs: list[str] = []

    # 何位まで系
    for ev in events:
        for tg in targets:
            qs.extend(
                [
                    f"{ev}で何位まで{tg}に出られる？",
                    f"{ev}は何位まで{tg}出場？",
                    f"{ev}で{tg}に出るには何位？",
                    f"{ev}は何位までが{tg}に出場できる？",
                    f"{ev}は何位までが{tg}に出られる？",
                    f"{ev}で何位までが{tg}に出場できる？",
                ]
            )

    # 2位まで確認系
    for ev in ("荒玉駅伝", "荒玉", "玉名荒尾中体連駅伝"):
        for tg in ("県駅伝", "県の駅伝", "熊本県駅伝"):
            qs.extend(
                [
                    f"{ev}は2位まで{tg}に出られる？",
                    f"{ev}で2位以内なら{tg}出場できる？",
                    f"{ev}の2位は{tg}に出られる？",
                    f"{ev}準優勝でも{tg}に出られる？",
                ]
            )

    # 出場権・出場圏・条件系
    qs.extend(
        [
            "荒玉駅伝の県駅伝出場条件は？",
            "荒玉の県駅伝出場権は何位まで？",
            "荒玉駅伝の出場圏は？",
            "荒玉駅伝で県駅伝に進めるのは何位まで？",
            "荒玉で県駅伝切符は何位まで？",
            "荒玉駅伝の県駅伝切符は何位？",
            "荒玉駅伝から県駅伝に行ける順位は？",
            "荒玉駅伝の県駅伝推薦は何位まで？",
            "荒玉駅伝で県に行けるのは上位何校？",
            "荒玉駅伝の上位何校が県駅伝？",
            "荒玉駅伝で県駅伝に出られる学校は何位まで？",
            "荒玉でトップ何校が県駅伝？",
            "荒玉駅伝の県出場枠は何位まで？",
            "荒玉駅伝の県大会出場枠は？",
            "荒玉駅伝で県駅伝出場できる順位は？",
            "荒玉駅伝の県駅伝進出条件を教えて",
            "荒玉駅伝から県駅伝に出る条件は？",
            "荒玉で県駅伝に出るには？",
            "県駅伝に出るには荒玉で何位必要？",
            "県駅伝出場には荒玉で何位以内？",
            "荒玉駅伝2位まで県駅伝って本当？",
            "荒玉は2位まで県駅伝？",
            "荒玉駅伝は2位まで県？",
            "荒玉駅伝2位以内で県駅伝？",
            "荒玉駅伝の2位までが県駅伝出場できる？",
            "荒玉駅伝で2位までに入れば県駅伝？",
            "荒玉で2位取れれば県駅伝出られる？",
            "荒玉駅伝優勝と準優勝は県駅伝に出られる？",
            "荒玉の優勝校と準優勝校は県駅伝？",
            "荒玉駅伝の1位と2位は県駅伝出場？",
            "荒玉駅伝トップ2は県駅伝に出られる？",
            "荒玉駅伝のトップ2が県駅伝？",
            "荒玉駅伝で2位以内＝県駅伝出場？",
            "徹底対策の県駅伝出場圏って何位まで？",
            "荒玉ガイドの県駅伝出場圏は？",
            "4.16の県駅伝出場圏は何位まで？",
            "荒玉駅伝の県駅伝出場圏は2位まで？",
            "荒玉駅伝は何位までが県駅伝に出場できる？",
            "荒玉は何位までが県駅伝に出場できる？",
            "荒玉駅伝は何位までが県駅伝出場できる？",
            "県駅伝に出場できるのは荒玉で上位何校？",
            "荒玉から県駅伝に出られるのは上位何校？",
        ]
    )
    return _dedupe(qs)


def not_3rd_questions() -> list[str]:
    return _dedupe(
        [
            "荒玉駅伝で3位でも県駅伝に出られる？",
            "荒玉で3位は県駅伝出場できる？",
            "荒玉駅伝3位は県駅伝に行ける？",
            "荒玉の3位校は県駅伝に出られる？",
            "荒玉駅伝で3位以内なら県駅伝？",
            "荒玉は3位まで県駅伝？",
            "荒玉駅伝は上位3校が県駅伝？",
            "荒玉で銅メダルでも県駅伝出られる？",
            "荒玉駅伝3位以下は県駅伝に出られる？",
            "荒玉で4位でも県駅伝に出られる？",
            "荒玉駅伝は3位まで出られる？",
            "県駅伝は荒玉3位まで？",
        ]
    )


def gender_questions() -> list[str]:
    return _dedupe(
        [
            "荒玉駅伝の男子も女子も2位まで県駅伝？",
            "荒玉女子も2位まで県駅伝に出られる？",
            "荒玉男子の県駅伝出場は何位まで？",
            "荒玉女子の県駅伝出場は何位まで？",
            "荒玉駅伝男子は何位まで県駅伝？",
            "荒玉駅伝女子は何位まで県駅伝？",
            "男女とも荒玉2位まで県駅伝？",
            "荒玉駅伝の県駅伝枠は男女同じ？",
            "荒玉女子2位は県駅伝に出られる？",
            "荒玉男子2位は県駅伝に出られる？",
        ]
    )


def confirm_questions() -> list[str]:
    return _dedupe(
        [
            "荒玉の県駅伝出場枠は要項で確認が必要？",
            "荒玉駅伝の県駅伝出場権は要項を見るべき？",
            "県駅伝出場枠は大会要項で変わる？",
            "荒玉2位まで県駅伝の根拠は？",
            "徹底対策の2位まで県駅伝は確定？",
            "荒玉の県出場は要項優先？",
            "県駅伝出場圏は毎年同じ？",
            "荒玉駅伝の出場枠はどこで確認する？",
        ]
    )


def line_questions() -> list[str]:
    return _dedupe(
        [
            "荒玉駅伝の2位到達ラインは？",
            "県駅伝出場圏の2位ラインはどのくらい？",
            "荒玉で2位に入る目安タイムは？",
            "荒玉駅伝2位の目安総合タイムは？",
            "県駅伝出場のための2位ペースは？",
            "徹底対策の2位到達ラインを教えて",
            "荒玉男子2位の参考総合は？",
            "荒玉女子2位の参考総合は？",
            "2位を狙う条件は？",
            "荒玉で県駅伝圏内の目安タイムは？",
        ]
    )


def goal_questions() -> list[str]:
    return _dedupe(
        [
            "県駅伝に出たい。荒玉で何位を取ればいい？",
            "県駅伝出場が目標なら荒玉は何位目標？",
            "荒玉駅伝の目標順位は県駅伝なら何位？",
            "県駅伝切符のために荒玉で狙う順位は？",
            "荒玉で県駅伝に行くための最低順位は？",
            "県駅伝出場のための荒玉目標は？",
            "荒玉駅伝は何位以内が目標？（県駅伝）",
            "県に行くなら荒玉は2位以内？",
        ]
    )


def singleton_entries() -> list[dict]:
    """One entry per question for long-tail paraphrases (~100 entries total with clusters)."""
    # Extra long-tail singles that shouldn't collide with core phrasing clusters
    singles = [
        ("q-rank-until", "荒玉駅伝は何位まで県にいける？", CORE_ANSWER),
        ("q-ken-shutsujouken", "荒玉の県出場条件教えて", CORE_ANSWER),
        ("q-ticket", "荒玉駅伝の県切符は上位何位？", CORE_ANSWER),
        ("q-advance", "荒玉から県駅伝に進出できるのは？", CORE_ANSWER),
        ("q-qualify", "荒玉駅伝の県駅伝クオリファイは？", CORE_ANSWER),
        ("q-runner-up-ok", "荒玉で準優勝なら県駅伝OK？", CORE_ANSWER),
        ("q-second-ok", "荒玉で2位でも県駅伝出られるよね？", CORE_ANSWER),
        ("q-ichi-ni", "荒玉の1・2位は県行き？", CORE_ANSWER),
        ("q-yusho-jun", "荒玉は優勝と準優勝だけ県駅伝？", CORE_ANSWER),
        ("q-top2-schools", "荒玉の上位2校が県駅伝？", CORE_ANSWER),
        ("q-ken-eki-nani", "県駅伝に出られる荒玉順位", CORE_ANSWER),
        ("q-ken-frame", "荒玉の県駅伝枠は2？", CORE_ANSWER),
        ("q-two-slots", "荒玉から県駅伝は2枠？", CORE_ANSWER),
        ("q-how-many", "荒玉から何チーム県駅伝に出る？", CORE_ANSWER),
        ("q-suisen", "荒玉の県駅伝推薦枠は？", CORE_ANSWER),
        ("q-area-rep", "荒玉地区代表は何位まで？", CORE_ANSWER),
        ("q-churen", "玉名荒尾の中体連駅伝で県に行ける順位は？", CORE_ANSWER),
        ("q-tamana-arao", "玉名荒尾中体連から県駅伝は何位まで？", CORE_ANSWER),
        ("q-true-false", "荒玉2位まで県駅伝○？", CORE_ANSWER),
        ("q-guide-premise", "徹底対策の前提の出場圏は？", CORE_ANSWER),
    ]
    out: list[dict] = []
    for suffix, q, ans in singles:
        out.append(
            entry(
                f"{ID_PREFIX}{suffix}",
                [q],
                ans,
                SOURCES,
                ["aragyoku", "県駅伝", "出場圏", "2位"],
            )
        )
    return out


def build_entries() -> list[dict]:
    tags = ["aragyoku", "県駅伝", "出場圏", "2位"]
    entries = [
        entry(f"{ID_PREFIX}core", core_questions(), CORE_ANSWER, SOURCES, tags),
        entry(f"{ID_PREFIX}not-3rd", not_3rd_questions(), NOT_3RD_ANSWER, SOURCES, tags + ["3位"]),
        entry(f"{ID_PREFIX}gender", gender_questions(), GENDER_ANSWER, SOURCES, tags + ["男女"]),
        entry(f"{ID_PREFIX}confirm", confirm_questions(), CONFIRM_ANSWER, SOURCES, tags + ["要項"]),
        entry(f"{ID_PREFIX}line", line_questions(), LINE_ANSWER, SOURCES, tags + ["到達ライン"]),
        entry(f"{ID_PREFIX}goal", goal_questions(), GOAL_ANSWER, SOURCES, tags + ["目標"]),
    ]
    entries.extend(singleton_entries())
    return entries


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    new_entries = build_entries()
    n_q = sum(len(e["questions"]) for e in new_entries)
    print(f"generated {len(new_entries)} entries / {n_q} questions")
    assert n_q >= 100, f"need >=100 questions, got {n_q}"
    assert any("2位まで" in e["answer"] for e in new_entries)

    if args.dry_run:
        for e in new_entries:
            print(f"- {e['id']}: {len(e['questions'])}qs | {e['questions'][0]}")
        return 0

    data = load_faq()
    before = len(data["entries"])
    data["entries"] = [
        e for e in data["entries"] if not str(e.get("id", "")).startswith(ID_PREFIX)
    ]
    removed = before - len(data["entries"])
    added, updated = upsert(data["entries"], new_entries)
    save_faq(data)
    print(f"removed stale {removed}; added {added}; updated {updated}; total {len(data['entries'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
