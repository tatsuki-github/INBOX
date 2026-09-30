#!/usr/bin/env python3
"""Polish ALL prepared-qa answers for user-facing quality (ADR 059).

Goals:
  - No repo paths / filename dumps in answer body
  - No ops jargon (状態:, ADR, 正本パス, 出典: out/...)
  - No raw markdown table dumps; keep short factual prose + https URLs
  - Cap runaway answers (careers / analysis / team digests)
  - Touch every entry (normalize whitespace / ending)

Usage:
  python3 scripts/polish_prepared_qa_quality.py --dry-run
  python3 scripts/polish_prepared_qa_quality.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / "input" / "faq" / "prepared-qa.v1.yaml"
REPORT = ROOT / "backend" / "data" / "eval-gaps" / "prepared-qa-quality-polish.jsonl"
TRIAL_JSON = ROOT / "out" / "analysis" / "2026-09-29_aragyoku_trial_results.json"

URL_RE = re.compile(r"https?://[^\s）)\]]+")
PATH_RE = re.compile(
    r"(?:`)?(?:input|out|docs|scripts|backend|work)/[^\s`。、）)\]]+(?:`)?"
)
FILE_RE = re.compile(
    r"`?[A-Za-z0-9_./\-一-龥]+?\.(?:md|yaml|yml|json|csv|txt|py|html)`?"
)
SOURCE_TAIL_RE = re.compile(
    r"(?:出典|詳細テキスト|索引)\s*[:：]\s*[^\n。]*"
)
STATUS_RE = re.compile(r"\s*状態:\s*\w+。?")
JARGON_RE = re.compile(
    r"\b(?:ADR\s*\d*|RAG|LLM|YAML|JSON|KG|coverage\.csv)\b"
)
MD_HEADING_RE = re.compile(r"#{1,6}\s+")
# inline or line tables: sequences of | cells
MD_TABLE_INLINE_RE = re.compile(r"(?:\|[^\n|]*){2,}\|?")
MD_TABLE_SEP_RE = re.compile(r"\|?\s*:?-{3,}(?:\s*\|+\s*:?-{3,})+\|?")
SEIHON_RE = re.compile(
    r"(?:チーム別)?正本に(?:あります|まとめています)[。．]?|"
    r"[をの]?正本とします[。．）)]*|"
    r"正本は\s*[^\s。]*?\s*です[。．]?|"
    r"[がを]\s*正本です[。．]?|"
    r"正本\s*ID[^\n。]*[。．]?|"
    r"正本\s*[:：]\s*[^\n。]+|"
    r"チーム正本|"
    r"詳細は\s*[。．]"
)


def extract_urls(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in URL_RE.finditer(text or ""):
        u = m.group(0).rstrip("。、,")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def extract_named_times(text: str, limit: int = 12) -> list[str]:
    """Pull 'Name … mm:ss' facts from dumps before tables are stripped."""
    out: list[str] = []
    seen: set[str] = set()

    # Pipe rows: | 1区 | 3km | 松野凛空 | laps | 9:48 |
    for m in re.finditer(
        r"\|\s*(\d+区)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|[^|]*\|\s*(\d{1,2}:\d{2}(?:\.\d+)?)\s*\|",
        text,
    ):
        leg, _km, name, mark = m.group(1), m.group(2), m.group(3).strip(), m.group(4)
        name = re.sub(r"\s+", "", name)
        if not name or name in {"選手", "名前"}:
            continue
        key = f"{leg}:{name}:{mark}"
        if key in seen:
            continue
        seen.add(key)
        out.append(f"{leg}{name} {mark}")
        if len(out) >= limit:
            return out

    for m in re.finditer(
        r"([一-龥々ぁ-んァ-ンA-Za-z]{2,16})"
        r"(?:（[^）]{0,20}）)?"
        r"[^\n|。]{0,24}?"
        r"(\d{1,2}:\d{2}(?:\.\d+)?)",
        text,
    ):
        name, mark = m.group(1), m.group(2)
        if name in {"区間", "総合", "順位", "記録", "日付", "距離", "ラップ", "選手"}:
            continue
        key = f"{name}:{mark}"
        if key in seen:
            continue
        seen.add(key)
        out.append(f"{name} {mark}")
        if len(out) >= limit:
            break
    return out


def strip_markdown_tables(text: str) -> str:
    t = MD_TABLE_SEP_RE.sub(" ", text)
    t = MD_TABLE_INLINE_RE.sub(" ", t)
    return t


def clean_jargon(text: str) -> str:
    t = text
    t = STATUS_RE.sub(" ", t)
    t = SOURCE_TAIL_RE.sub("", t)
    t = PATH_RE.sub("", t)
    # drop bare filename refs that look like repo artifacts (keep meet names)
    def _file_sub(m: re.Match[str]) -> str:
        s = m.group(0)
        if s.startswith("http"):
            return s
        # keep Japanese meet-ish names without path; drop analysis artifacts
        if any(
            x in s
            for x in (
                "aragyoku_",
                "notion_records",
                "coverage",
                "formula_",
                "prepared-qa",
                "events.",
                "knowledge-graph",
                "leg_awards",
                "focus_teams",
            )
        ):
            return ""
        if s.endswith((".yaml", ".yml", ".json", ".csv", ".py", ".html")):
            return ""
        if s.endswith(".md"):
            return ""
        return s

    t = FILE_RE.sub(_file_sub, t)
    t = SEIHON_RE.sub("", t)
    t = JARGON_RE.sub("", t)
    t = MD_HEADING_RE.sub("", t)
    t = strip_markdown_tables(t)
    t = re.sub(r"`[^`]+`", " ", t)
    t = re.sub(r"[（(]\s*[）)]", "", t)
    t = re.sub(r"詳細は\s*です。?", "", t)
    t = re.sub(r"概要:\s*", "", t)
    t = re.sub(r"（以降の区も[。．）)]*", "", t)
    t = re.sub(r"を見てください。?", "", t)
    # spaced slash used as a separator (keep 2026/04/29 and URLs intact)
    t = re.sub(r"\s+/\s+", " ", t)
    t = re.sub(r"。{2,}", "。", t)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\s+([。．])", r"\1", t)
    return t.strip(" 　")


def soft_trim(text: str, max_len: int) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    # prefer cut at sentence
    cut = text[: max_len - 1]
    for sep in ("。", "\n", "／", " "):
        i = cut.rfind(sep)
        if i >= int(max_len * 0.55):
            cut = cut[: i + (1 if sep == "。" else 0)]
            break
    cut = cut.rstrip("、・/ ")
    if not cut.endswith(("。", "…", "\n")):
        cut += "…"
    return cut


def polish_career(answer: str) -> str:
    """Keep lead + first few races; drop giant unknown dumps."""
    urls = extract_urls(answer)
    lines = [ln.strip() for ln in answer.splitlines() if ln.strip()]
    if not lines:
        return answer
    lead = clean_jargon(lines[0])
    # unknown mega-dump → short
    if "unknown" in lead.lower() or re.search(r"出走歴は\d{3,}回", lead):
        return "所属不明（unknown）として集計された区間記録があります。選手名が分かれば名前で聞いてください。"
    races = []
    for ln in lines[1:]:
        if re.search(r"\d{4}年|区|総合", ln):
            races.append(clean_jargon(ln))
        if len(races) >= 6:
            break
    parts = [lead if lead.endswith("。") else lead + "。"]
    if races:
        parts.append("主な出走: " + " ／ ".join(races[:6]))
        if len(lines) > 8:
            parts.append("他の出走もあります。")
    body = " ".join(parts)
    if urls:
        # careers rarely need urls; skip
        pass
    return soft_trim(body, 520)


def polish_records_athlete(answer: str) -> str:
    """Keep summary + race lines with meet URLs (tests depend on them)."""
    lines = [ln.rstrip() for ln in answer.splitlines()]
    if not lines:
        return answer
    out_lines = [clean_jargon(lines[0])]
    kept = 0
    for ln in lines[1:]:
        if not ln.strip():
            continue
        # keep race / 大会結果 lines
        if "大会結果:" in ln or re.search(r"\d{4}/\d{2}/\d{2}", ln) or "駅伝" in ln:
            # do not strip URLs
            cleaned = STATUS_RE.sub(" ", ln)
            cleaned = PATH_RE.sub("", cleaned)
            cleaned = SOURCE_TAIL_RE.sub("", cleaned)
            out_lines.append(cleaned.strip())
            kept += 1
        if kept >= 14:
            break
    body = "\n".join(out_lines).strip()
    if len(answer.splitlines()) > len(out_lines) + 2:
        body += "\n（他の記録もあります）"
    return soft_trim(body, 1400)


def polish_analysis_or_digest(answer: str, *, max_len: int = 360) -> str:
    urls = extract_urls(answer)
    facts = extract_named_times(answer, limit=10)
    t = answer
    t = re.sub(r"^分析ドキュメント「([^」]+)」:\s*", r"\1。", t)
    t = re.sub(r"^練習資料「([^」]+)」:\s*", r"\1。", t)
    title = ""
    tm = re.match(r"^([^。\n]{6,60})", t.strip())
    if tm:
        title = re.sub(r"^分析ドキュメント「([^」]+)」:\s*", r"\1", tm.group(1))
        title = MD_HEADING_RE.sub("", title).strip(" ：:")
    t = clean_jargon(t)
    t = re.sub(r"\s+", " ", t).strip()
    # If cleanup wiped the substance, rebuild from title + extracted facts
    if facts and (
        len(re.sub(r"[\s\W]+", "", t)) < 24
        or t.endswith("／。")
        or t.endswith("／")
        or re.search(r"日付:\s*20\d{2}-\d{2}-\d{2}\s*／?。?$", t)
    ):
        head = title or "要点"
        t = head.rstrip("。") + "。 " + "、".join(facts) + "。"
    elif facts and not any(f.split()[-1] in t for f in facts[:3]):
        t = soft_trim(t, max(120, max_len - 80))
        t = t.rstrip("。…") + "。 " + "、".join(facts[:8]) + "。"
    t = soft_trim(t, max_len)
    for u in urls[:3]:
        if u not in t:
            t = t.rstrip("…。") + "。 資料: " + u
    if t and not t.endswith(("。", "…")):
        t += "。"
    return t


def polish_notion(answer: str) -> str:
    t = re.sub(r"。?\s*出典:\s*\S+\s*$", "。", answer.strip())
    t = clean_jargon(t)
    if not t.endswith("。"):
        t += "。"
    return t


def scrub_remaining_seihon(text: str) -> str:
    """Last-pass: user-facing synonyms for leftover 正本 jargon."""
    t = text
    repl = (
        ("正本フォルダ", "資料フォルダ"),
        ("正本結果表", "結果表"),
        ("年度別正本", "年度別結果"),
        ("学校別正本", "学校別データ"),
        ("正本JSON", "データ"),
        ("既存分析ファイル", "分析資料"),
        ("を正本としたか", "を根拠にしたか"),
        ("チーム正本", "チーム結果"),
        ("チーム別正本にまとめています。", "チーム別の歴代成績です。"),
        ("詳細:。", ""),
    )
    for a, b in repl:
        t = t.replace(a, b)
    t = re.sub(r"「[^」]*」の正本。?", "", t)
    t = re.sub(r"正本は[^\n。]*。?", "", t)
    t = re.sub(r"が正本です。?", "です。", t)
    t = re.sub(r"結果・成績の質問で正本PDFがある場合", "結果・成績の質問でPDFがある場合", t)
    # leftover bare 正本 (not in 徹底対策 page titles about methodology chunks)
    t = re.sub(r"(?<![一-龥])正本(?![一-龥])", "根拠資料", t)
    t = re.sub(r"。{2,}", "。", t)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip()


def polish_trial_analysis(_answer: str) -> str:
    if not TRIAL_JSON.exists():
        return "2026年9月29日の岱明・荒玉試走結果です。"
    data = json.loads(TRIAL_JSON.read_text(encoding="utf-8"))
    bits = []
    for rec in data.get("records") or []:
        leg = rec.get("leg")
        name = rec.get("name") or rec.get("reported_name")
        t = rec.get("time")
        if leg and name and t:
            bits.append(f"{leg}区{name} {t}")
    body = "2026年9月29日の岱明・荒玉試走結果です。"
    if bits:
        body += " " + "、".join(bits) + "。"
    return body


def polish_generic(answer: str, eid: str) -> str:
    urls = extract_urls(answer)
    original = answer
    # Preserve multiline structure when URLs / 大会結果 lines matter
    if "大会結果:" in answer or eid.startswith(("sb-", "records-", "race-")):
        lines = []
        for ln in original.splitlines():
            if not ln.strip():
                lines.append("")
                continue
            if "大会結果:" in ln or URL_RE.search(ln):
                cleaned = STATUS_RE.sub("", ln)
                cleaned = PATH_RE.sub("", cleaned)
                cleaned = SOURCE_TAIL_RE.sub("", cleaned)
                lines.append(cleaned.rstrip())
            else:
                lines.append(clean_jargon(ln))
        t = "\n".join(lines)
        t = re.sub(r"\n{3,}", "\n\n", t).strip()
        # re-attach missing urls
        for u in urls:
            if u not in t:
                t += f"\n大会結果: {u}"
        return t

    t = clean_jargon(answer)
    t = re.sub(r"\s+", " ", t).strip()
    # restore urls lost by cleanup
    for u in urls:
        if u not in t:
            t = t.rstrip("。") + f"。 資料: {u}"
    if len(t) > 700 and not eid.startswith(("aragyoku-pref-", "guide-", "trial-")):
        t = soft_trim(t, 700)
    if t and not t.endswith(("。", "…", "!", "！", "?", "？")) and "http" not in t[-40:]:
        t += "。"
    return t


def polish_entry(entry: dict) -> tuple[str, str]:
    """Return (action, new_answer). action in touch|rewrite|keep-normalize."""
    eid = entry.get("id") or ""
    ans = entry.get("answer") or ""
    before = ans

    # intentional meta entry
    if eid == "coach-fallback-meaning":
        new = ans.strip() + ("\n" if not ans.endswith("\n") else "")
        return ("normalize", new)

    if eid == "analysis-2026-09-29_aragyoku_trial_results":
        new = polish_trial_analysis(ans)
    elif eid.startswith("aragyoku-career-"):
        new = polish_career(ans)
    elif eid.startswith("records-athlete-"):
        new = polish_records_athlete(ans)
    elif eid.startswith("gap1000b-notion-"):
        new = polish_notion(ans)
    elif eid.startswith(("gap1000b-arato-", "gap1000b-year-", "gap1000-team-hist-")):
        new = polish_analysis_or_digest(ans, max_len=300)
    elif eid.startswith(("analysis-", "practice-doc-", "meet-doc-", "guide-chunk-")):
        new = polish_analysis_or_digest(ans, max_len=420)
    elif eid.startswith("gap1000-meet-"):
        # meet daiming dumps — keep lead facts, trim
        new = polish_analysis_or_digest(ans, max_len=700)
    else:
        new = polish_generic(ans, eid)

    new = scrub_remaining_seihon(new)
    if new and not new.endswith(("。", "…", "\n")) and "http" not in new[-48:]:
        new += "。"
    new = new.strip() + "\n"
    if new != before:
        # substantive if jargon/path removed or length changed a lot
        if (
            PATH_RE.search(before)
            or SOURCE_TAIL_RE.search(before)
            or "正本" in before
            or "##" in before
            or abs(len(new) - len(before)) > 40
        ):
            return ("rewrite", new)
        return ("normalize", new)
    return ("unchanged", before if before.endswith("\n") else before + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = list(data.get("entries") or [])
    print(f"entries: {len(entries)}")

    counts = {"rewrite": 0, "normalize": 0, "unchanged": 0}
    report_rows: list[dict] = []

    for e in entries:
        before = e.get("answer") or ""
        action, new = polish_entry(e)
        # Universal light pass on every answer
        new2 = scrub_remaining_seihon(new)
        new2 = STATUS_RE.sub(" ", new2)
        new2 = PATH_RE.sub("", new2)
        new2 = re.sub(r"。{2,}", "。", new2)
        new2 = re.sub(r"[ \t]+\n", "\n", new2).strip() + "\n"
        if new2 != before:
            if action == "unchanged":
                action = "normalize"
            e["answer"] = new2
            report_rows.append(
                {
                    "id": e.get("id"),
                    "action": action,
                    "before_len": len(before),
                    "after_len": len(new2),
                }
            )
        else:
            e["answer"] = before if before.endswith("\n") else before + "\n"
            if e["answer"] != before:
                action = "normalize"
                report_rows.append(
                    {
                        "id": e.get("id"),
                        "action": action,
                        "before_len": len(before),
                        "after_len": len(e["answer"]),
                    }
                )
        counts[action] = counts.get(action, 0) + 1

    print("counts:", counts)
    print(f"touched: {counts['rewrite'] + counts['normalize']} / {len(entries)}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in report_rows) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {REPORT.relative_to(ROOT)} ({len(report_rows)} rows)")

    # smell re-check
    smells = {
        "path": 0,
        "source_out": 0,
        "seihon": 0,
        "status": 0,
        "md_table": 0,
    }
    for e in entries:
        a = e.get("answer") or ""
        if PATH_RE.search(a):
            smells["path"] += 1
        if re.search(r"出典:\s*(?:out/|input/|`)", a):
            smells["source_out"] += 1
        if "正本" in a:
            smells["seihon"] += 1
        if "状態:" in a:
            smells["status"] += 1
        if MD_TABLE_INLINE_RE.search(a) or "|" in a and "---" in a:
            smells["md_table"] += 1
    print("remaining smells:", smells)

    # samples
    for eid in (
        "gap1000b-notion-三原悠愛-1500m",
        "gap1000b-arato-ATRC",
        "gap1000b-year-2025",
        "aragyoku-pref-top2-core",
        "aragyoku-focus-four",
        "analysis-2026-09-29_aragyoku_trial_results",
    ):
        e = next((x for x in entries if x["id"] == eid), None)
        if e:
            print("---", eid)
            print(e["answer"][:220].replace("\n", " | "))

    if args.dry_run:
        return 0

    data["entries"] = entries
    data["total"] = len(entries)
    note = data.get("note") or ""
    if "polish-prepared-qa-quality" not in note:
        data["note"] = (
            note.rstrip()
            + "\npolish-prepared-qa-quality: 全想定Q&Aの回答をユーザー向けに品質改修"
            "（パス/正本/出典ダンプ除去・長文圧縮）。\n"
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
    print(f"wrote {FAQ.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
