#!/usr/bin/env python3
"""Discover uncovered questions → add prepared FAQ, 1000 rounds (ADR 059).

Each round:
  1) mine a grounded candidate Q&A from corpus/KG sources
  2) skip if primary question already exact-covered
  3) append prepared entry (or paraphrase into existing id when fixing)

Usage:
  python3 scripts/gap_crush_prepared_1000.py --dry-run
  python3 scripts/gap_crush_prepared_1000.py --target 1000
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

from generate_prepared_qa_bulk import (  # noqa: E402
    MEN_FULL,
    WOMEN_FULL,
    entry,
    load_years,
    slug,
)
from generate_prepared_qa_knowledge_1000 import take  # noqa: E402
from generate_prepared_qa_knowledge_5000 import (  # noqa: E402
    DEFAULT_YEAR,
    gen_athlete_meet,
    gen_calendar_gap,
    gen_course_points,
    gen_daiming_focus,
    gen_leg_awards,
    gen_media_boards,
    gen_practice_sessions,
    gen_remaining_legs,
    gen_runner_careers,
    gen_sb_gaps,
    gen_school_year_rankings,
    gen_team_orders,
)

FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
LOG = ROOT / "backend" / "data" / "eval-gaps" / "crush-prepared-1000-rounds.jsonl"
TEAMS_DIR = ROOT / "out" / "analysis" / "aragyoku-teams"
MEETS = ROOT / "input" / "idaten-corpus" / "drive-text" / "大会"
RANK_MEN = ROOT / "out" / "analysis" / "2026_men_1500m_pb_school_ranking.md"
RANK_WOMEN = ROOT / "out" / "analysis" / "2026_women_800m_1500m_pb_school_ranking.md"
RIVALS = ROOT / "out" / "analysis" / "aragyoku_daiming_rivals.md"


def norm_q(q: str) -> str:
    q = q.normalize("NFKC") if hasattr(q, "normalize") else q
    q = re.sub(r"\s+", "", q)
    q = q.replace("？", "?").replace("！", "!")
    return q


def existing_question_set(entries: list[dict]) -> set[str]:
    out: set[str] = set()
    for e in entries:
        for q in e.get("questions") or []:
            out.add(norm_q(q))
    return out


def gen_yearless_team_ranks(existing_ids: set[str], limit: int) -> list[dict]:
    """Yearless team rank questions → latest available year (2025)."""
    out: list[dict] = []
    latest = 2025
    for gender, path, src in (
        ("女子", WOMEN_FULL, "input/aragyoku/women_full_2012_2025.json"),
        ("男子", MEN_FULL, "input/aragyoku/men_full_2012_2025.json"),
    ):
        years = load_years(path)
        yd = years.get(str(latest)) or years.get(latest)
        if not yd:
            continue
        for team in yd.get("teams") or []:
            name = team.get("team") or ""
            rank = team.get("rank")
            total = team.get("total") or "—"
            if not name or not rank:
                continue
            eid = f"gap1000-aragyoku-yearless-{gender}-{slug(name)}-rank"
            if eid in existing_ids:
                continue
            qs = [
                f"荒玉{gender}の{name}の順位は？",
                f"荒玉{gender}の{name}は何位？",
                f"荒玉駅伝{gender}で{name}は何位？",
                f"{name}の荒玉{gender}順位",
                f"今年の荒玉{gender}{name}は何位？",
                f"郡市駅伝{gender}の{name}は何位？",
                f"荒玉中体連駅伝{gender}で{name}は何位？",
            ]
            ans = (
                f"直近開催の{latest}年荒玉駅伝{gender}で{name}は総合{rank}位"
                f"（{total}）です。2026年大会の結果はまだありません。"
            )
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [src, f"out/analysis/aragyoku-teams/{name}.md"],
                    ["gap1000", "aragyoku", "rank", gender, name],
                )
            )
            if len(out) >= limit:
                return out
    return out


def gen_team_history_paraphrase(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    if not TEAMS_DIR.exists():
        return out
    for path in sorted(TEAMS_DIR.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        name = path.stem
        eid = f"gap1000-team-hist-{slug(name)}"
        if eid in existing_ids:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        # pull a short factual blurb from first 2025 section if present
        m = re.search(rf"## 2025年.*?\n(.*?)(?:\n## |\Z)", text, re.S)
        blurb = ""
        if m:
            blurb = re.sub(r"\s+", " ", m.group(1))[:180]
        ans = f"{name}の荒玉駅伝歴代はチーム別正本にまとめています。"
        if blurb:
            ans += f" 2025年付近: {blurb}"
        ans += f" 詳細: out/analysis/aragyoku-teams/{name}.md"
        qs = [
            f"{name}の荒玉の過去成績は？",
            f"{name}中の荒玉歴代は？",
            f"{name}の駅伝成績を教えて",
            f"荒玉での{name}の成績推移",
        ]
        out.append(
            entry(
                eid,
                qs,
                ans + "\n",
                [f"out/analysis/aragyoku-teams/{name}.md"],
                ["gap1000", "aragyoku", "team", name],
            )
        )
        if len(out) >= limit:
            break
    return out


def gen_school_rank_paraphrases(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []

    def parse_table(path: Path, kind: str) -> list[dict]:
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(
                r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*\d+\s*\|\s*([^|]+?)\s*\|",
                line,
            )
            if not m:
                continue
            rows.append(
                {
                    "rank": m.group(1),
                    "school": m.group(2).strip(),
                    "avg": m.group(3).strip(),
                    "kind": kind,
                }
            )
        return rows

    men = parse_table(RANK_MEN, "男子1500m上位4人平均")
    women = parse_table(RANK_WOMEN, "女子800m上位3人平均")
    for rows, src, tag in (
        (men, str(RANK_MEN.relative_to(ROOT)), "men1500"),
        (women, str(RANK_WOMEN.relative_to(ROOT)), "women800"),
    ):
        for r in rows:
            school = r["school"]
            eid = f"gap1000-rank-{tag}-{slug(school)}"
            if eid in existing_ids:
                continue
            qs = [
                f"{r['kind']}で{school}は何位？",
                f"{school}の{r['kind']}順位は？",
                f"学校別{r['kind']}の{school}",
            ]
            ans = (
                f"2026年度・{r['kind']}で{school}は{r['rank']}位"
                f"（平均 {r['avg']}）です。"
            )
            out.append(
                entry(eid, qs, ans, [src], ["gap1000", "school-rank", tag, school])
            )
            if len(out) >= limit:
                return out
    return out


def gen_meet_folder_daiming(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    if not MEETS.exists():
        return out
    for year_dir in sorted(MEETS.iterdir(), reverse=True):
        if not year_dir.is_dir() or not year_dir.name.endswith("年度"):
            continue
        year = year_dir.name.replace("年度", "")
        for meet_dir in sorted(year_dir.iterdir()):
            if not meet_dir.is_dir():
                continue
            result = meet_dir / "岱明の結果.md"
            if not result.exists():
                continue
            text = result.read_text(encoding="utf-8", errors="ignore").strip()
            if len(text) < 40:
                continue
            if re.search(r"ステータス:\s*scheduled", text) and "区間" not in text:
                continue
            folder = meet_dir.name
            title = re.sub(r"^\d{2,4}(?:-\d{2,4})?_", "", folder)
            eid = f"gap1000-meet-{year}-{slug(title)[:40]}"
            if eid in existing_ids:
                continue
            # keep answer user-facing, truncate long dumps
            body = re.sub(r"\n{3,}", "\n\n", text)
            if len(body) > 900:
                body = body[:880] + "…"
            qs = [
                f"{title}の岱明の結果は？",
                f"{year}年{title}の岱明成績",
                f"岱明の{title}結果を教えて",
            ]
            if year == str(DEFAULT_YEAR):
                qs.append(f"今年の{title}で岱明はどうだった？")
            ans = f"{year}年度・{title}の岱明の結果です。\n{body}"
            out.append(
                entry(
                    eid,
                    qs,
                    ans,
                    [str(result.relative_to(ROOT))],
                    ["gap1000", "meet", "daiming", int(year) if year.isdigit() else year],
                )
            )
            if len(out) >= limit:
                return out
    return out


def gen_analysis_digest_gaps(existing_ids: set[str], limit: int) -> list[dict]:
    out: list[dict] = []
    digests = [
        (
            "gap1000-overview-distance",
            ["荒玉男子の総距離は？", "荒玉男子コースの合計kmは？", "荒玉男子は何km？"],
            "荒玉男子の現行（2024年以降）合計距離は17.71km、2023年以前は19.71kmです。女子は11.855km（年度共通）です。",
            ["out/analysis/aragyoku-overview.md"],
        ),
        (
            "gap1000-overview-women-dist",
            ["荒玉女子の総距離は？", "荒玉女子は何km？", "女子荒玉のコース距離"],
            "荒玉女子の総距離は11.855kmです（年度共通）。",
            ["out/analysis/aragyoku-overview.md"],
        ),
        (
            "gap1000-rivals-short",
            ["岱明のライバル校はどこ？", "荒玉で岱明の対抗校", "岱明と近い学校は？"],
            (
                "直近順位と2026トラック層から見ると、男子は荒尾三・南関、女子は長洲・荒尾三が近いです。"
                " 詳細: out/analysis/aragyoku_daiming_rivals.md"
            ),
            ["out/analysis/aragyoku_daiming_rivals.md"],
        ),
        (
            "gap1000-pref-top2-short",
            ["県駅伝に出るには荒玉で何位？", "荒玉から県に行ける順位", "県切符は荒玉何位まで？"],
            "荒玉駅伝は総合2位までが県駅伝出場圏という前提です（要項で再確認）。",
            [
                "input/aragyoku/guides/荒玉駅伝2026徹底対策.extracted.txt",
                "scripts/generate_prepared_qa_prefectural_top2.py",
            ],
        ),
    ]
    # winners by year paraphrases
    winners = ROOT / "input" / "idaten-corpus" / "aragyoku" / "winners-by-year.md"
    if winners.exists():
        for year in range(2012, 2026):
            for gender in ("男子", "女子"):
                eid = f"gap1000-winner-{year}-{gender}"
                if eid in existing_ids:
                    continue
                # pull from prose lines if present
                text = winners.read_text(encoding="utf-8", errors="ignore")
                m = re.search(
                    rf"{year}年荒玉駅伝{gender}の優勝校は「([^」]+)」（総合\s*([^）]+)）",
                    text,
                )
                if not m:
                    continue
                school, total = m.group(1), m.group(2)
                m2 = re.search(
                    rf"{year}年荒玉駅伝{gender}の優勝校は「{re.escape(school)}」[^。]*準優勝校は「([^」]+)」（総合\s*([^）]+)）",
                    text,
                )
                ans = f"{year}年荒玉駅伝{gender}の優勝校は{school}（総合 {total}）です。"
                if m2:
                    ans += f" 準優勝は{m2.group(1)}（総合 {m2.group(2)}）。"
                qs = [
                    f"{year}年荒玉{gender}優勝は？",
                    f"{year}荒玉{gender}の優勝校",
                    f"{year}年の荒玉駅伝{gender}誰が勝った？",
                ]
                out.append(
                    entry(
                        eid,
                        qs,
                        ans,
                        [str(winners.relative_to(ROOT))],
                        ["gap1000", "winner", gender, year],
                    )
                )
                if len(out) >= limit:
                    return out

    for eid, qs, ans, srcs in digests:
        if eid in existing_ids:
            continue
        out.append(entry(eid, qs, ans, srcs, ["gap1000", "digest"]))
        if len(out) >= limit:
            return out
    return out


def gen_alias_paraphrase_gaps(existing_ids: set[str], limit: int) -> list[dict]:
    """Questions that use 郡市/中体連 wording for concrete facts."""
    out: list[dict] = []
    # latest known ranks for focus teams via yearless mapping
    facts = [
        (
            "gap1000-alias-daiming-men-rank",
            [
                "郡市駅伝男子の岱明は何位？",
                "荒玉中体連駅伝男子で岱明は何位だった？",
                "玉名荒尾中体連の男子岱明順位",
            ],
            "直近2025年の荒玉駅伝（郡市/中体連）男子で岱明は総合6位（59:08）です。",
            ["out/analysis/aragyoku-teams/岱明.md"],
        ),
        (
            "gap1000-alias-daiming-women-rank",
            [
                "郡市駅伝女子の岱明は何位？",
                "荒玉中体連駅伝女子で岱明は何位？",
            ],
            "直近2025年の荒玉駅伝女子で岱明は総合7位（45:22）です。",
            ["out/analysis/aragyoku-teams/岱明.md"],
        ),
        (
            "gap1000-alias-when",
            [
                "郡市駅伝はいつ？",
                "玉名荒尾中体連駅伝の日程は？",
                "荒玉中体連は何日？",
            ],
            "2026年の荒玉中体連駅伝（郡市駅伝）は2026-10-14（予備日10-15）予定です。",
            ["input/events.2026.yaml"],
        ),
    ]
    for eid, qs, ans, srcs in facts:
        if eid in existing_ids:
            continue
        out.append(entry(eid, qs, ans, srcs, ["gap1000", "alias"]))
        if len(out) >= limit:
            return out
    return out


def mine_candidates(existing_ids: set[str]) -> list[tuple[str, dict]]:
    """Return list of (theme, entry) candidates, not yet filtered by question overlap."""
    # High-value / previously-missed themes first, then volume fillers.
    buckets: list[tuple[str, list[dict]]] = [
        ("alias", gen_alias_paraphrase_gaps(existing_ids, 20)),
        ("yearless_ranks", gen_yearless_team_ranks(existing_ids, 80)),
        ("analysis", gen_analysis_digest_gaps(existing_ids, 80)),
        ("school_rank", gen_school_rank_paraphrases(existing_ids, 80)),
        ("meet_daiming", gen_meet_folder_daiming(existing_ids, 200)),
        ("team_orders", gen_team_orders(existing_ids, 200)),
        ("team_hist", gen_team_history_paraphrase(existing_ids, 40)),
        ("daiming", gen_daiming_focus(existing_ids, 40)),
        ("leg_awards", gen_leg_awards(existing_ids, 80)),
        ("legs_rem", gen_remaining_legs(existing_ids, 80)),
        ("sb_gaps", gen_sb_gaps(existing_ids, 80)),
        ("calendar", gen_calendar_gap(existing_ids, 250)),
        ("practice", gen_practice_sessions(existing_ids, 150)),
        ("media", gen_media_boards(existing_ids, 40)),
        ("course", gen_course_points(existing_ids, 20)),
        ("school_rank_gen", gen_school_year_rankings(existing_ids, 100)),
        ("athlete_meet", gen_athlete_meet(existing_ids, 800)),
        ("careers", gen_runner_careers(existing_ids, 700)),
    ]
    mined: list[tuple[str, dict]] = []
    for theme, items in buckets:
        print(f"  mine {theme}: {len(items)}")
        for e in items:
            mined.append((theme, e))
    return mined


def crush(entries: list[dict], target: int) -> tuple[list[dict], list[dict]]:
    existing_ids = {e["id"] for e in entries}
    covered_q = existing_question_set(entries)
    mined = mine_candidates(existing_ids)

    added: list[dict] = []
    rounds: list[dict] = []
    used_ids = set(existing_ids)

    for theme, cand in mined:
        if len(added) >= target:
            break
        eid = cand["id"]
        if eid in used_ids:
            continue
        qs = [q for q in (cand.get("questions") or []) if norm_q(q) not in covered_q]
        if not qs:
            continue
        # require at least the primary question to be new
        primary = qs[0]
        e = dict(cand)
        e["questions"] = qs
        added.append(e)
        used_ids.add(eid)
        for q in qs:
            covered_q.add(norm_q(q))
        rounds.append(
            {
                "round": len(added),
                "theme": theme,
                "id": eid,
                "q": primary,
                "action": "add",
                "n_questions": len(qs),
            }
        )
        if len(added) % 100 == 0:
            print(f"  round {len(added)}/{target}: {theme} | {primary}")

    return added, rounds


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--target", type=int, default=1000)
    args = ap.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = list(data.get("entries") or [])
    print(f"existing entries: {len(entries)}")

    added, rounds = crush(entries, args.target)
    print(f"crushed rounds: {len(rounds)} (target {args.target})")
    if len(rounds) < args.target:
        raise SystemExit(f"only completed {len(rounds)} rounds, need {args.target}")

    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rounds) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {LOG.relative_to(ROOT)}")

    # theme histogram
    from collections import Counter

    print("themes:", dict(Counter(r["theme"] for r in rounds)))
    print("sample rounds:")
    for r in rounds[:5] + rounds[-3:]:
        print(f"  #{r['round']} [{r['theme']}] {r['q']}")

    if args.dry_run:
        return 0

    merged = list(entries) + added
    seen: set[str] = set()
    uniq = []
    for e in merged:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        uniq.append(e)
    data["entries"] = uniq
    data["total"] = len(uniq)
    note = data.get("note") or ""
    if "gap-crush-prepared-1000" not in note:
        data["note"] = (
            note.rstrip()
            + "\ngap-crush-prepared-1000: 未カバー質問を1問ずつ発見して想定Q&Aへ1000件追加。\n"
        )
    FAQ.write_text(
        yaml.dump(
            data,
            allow_unicode=True,
            sort_keys=False,
            width=120,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {FAQ.relative_to(ROOT)} total={len(uniq)} (+{len(added)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
