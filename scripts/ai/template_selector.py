"""Template selection for AI practice generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config import TEMPLATES_PATH


@dataclass(frozen=True)
class TemplateMatch:
    template_id: str
    label: str
    score: float
    practice: dict[str, Any]


def load_templates(path: Path | None = None) -> list[dict[str, Any]]:
    templates_path = path or TEMPLATES_PATH
    if not templates_path.exists():
        return []
    data = yaml.safe_load(templates_path.read_text(encoding="utf-8")) or {}
    return data.get("templates") or []


def _tokenize(text: str) -> set[str]:
    text = text.lower()
    tokens = set(re.findall(r"[\w\d]+", text))
    tokens.update(re.findall(r"\d+", text))
    return tokens


def _score_template(query: str, template: dict[str, Any]) -> float:
    tid = template.get("id") or ""
    label = template.get("label") or ""
    practice = template.get("practice") or {}
    notes = practice.get("notes") or ""
    items_text = " ".join(
        str(v)
        for item in practice.get("items") or []
        for v in item.values()
        if v is not None
    )
    corpus = f"{tid} {label} {notes} {items_text}".lower()
    query_l = query.lower()
    score = 0.0

    # Strong signals
    if tid.replace("-", " ") in query_l or tid in query_l:
        score += 10.0
    for dist in re.findall(r"(\d+)\s*m", query_l):
        if f"{dist}m" in corpus:
            score += 5.0
    if "gz" in query_l or "ゴールデン" in query_l or "軽" in query_l:
        if "gz" in corpus or "軽" in label:
            score += 4.0
    if "45/15" in query_l or "45" in query_l:
        if "45/15" in corpus or "norwegian" in tid:
            score += 6.0
    if "ジョグ" in query_l or "jog" in query_l:
        if "jog" in tid:
            score += 3.0
    if "夕練" in query_l:
        if "evening" in tid or "夕練" in label:
            score += 3.0
    if "rp" in query_l.lower():
        if "rp" in corpus:
            score += 3.0

    q_tokens = _tokenize(query_l)
    c_tokens = _tokenize(corpus)
    if q_tokens and c_tokens:
        score += len(q_tokens & c_tokens) * 0.5

    return score


def select_templates(
    query: str,
    *,
    path: Path | None = None,
    top_k: int = 3,
) -> list[TemplateMatch]:
    templates = load_templates(path)
    scored: list[TemplateMatch] = []
    for tpl in templates:
        tid = tpl.get("id")
        if not tid:
            continue
        score = _score_template(query, tpl)
        scored.append(
            TemplateMatch(
                template_id=tid,
                label=tpl.get("label") or tid,
                score=score,
                practice=tpl.get("practice") or {"items": []},
            )
        )
    scored.sort(key=lambda m: m.score, reverse=True)
    return scored[:top_k]


def select_template_by_id(template_id: str, *, path: Path | None = None) -> TemplateMatch | None:
    for tpl in load_templates(path):
        tid = tpl.get("id")
        if tid != template_id:
            continue
        return TemplateMatch(
            template_id=tid,
            label=tpl.get("label") or tid,
            score=100.0,
            practice=tpl.get("practice") or {"items": []},
        )
    return None


def select_best_template(query: str, *, path: Path | None = None) -> TemplateMatch | None:
    matches = select_templates(query, path=path, top_k=1)
    if not matches or matches[0].score <= 0:
        return None
    return matches[0]
