#!/usr/bin/env python3
"""Lossless, source-pinned inventory for three new QAs per knowledge chunk.

This script only prepares evidence and coverage. It never invents answers, edits
the prepared catalog, or declares QA completion. Authored answers are a separate
reviewed stage. Default scope: corpus documents + their original sources + every
textual source reached by the repository knowledge graph.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/qa-chunks"
BUDGET = 5000
TEXT = {".md", ".txt", ".csv", ".json", ".yaml", ".yml"}
BOOKKEEPING = {"sources.json", "SOURCES.md"}
FAQ_NAMES = {"prepared-qa.v1.yaml", "prepared-qa.json"}
ENGINE_OUTPUTS = {"knowledge-graph.json", "knowledge-graph.min.json", "rag_index.json"}

def digest(text):
    if isinstance(text, str):
        text = text.encode("utf-8")
    return hashlib.sha256(text).hexdigest()

def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)

def pointer(parent, part):
    return parent + "/" + str(part).replace("~", "~0").replace("/", "~1")

def resolve_pointer(value, path):
    for part in path.lstrip("/").split("/") if path else []:
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value

def safe_path(rel):
    path = (ROOT / rel).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("source escapes repository: " + str(rel))
    return path

def split_spans(text, budget=BUDGET):
    """Partition ALL characters; prefer paragraphs, then lines, then sentences."""
    start = 0
    while start < len(text):
        end = min(start + budget, len(text))
        if end < len(text):
            floor = start + budget // 2
            boundaries = [text.rfind("\n\n", floor, end), text.rfind("\n", floor, end),
                          text.rfind("。", floor, end)]
            for boundary in boundaries:
                if boundary >= floor:
                    end = boundary + (2 if text[boundary:boundary+2] == "\n\n" else 1)
                    break
        yield start, end
        start = end

def object_units(value, path="", context=None):
    """Typed units retain JSON pointers instead of cutting JSON mid-record."""
    context = context or {}
    rendered = compact(value)
    if len(rendered) <= BUDGET:
        yield {"pointer": path, "value": value, "context": context}
    elif isinstance(value, dict):
        labels = {k: v for k, v in value.items()
                  if not isinstance(v, (dict, list)) and len(str(v)) <= 160}
        for key, child in value.items():
            yield from object_units(child, pointer(path, key), {**context, **labels})
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from object_units(child, pointer(path, index), context)
    elif isinstance(value, str):
        for start, end in split_spans(value):
            yield {"pointer": path, "string_span": [start, end],
                   "value": value[start:end], "context": context}
    else:
        yield {"pointer": path, "value": value, "context": context}

def pack_units(units):
    batch, size = [], 0
    for unit in units:
        length = len(compact(unit))
        if batch and size + length > BUDGET:
            yield batch
            batch, size = [], 0
        batch.append(unit)
        size += length
    if batch:
        yield batch

def chunk_csv(raw):
    # csv.reader preserves quoted commas and multiline cells. No width trimming.
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        return []
    header = rows[0]
    units = [{"row": i, "cells": row} for i, row in enumerate(rows[1:], 1)]
    return [{"kind": "csv", "header": header, "units": batch}
            for batch in pack_units(units)] or [{"kind": "csv", "header": header, "units": []}]

def chunk_source(raw, suffix):
    if suffix == ".csv":
        return chunk_csv(raw)
    if suffix in {".json", ".yaml", ".yml"}:
        try:
            value = json.loads(raw) if suffix == ".json" else yaml.load(
                raw, Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
            # YAML dates are rendered with default=str, and pointer checks retain
            # the same parsing; no dates or fields are inferred from filenames.
            return [{"kind": "structured", "units": units}
                    for units in pack_units(object_units(value))]
        except (ValueError, TypeError, yaml.YAMLError):
            # Invalid imported JSON is retained as text, not silently discarded.
            pass
    parts = []
    headings = list(re.finditer(r"(?m)^#{1,6}\s+(.+)$", raw))
    for start, end in split_spans(raw):
        before = [m.group(1) for m in headings if m.start() <= start]
        parts.append({"kind": "text", "span": [start, end], "text": raw[start:end],
                      "heading": before[-1] if before else ""})
    return parts

def verify_partition(raw, suffix, parts):
    if not parts:
        assert not raw
        return
    if parts[0]["kind"] == "text":
        assert "".join(p["text"] for p in parts) == raw
        assert parts[0]["span"][0] == 0 and parts[-1]["span"][1] == len(raw)
        for p in parts:
            assert raw[slice(*p["span"])] == p["text"]
    elif parts[0]["kind"] == "csv":
        rows = list(csv.reader(io.StringIO(raw)))
        flattened = [u for p in parts for u in p["units"]]
        assert [u["row"] for u in flattened] == list(range(1, len(rows)))
        assert [u["cells"] for u in flattened] == rows[1:]
        assert all(p["header"] == rows[0] for p in parts)
    else:
        value = json.loads(raw) if suffix == ".json" else yaml.load(
            raw, Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
        units = [u for p in parts for u in p["units"]]
        for u in units:
            actual = resolve_pointer(value, u["pointer"])
            if "string_span" in u:
                actual = actual[slice(*u["string_span"])]
            assert compact(actual) == compact(u["value"])
        # Independently enumerate all scalar leaves; each must be covered by a
        # complete ancestor unit or a complete string-span partition.
        leaves = []
        def walk(v, path=""):
            if isinstance(v, dict) and v:
                for k, x in v.items(): walk(x, pointer(path, k))
            elif isinstance(v, list) and v:
                for k, x in enumerate(v): walk(x, pointer(path, k))
            else:
                leaves.append((path, v))
        walk(value)
        covered = {u["pointer"] for u in units if "string_span" not in u}
        spans = {}
        for u in units:
            if "string_span" in u:
                spans.setdefault(u["pointer"], []).append(u)
        for path, leaf in leaves:
            if any(path == p or path.startswith(p + "/") or p == "" for p in covered):
                continue
            pieces = sorted(spans.get(path, []), key=lambda u: u["string_span"][0])
            assert isinstance(leaf, str) and "".join(u["value"] for u in pieces) == leaf, path

def discover():
    routes = {}
    def add(rel, reason):
        routes.setdefault(rel, set()).add(reason)
    graph = json.loads((ROOT / "out/knowledge-graph.json").read_text())
    for node in graph["nodes"]:
        for ref in node.get("refs", []):
            if not isinstance(ref, str) or re.match(r"[a-z]+://", ref):
                continue
            # Legacy KG refs sometimes annotate the derived directory.
            ref = re.sub(r" [(]derived[)]$", "", ref)
            path = safe_path(ref)
            if path.is_dir():
                for child in sorted(path.rglob("*")):
                    if child.is_file():
                        add(str(child.relative_to(ROOT)), "kg-directory:" + ref)
            else:
                add(ref, "kg-reference")
    manifest = json.loads((ROOT / "input/idaten-corpus/sources.json").read_text())
    for item in manifest:
        original = re.sub(r" [(]derived[)]$", "", item["source"])
        path = safe_path(original)
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    add(str(child.relative_to(ROOT)), "corpus-derived-original:" + original)
        else:
            add(original, "corpus-original")
        rel = "input/idaten-corpus/" + item["corpus"]
        add(rel, "corpus-copy")
    for path in sorted((ROOT / "input/idaten-corpus").rglob("*")):
        if path.is_file():
            add(str(path.relative_to(ROOT)), "corpus-file")
    return routes

def build():
    routes = discover()
    files, content_groups = [], {}
    copy_origins = {"input/idaten-corpus/" + item["corpus"]: item["source"]
                    for item in json.loads((ROOT / "input/idaten-corpus/sources.json").read_text())}
    for rel, origin in sorted(routes.items()):
        path = safe_path(rel)
        record = {"path": rel, "routes": sorted(origin)}
        files.append(record)
        if rel.startswith("out/qa-chunks/") or rel.startswith("input/faq/chunk-qa/"):
            record["disposition"] = "generated-review-ledger"
        elif path.name in FAQ_NAMES or path.name in ENGINE_OUTPUTS or path.name in BOOKKEEPING:
            record["disposition"] = "derived-index-or-existing-qa"
        elif not path.is_file():
            record["disposition"] = "missing-route"
        elif path.suffix.lower() not in TEXT:
            record["disposition"] = "nontext-asset-or-implementation"
        else:
            payload = path.read_bytes()
            record["source_sha256"] = digest(payload)
            raw = payload.decode("utf-8-sig", errors="strict").replace("\r\n", "\n")
            if not raw.strip():
                record["disposition"] = "empty-document"
                continue
            h = digest(raw)
            record["normalized_sha256"] = h
            record["disposition"] = "canonical-or-alias"
            # Do not merge identical words from unrelated subject contexts.
            owner = copy_origins.get(rel, rel)
            original = safe_path(owner)
            if original.is_file():
                original_text = original.read_bytes().decode("utf-8-sig", errors="strict").replace("\r\n", "\n")
                if digest(original_text) != h:
                    owner = rel
            else:
                owner = rel
            content_groups.setdefault((owner, h), []).append((rel, raw, record))
    chunks = []
    for (owner, h), group in sorted(content_groups.items()):
        # Prefer original snapshots; preserve every identical alias in coverage.
        group.sort(key=lambda row: (row[0].startswith("input/idaten-corpus/"), row[0]))
        rel, raw, canonical = group[0]
        parts = chunk_source(raw, Path(rel).suffix.lower())
        verify_partition(raw, Path(rel).suffix.lower(), parts)
        ids = []
        for index, part in enumerate(parts):
            chunk_id = "knowledge-" + digest(compact([owner, h, index, part]))[:24]
            ids.append(chunk_id)
            chunks.append({"id": chunk_id, "source": rel, "source_sha256": canonical["source_sha256"],
                           "source_normalized_sha256": h, "index": index,
                           "title": Path(rel).stem, "evidence": part, "required_new_qa": 3})
        for alias, _, record in group:
            record["disposition"] = "canonical" if alias == rel else "identical-alias"
            record["canonical"] = rel
            record["chunk_ids"] = ids
    assert len({c["id"] for c in chunks}) == len(chunks)
    by_path = {f["path"]: f for f in files}
    for record in files:
        m = re.fullmatch(r"input/idaten-corpus/calendar/events[.](20\d{2})[.]filtered[.]yaml", record["path"])
        if record["disposition"] == "missing-route" and m:
            source = "input/events." + m[1] + ".yaml"
            full = by_path.get(source)
            if full and full.get("chunk_ids"):
                record.update(disposition="virtual-filtered-calendar-route",
                              covered_by=source, chunk_ids=full["chunk_ids"])
    missing = [f["path"] for f in files if f["disposition"] == "missing-route"]
    catalog = ROOT / "input/faq/prepared-qa.v1.yaml"
    existing = yaml.load(catalog.read_text(), Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
    return {"version": 1, "max_chunk_chars": BUDGET, "files": files,
            "baseline_prepared_qa_count": len(existing["entries"]),
            "baseline_prepared_qa_sha256": digest(catalog.read_bytes()),
            "chunk_kinds": dict(Counter(c["evidence"]["kind"] for c in chunks)),
            "canonical_suffixes": dict(Counter(Path(f["path"]).suffix.lower() for f in files
                                               if f["disposition"] == "canonical")),
            "chunk_count": len(chunks), "required_new_qa": len(chunks) * 3,
            "dispositions": dict(Counter(f["disposition"] for f in files)),
            "missing_routes": missing}, chunks

def write():
    inventory, chunks = build()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("chunks-*.jsonl"):
        old.unlink()
    # Bounded files are directly reviewable through GitHub's contents API.
    part, buffer, chars = 1, [], 0
    batches = []
    for chunk in chunks:
        line = json.dumps(chunk, ensure_ascii=False, default=str) + "\n"
        if buffer and chars + len(line) > 180000:
            name = f"chunks-{part:04d}.jsonl"
            (OUT / name).write_text("".join(buffer))
            batches.append({"path": "out/qa-chunks/" + name, "chunks": len(buffer)})
            part, buffer, chars = part + 1, [], 0
        buffer.append(line)
        chars += len(line)
    if buffer:
        name = f"chunks-{part:04d}.jsonl"
        (OUT / name).write_text("".join(buffer))
        batches.append({"path": "out/qa-chunks/" + name, "chunks": len(buffer)})
    inventory["batches"] = batches
    source_index = {}
    for chunk in chunks:
        source_index.setdefault(chunk["source"], []).append(chunk["id"])
    (OUT / "source-index.json").write_text(json.dumps(source_index, ensure_ascii=False, indent=2) + "\n")
    (OUT / "inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n")
    report = {k: v for k, v in inventory.items() if k not in {"files", "batches"}}
    report["batches"] = len(batches)
    (OUT / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    print("Evidence prepared. No QAs authored; completion has NOT been declared.")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        write()
    else:
        inventory, _ = build()
        print(json.dumps({k: v for k, v in inventory.items() if k != "files"}, ensure_ascii=False))
if __name__ == "__main__":
    main()
