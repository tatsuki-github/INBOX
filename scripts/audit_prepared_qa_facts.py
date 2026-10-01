#!/usr/bin/env python3
"""Recheck every prepared answer against its source snapshot.

Source-derived entries: compare numeric claims and dated race tuples with fresh
source projections. Other prose: check referenced files and literal time claims.
This is NOT a proof of every natural-language assertion or of external results.
The report records the check level for every entry; unsupported claims fail.

Run --fix to refresh the families with corrected extraction/scope semantics, then
sync_prepared_qa.py. Run --check in CI to detect source/answer drift.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import inspect
import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / "input/faq/prepared-qa.v1.yaml"
REPORT = ROOT / "backend/data/eval-gaps/prepared-qa-factual-audit.json"
URL_RE = re.compile(r"https?://[^\s]+")
CLOCK_RE = re.compile(r"(?<![\d:])(?:\d{1,2}:)?\d{1,2}:\d{2}(?:\.\d+)?(?![\d:])")
MODULES = (
    "generate_prepared_qa_bulk", "generate_prepared_qa_knowledge_1000",
    "generate_prepared_qa_knowledge_3000", "generate_prepared_qa_knowledge_5000",
    "generate_prepared_qa_aragyoku_3000", "gap_crush_prepared_1000",
)


def clock_value(mark: str) -> str:
    parts = mark.split(":")
    value = sum(float(p) * 60 ** i for i, p in enumerate(reversed(parts)))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def clean_for_facts(text: str) -> str:
    text = URL_RE.sub("", text)
    return re.sub(r"(?:input|out|docs|scripts|backend)/[^\s。]+", "", text)


def clocks(text: str) -> set[str]:
    text = clean_for_facts(text)
    text = re.sub(r"(\d+)分(\d+)秒(\d+)?", lambda m: f"{m[1]}:{int(m[2]):02d}" +
                  (f".{m[3]}" if m[3] else ""), text)
    return {clock_value(m[0]) for m in CLOCK_RE.finditer(text)}


def asserted_clocks(text: str) -> set[str]:
    # Quoted sample questions are inputs, not asserted race/pace results.
    text = re.sub(r"「[^」]+」(?=のように)", "", text)
    return clocks(text)


def numeric_claims(text: str) -> set[str]:
    text = clean_for_facts(text)
    result = {"time:" + c for c in clocks(text)}
    text = CLOCK_RE.sub("", text)
    result.update(re.findall(r"\d+(?:\.\d+)?(?:km|m|位|件|回|区|年)", text))
    result.update(re.findall(r"20\d{2}[/-]\d{2}[/-]\d{2}", text.replace("/", "-")))
    return result


def race_tuples(text: str) -> set[tuple[str, str, str]]:
    # Preserve date/event/result association: a time merely occurring somewhere
    # in a CSV must not validate a different athlete/date/event's answer.
    return {
        (m[1].replace("-", "/"), m[2], clock_value(m[3]))
        for m in re.finditer(
            r"(20\d{2}[/-]\d{2}[/-]\d{2})\s+(\d+(?:\.\d+)?m|\d+区(?:[\d.]+km)?)\s+"
            r"((?:\d{1,2}:)?\d{1,2}:\d{2}(?:\.\d+)?)", text
        )
    }


@lru_cache(maxsize=None)
def source_text(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file() or path.suffix not in {".json", ".md", ".csv", ".yaml", ".yml", ".txt", ".ts", ".py"}:
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


@lru_cache(maxsize=None)
def source_clocks(rel: str) -> frozenset[str]:
    return frozenset(clocks(source_text(rel)))


def source_projection() -> dict[str, dict]:
    """Read-only projections. Never call generator main() or mutate the FAQ."""
    out: dict[str, dict] = {}
    for module_name in MODULES:
        module = importlib.import_module(module_name)
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if fn.__module__ != module_name or not name.startswith("gen_"):
                continue
            params = inspect.signature(fn).parameters
            if not set(params).issubset({"existing_ids", "limit"}):
                continue
            # Static workflow/help text is not factual evidence.
            if name in {"gen_meta_paraphrases", "gen_knowledge_seeds", "gen_topic_extras", "gen_guide_qa"}:
                continue
            kwargs = {"existing_ids": set()}
            if "limit" in params:
                kwargs["limit"] = 100000
            for e in fn(**kwargs):
                out.setdefault(e["id"], e)

    sb = importlib.import_module("generate_aragyoku_athlete_sb_qa")
    for year in range(sb.YEAR_START, sb.YEAR_END + 1):
        for e in sb.build_entries_for_year(year, sb.load_year_records(year, sb.load_keywords())):
            out[e["id"]] = e
    records = importlib.import_module("generate_prepared_qa_athlete_all_records")
    for e in records.gen_entries(set(), replace=True):
        out[e["id"]] = e
    for module_name, function in (
        ("generate_prepared_qa_aragyoku_rank_gaps", "gen_entries"),
        ("generate_prepared_qa_school_rosters", "gen_entries"),
        ("generate_prepared_qa_daiming_rivals", "build_entries"),
        ("generate_prepared_qa_prefectural_top2", "build_entries"),
        ("generate_prepared_qa_aragyoku_pass_rank", "gen_entries"),
        ("generate_prepared_qa_aragyoku_leg_time_rank", "gen_entries"),
        ("generate_prepared_qa_aragyoku_rank_benchmark", "gen_entries"),
    ):
        for e in getattr(importlib.import_module(module_name), function)():
            out[e["id"]] = e
    course = importlib.import_module("generate_prepared_qa_course_points")
    for e in course.build_entries(json.loads(course.COURSE_JSON.read_text())):
        out[e["id"]] = e
    nagomi = importlib.import_module("generate_prepared_qa_nagomi_team_results")
    for year in nagomi.MEET_DIRS:
        for e in nagomi.collect_year(year):
            out[e["id"]] = e
    # Shared slug collisions have explicit calx IDs in the stored catalog.
    for e in list(out.values()):
        if e["id"].startswith("cal-"):
            out.setdefault(e["id"].replace("cal-", "calx-", 1), e)
    # A derived average pace is checked by arithmetic, not by looking for the
    # resulting number as a literal in a distance definition document.
    men = json.loads((ROOT / "input/aragyoku/men_full_2012_2025.json").read_text())
    winner = next(t for t in men["years"]["2025"]["teams"] if t["rank"] == 1)
    distances = []
    active = False
    for line in source_text("docs/aragyoku-ekiden-distance-definitions.md").splitlines():
        if line.startswith("### "):
            active = line == "### 2024年以降"
        elif line.startswith("## 女子"):
            active = False
        if active:
            match = re.match(r"\|\s*\d+区\s*\|\s*([\d.]+)km", line)
            if match:
                distances.append(float(match[1]))
    if len(distances) != 6:
        raise ValueError("Expected six source-backed men's course distances")
    distance = sum(distances)
    pace = round(float(clock_value(winner["total"])) / distance)
    answer = (f"2025年荒玉駅伝男子優勝・{winner['team']}は総合{winner['total']}、"
              f"総距離{distance:g}kmです。平均ペースは約{pace // 60}:{pace % 60:02d}/kmです。")
    out["aragyoku-winner-pace"] = {"answer": answer, "sources": [
        "input/aragyoku/men_full_2012_2025.json", "docs/aragyoku-ekiden-distance-definitions.md"]}
    # Calendar descriptions can be cut inside a clock ("1:05:1…"). Build this
    # result summary from the same team rows instead of that truncated dump.
    bits = []
    result_sources = ["input/events.2025.yaml"]
    for gender, filename in (("男子", "men"), ("女子", "women")):
        rel = f"input/aragyoku/{filename}_full_2012_2025.json"
        data = json.loads(source_text(rel))["years"]["2025"]
        team = next(t for t in data["teams"] if t["team"] == "岱明")
        bits.append(f"{gender}は総合{team['rank']}位・{team['total']}")
        result_sources.append(rel)
    out["cal-2025-20251015-玉名荒尾中体連駅伝大会"] = {
        "answer": "玉名荒尾中体連駅伝大会は2025-10-15に実施済みです。岱明の結果は、" + "、".join(bits) + "です。",
        "sources": result_sources,
    }
    return out


def check_entry(e: dict, projected: dict | None) -> dict:
    problems: list[str] = []
    sources = e.get("sources") or []
    for s in sources:
        if not (ROOT / s).exists():
            problems.append("missing_source:" + s)
    # Do not use the FAQ itself as evidence for its own claims.
    evidence_times = set().union(*(source_clocks(s) for s in sources if "prepared-qa" not in s))
    answer = e.get("answer") or ""
    if re.search(r"\b(?:mimeType|fileSize|parentId|modifiedTime)\b", answer):
        problems.append("drive_metadata_leak")
    # Hollow answers after path/link stripping no longer address the question.
    if "「」" in answer or re.search(r"詳細表は\s*です", answer):
        problems.append("hollow_answer_template")
    if re.search(r"(?:平均|ランキング|一覧|接続|付属)は\s*。", answer):
        problems.append("hollow_answer_fact")
    if re.search(r"および\s*の[なごじ]", answer) or (
        "[]" in answer and re.search(r"より。|他校は\s*\[\]", answer)
    ):
        problems.append("hollow_answer_link_strip")
    mode = "source_text_time_check"
    if projected:
        mode = "source_projection_claim_check"
        extra = numeric_claims(answer) - numeric_claims(projected["answer"])
        # Excerpts can differ in length. Inspect the complete reference, not just
        # a regenerated excerpt, before calling a longer answer a mismatch.
        unsupported_times = {c for c in extra if c.startswith("time:") and c[5:] not in evidence_times}
        problems.extend("unsupported_claim:" + c for c in sorted(unsupported_times))
        if re.match(r"^(?:sb-20\d{2}-|race-|rank-school-|aragyoku-20\d{2}-|gap1000b-rank-|gap1000-rank-)", e["id"]):
            problems.extend("numeric_projection_mismatch:" + c for c in sorted(extra))
        identity_patterns = (r"^([^（\n]+)（", r"区は([^（\n]+)（", r"(?:区間賞|区間\d+位)は([^（\n]+)（") if re.match(
            r"^(?:sb-20\d{2}-|race-|records-athlete-|aragyoku-20\d{2}-)", e["id"]
        ) else ()
        for pattern in identity_patterns:
            actual = re.search(pattern, answer)
            expected = re.search(pattern, projected["answer"])
            if actual and expected and re.sub(r"\s+", "", actual[1]) != re.sub(r"\s+", "", expected[1]):
                problems.append("identity_projection_mismatch:" + actual[1])
        if e["id"].startswith(("race-", "records-athlete-", "recent-")):
            wrong = race_tuples(answer) - race_tuples(projected["answer"])
            problems.extend("wrong_race_tuple:" + repr(t) for t in sorted(wrong))
        # Projections refreshed by --fix must match exactly, including the
        # identity and counts; these cannot be validated by loose token overlap.
        if refresh_family(e["id"]) and answer.strip() != projected["answer"].strip():
            problems.append("source_projection_drift")
    else:
        unsupported = asserted_clocks(answer) - evidence_times
        problems.extend("unsupported_time:" + t for t in sorted(unsupported))
    # Short meet aliases must not claim a different real meet (e.g. 天草→玉名郡).
    if e["id"].startswith(("race-", "recent-")) and "ナイター" in e["id"]:
        meet_m = re.search(r"大会名:\s*([^）\n]+)", answer)
        if meet_m and "玉名郡ナイター" in e["id"] and "玉名郡" not in meet_m.group(1):
            problems.append("nighter_meet_alias_mismatch:" + meet_m.group(1).strip())
        if "玉名郡ナイター" in answer and re.search(
            r"大会名:\s*[^）\n]*(?:天草|ナイター記録会)", answer
        ) and "玉名郡" not in (meet_m.group(1) if meet_m else ""):
            problems.append("nighter_meet_alias_mismatch_prose")
        if e["id"].startswith("recent-") and "玉名郡ナイター" in e["id"]:
            if "jaaf-nagasaki" in answer or "amakusa" in answer.lower() or "天草" in answer:
                problems.append("nighter_meet_alias_mismatch_recent")
    return {"id": e["id"], "check": mode, "problems": problems}


def refresh_family(eid: str) -> bool:
    return (
        eid.startswith(("records-athlete-", "records-team-"))
        or bool(re.match(r"^sb-20\d{2}-", eid))
        or bool(re.match(r"^formula-2026-.*-order$", eid))
        or eid == "aragyoku-winner-pace"
        or eid == "cal-2025-20251015-玉名荒尾中体連駅伝大会"
    )


def apply_source_fixes(entries: list[dict], projected: dict[str, dict]) -> list[dict]:
    changes: list[dict] = []
    for e in entries:
        before = json.loads(json.dumps(e, ensure_ascii=False))
        fresh = projected.get(e["id"])
        if fresh and refresh_family(e["id"]):
            e["answer"] = fresh["answer"].strip() + "\n"
            e["sources"] = fresh["sources"]
        if fresh and re.match(r"^race-202[45]-", e["id"]):
            # Old annual results must not advertise themselves as this year's.
            year = e["id"].split("-")[1]
            e["questions"] = [q if re.search(r"20\d{2}", q) else f"{year}年{q}" for q in e["questions"]]
        if e["id"].startswith("gap1000-aragyoku-yearless-"):
            e["questions"] = [q for q in e["questions"] if "今年" not in q]
        if e["id"] == "aragyoku-2025-men-meet-record":
            rel = "input/aragyoku/men_full_2012_2025.json"
            if rel not in e["sources"]:
                e["sources"].append(rel)
        if e != before:
            changes.append({"id": e["id"], "before": before, "after": json.loads(json.dumps(e, ensure_ascii=False))})
    return changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--report", type=Path, default=REPORT)
    args = ap.parse_args()
    if args.fix and args.check:
        ap.error("--fix and --check are mutually exclusive")
    data = yaml.safe_load(FAQ.read_text())
    entries = data["entries"]
    projected = source_projection()
    changes = apply_source_fixes(entries, projected) if args.fix else []
    if args.fix:
        data["total"] = len(entries)
        FAQ.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120))
        log = REPORT.with_name("prepared-qa-factual-corrections.jsonl")
        if changes:
            with log.open("a") as stream:
                for change in changes:
                    before, after = change["before"], change["after"]
                    digest = lambda row: hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                    stream.write(json.dumps({"id": change["id"],
                        "changed_fields": sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k)),
                        "before_sha256": digest(before), "after_sha256": digest(after),
                        "sources": after["sources"]}, ensure_ascii=False) + "\n")
    rows = [check_entry(e, projected.get(e["id"])) for e in entries]
    paths = sorted({s for e in entries for s in e["sources"]})
    report = {
        "catalog_sha256": hashlib.sha256(FAQ.read_bytes()).hexdigest(),
        "total": len(entries),
        "checks": dict(Counter(r["check"] for r in rows)),
        "entries_with_problems": sum(bool(r["problems"]) for r in rows),
        "limitations": ["Checks repository snapshots, not external live results.",
                        "Source projections are generated from data; regression fixtures independently check known extraction errors.",
                        "Text time checks establish literal support, not every prose assertion or identity association."],
        "sources": {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest()
                    for s in paths if (ROOT / s).is_file()},
        "entries": rows,
    }
    if not args.check:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("total", "checks", "entries_with_problems")}, ensure_ascii=False))
    for r in rows:
        if r["problems"]:
            print(json.dumps(r, ensure_ascii=False))
    return 1 if report["entries_with_problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
