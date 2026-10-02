#!/usr/bin/env python3
"""Draft unreviewed candidates for chunks not covered by schema generators.

Reads pending chunks from out/qa-chunks, writes candidate JSON under
out/qa-candidates/. Does not publish or certify review; candidates require contextual review before promotion.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/qa-chunks"
BATCH_DIR = ROOT / "input/faq/full-knowledge-qa"
CANDIDATE_DIR = ROOT / "out/qa-candidates"
PREPARED = ROOT / "backend/data/prepared-qa.json"

PATH_IN_ANSWER = re.compile(
    r"(?:`?(?:input|out|docs|scripts|backend)/[^\s`]+`?|"
    r"\[[^\]]+\]\([^)]*(?:input|out|docs|scripts)/[^)]+\))"
)
BULLET_KV = re.compile(r"^[-*]\s+\*\*([^*]+)\*\*[:\s]+(.+)$")
HEADING = re.compile(r"^#{1,6}\s+(.+)$")


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s)


def normalize_question_key(q: str) -> str:
    q = nfkc(q.strip())
    q = re.sub(r"[?？!！。．、,，・]", "", q)
    q = re.sub(r"(を)?(教えて|見せて|知りたい|ください|下さい|お願い|ですか|でしょうか)+$", "", q)
    return re.sub(r"\s+", "", q)


def load_existing_keys() -> set[str]:
    keys: set[str] = set()
    if PREPARED.is_file():
        for e in json.loads(PREPARED.read_text()).get("entries", []):
            for q in e.get("questions", []):
                keys.add(normalize_question_key(q))
    for p in BATCH_DIR.glob("*.json"):
        if p.name == "progress.json":
            continue
        for e in json.loads(p.read_text()).get("entries", []):
            for q in e.get("questions", []):
                keys.add(normalize_question_key(q))
    carry = BATCH_DIR / "knowledge-chunk-reviewed.json"
    if carry.is_file():
        for e in json.loads(carry.read_text()).get("entries", []):
            for q in e.get("questions", []):
                keys.add(normalize_question_key(q))
    return keys


def load_reviewed_entries() -> list[dict]:
    rows: list[dict] = []
    for p in sorted(BATCH_DIR.glob("reviewed-*.json")):
        rows.extend(json.loads(p.read_text()).get("entries", []))
    carry = BATCH_DIR / "carry-forward.json"
    if carry.is_file():
        rows.extend(json.loads(carry.read_text()).get("entries", []))
    return rows


def strip_for_user(text: str) -> str:
    text = PATH_IN_ANSWER.sub("", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip(" ・—-")
    return text


def unique_question(base: str, keys: set[str], salt: str = "") -> str | None:
    key = normalize_question_key(base)
    if not key or key in keys:
        return None
    keys.add(key)
    return base


def entry_id(chunk_id: str, ordinal: int) -> str:
    return "fullchunkqa-" + chunk_id.removeprefix("knowledge-") + f"-{ordinal}"


def base_entry(chunk: dict, ordinal: int) -> dict:
    return {
        "id": entry_id(chunk["id"], ordinal),
        "chunk_id": chunk["id"],
        "sources": [chunk["source"]],
        "source_sha256": chunk["source_sha256"],
        "review": {"method": "automatic-candidate", "status": "pending-context-review"},
    }


def text_candidates(text: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"[\u3000-\u9fffA-Za-z0-9]{10,}", text):
        seg = m.group(0).strip()
        if seg not in out:
            out.append(seg[:240])
    for raw in text.split("\n"):
        line = raw.strip()
        if len(line) < 3:
            continue
        if len(line) < 12 and not re.search(r"[\u3040-\u9fff]{2,}", line):
            continue
        if re.match(r"^<https?://", line) or re.match(r"^https?://", line):
            continue
        if HEADING.match(line):
            continue
        if line.count("http://") + line.count("https://") >= 2 and len(line) > 120:
            continue
        out.append(line)
    return out


def qa_from_text_line(
    line: str, heading: str, keys: set[str], salt: str = ""
) -> tuple[str, str, list[dict]] | None:
    m = BULLET_KV.match(line)
    if m:
        key, val = m.group(1).strip(), strip_for_user(m.group(2))
        if not val or len(val) > 200:
            val = val[:200]
        q_base = f"「{heading}」の記録では、{key}は何ですか？" if heading else f"この資料の{key}は何ですか？"
        q = unique_question(q_base, keys, salt)
        if not q:
            return None
        ans = f"{key}は{val}です。" if val else f"{key}について記載があります。"
        return q, ans, [{"kind": "quote", "text": line}]

    plain = strip_for_user(line)
    if len(plain) < 8:
        return None
    short = plain[:40] + ("…" if len(plain) > 40 else "")
    q_base = f"「{heading}」で触れている「{short}」の要点は？" if heading else f"次の記述の要点は？「{short}」"
    q = unique_question(q_base, keys, salt)
    if not q:
        return None
    ans = plain if len(plain) <= 220 else plain[:217] + "…"
    return q, ans, [{"kind": "quote", "text": line}]


def iter_scalars(value, prefix: str = "") -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    if isinstance(value, dict):
        for k, v in value.items():
            found.extend(iter_scalars(v, f"{prefix}{k}." if prefix else f"{k}."))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            found.extend(iter_scalars(v, f"{prefix}{i}."))
    else:
        if value is not None and str(value).strip() not in ("", "None"):
            found.append((prefix.rstrip("."), value))
    return found


def qa_from_json_unit(unit: dict, keys: set[str], salt: str = "") -> tuple[str, str, list[dict]] | None:
    value = unit.get("value")
    ctx = unit.get("context") or {}
    if isinstance(value, list) and value:
        if all(isinstance(x, str) for x in value):
            joined = "、".join(strip_for_user(x) for x in value[:4])
            if joined:
                q = unique_question("この項目に関連付けられている情報源は？", keys, salt)
                if q:
                    return q, f"関連情報: {joined}。", [{"kind": "json-unit", "unit": unit}]
        if isinstance(value[0], dict) and "leg" in value[0]:
            parts = [
                f"{row.get('leg')}区{row.get('distance_km', row.get('distance_m', '?'))}"
                for row in value[:6]
            ]
            q = unique_question("保存データの区間距離構成は？", keys, salt)
            if q:
                return q, "区間距離は " + "、".join(parts) + " などです。", [{"kind": "json-unit", "unit": unit}]
        if isinstance(value[0], dict) and "名前" in value[0]:
            item = value[0]
            name = item["名前"]
            q = unique_question(f"「{name}」に関する記載の要点は？", keys, salt)
            if q:
                ans = strip_for_user(name)[:220]
                if item.get("url"):
                    ans += f" 参照: {item['url']}"
                return q, ans, [{"kind": "json-unit", "unit": unit}]
    if isinstance(value, dict):
        if "title" in value and "date" in value:
            title = str(value["title"]).strip()
            date = str(value["date"]).strip()
            status = str(value.get("status", "")).strip()
            q = unique_question(f"「{title}」の予定日はいつですか？", keys, salt)
            if not q:
                return None
            ans = f"「{title}」は{date}です。"
            if status and status not in ("scheduled", "done", "cancelled"):
                ans += f" 状態は{status}です。"
            elif status == "scheduled":
                ans += " 予定として登録されています。"
            elif status == "done":
                ans += " 開催済みとして記録されています。"
            return q, ans, [{"kind": "json-unit", "unit": unit}]
        if "team" in value and "passing_rank" in value:
            team = value["team"]
            rank = value["passing_rank"]
            q = unique_question(
                f"{ctx.get('year', '')}年{ctx.get('gender', '')}{team}の通過順位は？".strip(), keys, salt
            )
            if not q:
                return None
            ans = f"{team}の通過順位は{rank}位です。"
            return q, ans, [{"kind": "json-unit", "unit": unit}]
        if "name" in value and "time_text" in value:
            name = value["name"]
            dist = value.get("distance") or value.get("event") or "記録"
            t = value["time_text"]
            q = unique_question(f"{name}の{dist}の記録タイムは？", keys, salt)
            if not q:
                return None
            ans = f"{name}の{dist}は{t}です。"
            return q, ans, [{"kind": "json-unit", "unit": unit}]
        if "question" in value and "answer" in value:
            qtext = str(value["question"]).strip()
            ans = str(value.get("explanation") or value["answer"]).strip()
            q = unique_question(strip_for_user(qtext)[:120], keys, salt)
            if not q:
                return None
            return q, strip_for_user(ans), [{"kind": "json-unit", "unit": unit}]
        scalars = [
            (k, v)
            for k, v in value.items()
            if not isinstance(v, (dict, list)) and str(v).strip() not in ("", "None")
        ]
        for k, v in scalars:
            label = str(k)
            q = unique_question(f"このデータの{label}の値は？", keys, salt)
            if not q:
                continue
            return q, f"{label}は{v}です。", [{"kind": "json-unit", "unit": unit}]
    if isinstance(value, str) and len(value.strip()) >= 10:
        q = unique_question(f"この項目の内容は？", keys, salt)
        if not q:
            return None
        return q, strip_for_user(value)[:220], [{"kind": "json-unit", "unit": unit}]
    return None


def qa_from_csv_row(
    row: dict, header: list[str], keys: set[str], source_text: str, salt: str = ""
) -> tuple[str, str, list[dict]] | None:
    cells = row["cells"]
    if len(cells) != len(header):
        return None
    data = dict(zip(header, cells))
    if "question" in data and "answer" in data:
        qtext = data["question"]
        expl = data.get("explanation") or data["answer"]
        q = unique_question(strip_for_user(qtext)[:140], keys, salt)
        if not q:
            return None
        quote = expl if expl in source_text else None
        if not quote:
            for c in cells:
                if len(c) >= 8 and c in source_text:
                    quote = c
                    break
        if not quote:
            return None
        ans = strip_for_user(expl)
        if data.get("answer") in ("○", "×"):
            ans = f"正解は{data['answer']}。{ans}"
        return q, ans, [{"kind": "quote", "text": quote}]
    if "名前" in data and "所属" in data:
        name, team = data["名前"], data["所属"]
        q = unique_question(f"{name}（{team}）の行で分かることは？", keys, salt)
        if not q:
            return None
        parts = [f"{name}は{team}所属"]
        for k, v in data.items():
            if k in ("名前", "所属") or not v:
                continue
            if re.search(r"SB$|記録|タイム", k):
                parts.append(f"{k}は{v}")
                break
        ans = "。".join(parts) + "。"
        quote = next((c for c in cells if c in source_text and len(c) >= 4), None)
        if not quote:
            return None
        return q, ans, [{"kind": "quote", "text": quote}]
    label = header[0] if header else "値"
    q = unique_question(f"この表の{label}列の1行目付近の内容は？", keys, salt)
    if not q:
        return None
    quote = next((c for c in cells if c in source_text and len(c) >= 6), None)
    if not quote:
        return None
    ans = strip_for_user(" / ".join(c for c in cells[:4] if c))
    return q, ans, [{"kind": "quote", "text": quote}]


def author_for_chunk(chunk: dict, need: int, keys: set[str], root: Path) -> list[dict]:
    ev = chunk["evidence"]
    source_text = (root / chunk["source"]).read_text()
    heading = ev.get("heading", "") if ev["kind"] == "text" else Path(chunk["source"]).stem
    salt = chunk["id"].removeprefix("knowledge-")[-8:]
    authored: list[dict] = []
    ordinal_base = 0

    if ev["kind"] == "text":
        lines = text_candidates(ev["text"])
        for line in lines:
            if len(authored) >= need:
                break
            item = qa_from_text_line(line, heading, keys, salt)
            if not item:
                continue
            q, ans, evidence = item
            ordinal_base += 1
            e = base_entry(chunk, ordinal_base)
            e.update(questions=[q], answer=ans, evidence=evidence)
            authored.append(e)
        if len(authored) < need:
            step = max(80, len(ev["text"]) // max(need + 1, 4))
            for i in range(0, max(1, len(ev["text"]) - 40), step):
                if len(authored) >= need:
                    break
                piece = ev["text"][i : i + 220].strip()
                if len(piece) < 15 or piece not in ev["text"]:
                    continue
                q = unique_question(
                    f"「{heading}」の記述抜粋{i // step + 1}の内容は？",
                    keys,
                    f"{salt}-sl{i // step}",
                )
                if not q:
                    continue
                ordinal_base += 1
                e = base_entry(chunk, ordinal_base)
                e.update(
                    questions=[q],
                    answer=strip_for_user(piece)[:240],
                    evidence=[{"kind": "quote", "text": piece}],
                )
                authored.append(e)
        if len(authored) < need:
            for para in re.split(r"\n\s*\n", ev["text"]):
                para = para.strip()
                if len(para) < 10:
                    continue
                snippet = para[: min(len(para), 400)]
                if snippet not in ev["text"]:
                    continue
                q = unique_question(
                    f"「{heading}」の抜粋で伝えている内容は？" if heading else "この抜粋の内容は？",
                    keys,
                    salt,
                )
                if not q:
                    continue
                ordinal_base += 1
                e = base_entry(chunk, ordinal_base)
                e.update(
                    questions=[q],
                    answer=strip_for_user(snippet)[:240],
                    evidence=[{"kind": "quote", "text": snippet}],
                )
                authored.append(e)
                if len(authored) >= need:
                    break
        return authored[:need]

    if ev["kind"] == "structured":
        units = ev.get("units", [])
        for unit in units:
            if len(authored) >= need:
                break
            if unit.get("string_span"):
                text = str(unit.get("value", "")).strip()
                step = max(120, len(text) // 4) if text else 0
                for i, start in enumerate(range(0, max(len(text), 1), step or 1)):
                    if len(authored) >= need:
                        break
                    piece = text[start : start + 220].strip()
                    if len(piece) < 12:
                        continue
                    q = unique_question(
                        f"このイベント説明の抜粋{i + 1}の要点は？",
                        keys,
                        f"{salt}-span{i}",
                    )
                    if not q:
                        continue
                    ordinal_base += 1
                    e = base_entry(chunk, ordinal_base)
                    e.update(
                        questions=[q],
                        answer=strip_for_user(piece)[:240],
                        evidence=[{"kind": "quote", "text": piece}],
                    )
                    authored.append(e)
                continue
            item = qa_from_json_unit(unit, keys, salt)
            if not item:
                continue
            q, ans, evidence = item
            if not str(ans).strip():
                continue
            ordinal_base += 1
            e = base_entry(chunk, ordinal_base)
            e.update(questions=[q], answer=ans, evidence=evidence)
            authored.append(e)
        if len(authored) < need and units:
            for unit in units:
                value = unit.get("value")
                if isinstance(value, str) and len(value) > 40:
                    step = max(120, len(value) // 4)
                    for i, start in enumerate(range(0, len(value), step)):
                        if len(authored) >= need:
                            break
                        piece = value[start : start + 220].strip()
                        if len(piece) < 12:
                            continue
                        q = unique_question(
                            f"この資料の抜粋{i + 1}の要点は？",
                            keys,
                            f"{salt}-str{i}",
                        )
                        if not q:
                            continue
                        ordinal_base += 1
                        e = base_entry(chunk, ordinal_base)
                        e.update(
                            questions=[q],
                            answer=strip_for_user(piece)[:240],
                            evidence=[{"kind": "json-unit", "unit": unit}],
                        )
                        authored.append(e)
                for label, val in iter_scalars(unit.get("value")):
                    if len(authored) >= need:
                        break
                    q = unique_question(f"設定項目「{label or '値'}」の内容は？", keys, f"{salt}-{label}-{len(authored)}")
                    if not q:
                        continue
                    ordinal_base += 1
                    e = base_entry(chunk, ordinal_base)
                    e.update(
                        questions=[q],
                        answer=f"{label + 'は' if label else ''}{val}です。",
                        evidence=[{"kind": "json-unit", "unit": unit}],
                    )
                    authored.append(e)
                if len(authored) >= need:
                    break
        return authored[:need]

    if ev["kind"] == "csv":
        header = ev["header"]
        for row in ev.get("units", []):
            if len(authored) >= need:
                break
            item = qa_from_csv_row(row, header, keys, source_text, salt)
            if not item:
                continue
            q, ans, evidence = item
            ordinal_base += 1
            e = base_entry(chunk, ordinal_base)
            e.update(questions=[q], answer=ans, evidence=evidence)
            authored.append(e)

    while len(authored) < need:
        if ev["kind"] == "text":
            snippet = ev.get("text", "").strip()
        else:
            snippet = source_text.strip()
        if not snippet:
            break
        start = min(max(0, len(snippet) - 1), len(authored) * 100)
        piece = snippet[start : start + 280].strip()
        if len(piece) < 12:
            piece = snippet[:280].strip()
        if len(piece) < 8:
            break
        if ev["kind"] == "text" and piece not in ev["text"]:
            piece = ev["text"][:280].strip()
        q = unique_question(f"資料「{heading}」の記載内容は？", keys, f"{salt}-fb{len(authored)}")
        if not q:
            break
        ordinal_base += 1
        e = base_entry(chunk, ordinal_base)
        if ev["kind"] == "structured" and ev.get("units"):
            e.update(
                questions=[q],
                answer=strip_for_user(piece)[:240],
                evidence=[{"kind": "json-unit", "unit": ev["units"][len(authored) % len(ev["units"])]}],
            )
        else:
            e.update(
                questions=[q],
                answer=strip_for_user(piece)[:240],
                evidence=[{"kind": "quote", "text": piece}],
            )
        authored.append(e)

    return authored[:need]


def write_batches(entries: list[dict], start_index: int, per_file: int) -> list[str]:
    written: list[str] = []
    for offset in range(0, len(entries), per_file):
        batch = entries[offset : offset + per_file]
        num = start_index + offset // per_file
        CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
        path = CANDIDATE_DIR / f"candidate-{num:04d}.json"
        path.write_text(json.dumps({"version": 1, "entries": batch}, ensure_ascii=False, indent=2) + "\n")
        written.append(str(path.relative_to(ROOT)))
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start-batch", type=int, default=18, help="First reviewed-NNNN number to write")
    ap.add_argument("--per-file", type=int, default=450)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    chunks = [
        json.loads(line)
        for p in sorted(OUT.glob("chunks-*.jsonl"))
        for line in p.read_text().split("\n")
        if line
    ]
    existing = load_reviewed_entries()
    by_chunk = Counter(e["chunk_id"] for e in existing)
    keys = load_existing_keys()
    pending = [c for c in chunks if by_chunk[c["id"]] < 3]

    new_entries: list[dict] = []
    unresolved: list[str] = []
    for chunk in pending:
        need = 3 - by_chunk[chunk["id"]]
        authored = author_for_chunk(chunk, need, keys, ROOT)
        if len(authored) < need:
            unresolved.append(chunk["id"])
        for i, e in enumerate(authored, 1):
            e["id"] = entry_id(chunk["id"], by_chunk[chunk["id"]] + i)
            new_entries.append(e)
            by_chunk[chunk["id"]] += 1

    report = {
        "pending_chunks": len(pending),
        "unreviewed_candidates": len(new_entries),
        "unresolved_chunks": len(unresolved),
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False))
        return

    if new_entries:
        files = write_batches(new_entries, args.start_batch, args.per_file)
        report["written_files"] = files
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
