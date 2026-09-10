"""School name normalization for Aragyoku ekiden transcripts."""

from __future__ import annotations

import unicodedata

SCHOOL_ALIASES = {
    "荒尾第三": "荒尾三",
    "荒尾第四": "荒尾四",
}


def school_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").replace(" ", "").replace("　", "")
    for suffix in ("中学校", "中"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return SCHOOL_ALIASES.get(normalized, normalized)
