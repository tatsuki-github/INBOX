"""Literal provenance checks for manually reviewed structured JSON excerpts."""
import json,re
from prepare_knowledge_qa_chunks import resolve_pointer


def validate_manual_json(entry,chunk,source_text):
    source=json.loads(source_text)
    units={u['pointer']:u for u in chunk['evidence']['units']}
    for evidence in entry.get('evidence',[]):
        if evidence.get('kind')!='json-unit':raise ValueError('typed JSON evidence required')
        unit=evidence['unit'];pointer=unit['pointer']
        if unit.get('string_span'):raise ValueError('split string validator required')
        if units.get(pointer)!=unit:raise ValueError('JSON evidence outside assigned chunk')
        if resolve_pointer(source,pointer)!=unit['value']:raise ValueError('JSON source record changed')
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
