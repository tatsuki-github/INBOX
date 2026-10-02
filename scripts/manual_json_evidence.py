"""Literal provenance checks for manually reviewed structured JSON excerpts."""
import json
import re
from datetime import date, datetime
from pathlib import Path

import yaml

from prepare_knowledge_qa_chunks import compact, resolve_pointer


def normalize_leaf(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return value


def load_structured_source(source_text: str, source_path: str):
    suffix = Path(source_path).suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return yaml.load(source_text, Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
    return json.loads(source_text)


def validate_manual_json(entry, chunk, source_text):
    source = load_structured_source(source_text, chunk.get("source") or entry.get("sources", ["source.json"])[0])
    units={u['pointer']:u for u in chunk['evidence']['units']}
    for evidence in entry.get('evidence',[]):
        if evidence.get('kind')!='json-unit':raise ValueError('typed JSON evidence required')
        unit=evidence['unit'];pointer=unit['pointer']
        if unit.get('string_span'):raise ValueError('split string validator required')
        if units.get(pointer)!=unit:raise ValueError('JSON evidence outside assigned chunk')
        actual = resolve_pointer(source, pointer)
        if compact(actual) != compact(unit["value"]):
            raise ValueError("JSON source record changed")
        # Context is derived only from scalar ancestor labels, never supplied
        # by an unrelated year or team.
        expected={};value=source
        for escaped in pointer.lstrip('/').split('/') if pointer else []:
            if isinstance(value,dict):
                expected.update({k:v for k,v in value.items() if not isinstance(v,(dict,list)) and len(str(v))<=160})
            part=escaped.replace('~1','/').replace('~0','~')
            value=value[int(part)] if isinstance(value,list) else value[part]
        m=re.match(r'^/years/(20\d{2})(?:/|$)',pointer)
        if m and isinstance(source.get('meta'),dict) and source['meta'].get('gender') in ('男子','女子') and 'gender' not in source['years'][m[1]]:
            expected.update(year=int(m[1]),gender=source['meta']['gender'])
        if unit.get('context',{})!=expected:raise ValueError('JSON source context changed')


def validate_string_span_quotes(entry, chunk, source_text):
    source = load_structured_source(source_text, chunk.get("source") or entry.get("sources", ["source.json"])[0])
    span_units = [u for u in chunk["evidence"]["units"] if u.get("string_span")]
    if not span_units:
        raise ValueError("missing string span units")
    for evidence in entry.get("evidence", []):
        if evidence.get("kind") != "quote":
            raise ValueError("quote evidence required")
        quote = evidence.get("text") or ""
        host = next((u for u in span_units if quote in str(u.get("value", ""))), None)
        if not host:
            raise ValueError("quote is not grounded in structured source")
        pointer = host["pointer"]
        full = resolve_pointer(source, pointer)
        if not isinstance(full, str):
            raise ValueError("string span host is not text")
        start, end = host["string_span"]
        if full[slice(start, end)] != host["value"]:
            raise ValueError("string span partition drift")
