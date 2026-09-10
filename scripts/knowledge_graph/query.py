"""Query the repository knowledge graph for routing paths + neighborhood context."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .builder import KG_PATH, ROOT, build_knowledge_graph

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u3040-\u30ff]+|[\u3400-\u9fff]+", re.UNICODE)
_PARTICLE_SPLIT = re.compile(r"[のとへをはがでにでもや]+")


def _tokenize(text: str) -> list[str]:
    """Tokenize for JP/EN routing queries (labels are often short JP names)."""
    text = text.lower().strip()
    tokens: list[str] = []
    for part in _PARTICLE_SPLIT.split(text):
        part = part.strip()
        if not part:
            continue
        for m in _TOKEN_RE.findall(part):
            if len(m) >= 1:
                tokens.append(m)
        # Character bigrams help when a compound stays glued
        chars = re.findall(r"[\u3400-\u9fff]", part)
        if len(chars) >= 2:
            for i in range(len(chars) - 1):
                tokens.append(chars[i] + chars[i + 1])
    # Deduplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def load_graph(path: Path | None = None) -> dict[str, Any]:
    path = path or KG_PATH
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return build_knowledge_graph()


def _score_node(node: dict[str, Any], q_tokens: list[str], query: str) -> float:
    label = (node.get("label") or "").lower()
    node_type = node.get("type", "")
    hint = (node.get("hint") or "").lower()
    topics = " ".join(node.get("topics") or []).lower()
    refs = " ".join(node.get("refs") or []).lower()
    blob = " ".join([node.get("id", ""), label, hint, topics, refs]).lower()
    q = query.lower().strip()
    score = 0.0
    # Exact / substring label hit (critical for athlete names)
    if label and label in q:
        score += 8.0
    for tok in q_tokens:
        if not tok:
            continue
        if tok == label:
            score += 6.0
            continue
        if tok and tok in label:
            score += 3.0
            continue
        # For Athlete nodes, avoid scoring generic hint/topic words
        if node_type == "Athlete":
            continue
        if tok in blob:
            score += 2.0 if len(tok) >= 2 else 0.5
    if node_type != "Athlete" and q and q in blob:
        score += 5.0
    if score <= 0:
        return 0.0
    boost = {
        "QueryHint": 1.5,
        "Topic": 1.2,
        "Source": 1.0,
        "Athlete": 1.4,
        "Template": 1.1,
        "Entity": 1.0,
        "Year": 1.0,
    }
    score *= boost.get(node_type, 1.0)
    return score


def _adjacency(edges: list[dict[str, str]]) -> dict[str, list[tuple[str, str]]]:
    """Directed adjacency: from -> [(to, rel), ...]."""
    adj: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for e in edges:
        adj[e["from"]].append((e["to"], e["rel"]))
    return adj


def _read_neighborhood(path: Path, query: str, *, max_chars: int = 2400) -> str:
    if not path.exists() or not path.is_file():
        return ""
    # Skip large binaries
    if path.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return f"[binary/image skipped: {_rel_safe(path)}]"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if not text.strip():
        return ""
    tokens = [t for t in _tokenize(query) if len(t) >= 2]
    if not tokens:
        return text[:max_chars]
    lines = text.splitlines()
    hit_idxs = [
        i
        for i, line in enumerate(lines)
        if any(tok in line.lower() for tok in tokens)
    ]
    if not hit_idxs:
        return text[:max_chars]
    windows: list[str] = []
    used: set[int] = set()
    for idx in hit_idxs[:8]:
        start = max(0, idx - 4)
        end = min(len(lines), idx + 5)
        for j in range(start, end):
            if j not in used:
                used.add(j)
        chunk = "\n".join(lines[start:end])
        windows.append(chunk)
    joined = "\n---\n".join(windows)
    return joined[:max_chars]


def _rel_safe(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def query_knowledge_graph(
    question: str,
    *,
    graph: dict[str, Any] | None = None,
    top_k: int = 8,
    expand_hops: int = 1,
    context_files: int = 6,
    include_context: bool = True,
) -> dict[str, Any]:
    graph = graph or load_graph()
    nodes = {n["id"]: n for n in graph.get("nodes") or []}
    edges = list(graph.get("edges") or [])
    adj = _adjacency(edges)
    q_tokens = _tokenize(question)

    scored = [
        (nid, _score_node(node, q_tokens, question))
        for nid, node in nodes.items()
    ]
    scored = [(nid, s) for nid, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    seeds = scored[:top_k]

    # If a specific entity matched strongly, drop broad Topic/QueryHint seeds that flood refs
    if any(nodes[nid]["type"] in {"Athlete", "Template", "Year"} and s >= 8 for nid, s in seeds):
        seeds = [
            (nid, s)
            for nid, s in seeds
            if nodes[nid]["type"] not in {"Topic", "QueryHint"} or s >= 20
        ] or seeds[:3]

    # If nothing matched, fall back to Topic nodes by crude keyword map
    if not seeds:
        fallback = []
        mapping = [
            (["練習", "メニュー", "jog", "interval", "欠席"], "topic:practice"),
            (["記録", "タイム", "選手", "PB"], "topic:athlete_records"),
            (["カレンダー", "予定", "祝日", "inbox"], "topic:calendar"),
            (["norwegian", "gz", "閾値", "vdot", "ペース"], "topic:norwegian"),
            (["ai", "生成", "プロンプト"], "topic:ai"),
            (["ケガ", "障害", "rri", "怪我"], "topic:injury"),
        ]
        q = question.lower()
        for keys, tid in mapping:
            if any(k.lower() in q for k in keys) and tid in nodes:
                fallback.append((tid, 1.0))
        seeds = fallback[:top_k] or [("topic:meta", 1.0)] if "topic:meta" in nodes else scored[:top_k]

    selected: dict[str, float] = {nid: score for nid, score in seeds}
    frontier = list(selected.keys())
    route_rels = {"search_here", "documented_in", "mentioned_in", "see_also"}
    for _ in range(max(0, expand_hops)):
        nxt: list[str] = []
        for nid in frontier:
            for neighbor, rel in adj.get(nid, []):
                if rel not in route_rels:
                    continue
                boost = 0.85 if rel in {"search_here", "mentioned_in", "documented_in"} else 0.55
                new_score = selected[nid] * boost
                if neighbor not in selected or new_score > selected[neighbor]:
                    selected[neighbor] = new_score
                    nxt.append(neighbor)
        frontier = nxt

    ordered_ids = sorted(selected.keys(), key=lambda i: selected[i], reverse=True)
    hit_nodes = [nodes[i] for i in ordered_ids if i in nodes]

    refs: list[str] = []
    seen_refs: set[str] = set()
    for node in hit_nodes:
        for ref in node.get("refs") or []:
            if ref not in seen_refs:
                seen_refs.add(ref)
                refs.append(ref)

    contexts: list[dict[str, str]] = []
    if include_context:
        for ref in refs[:context_files]:
            path = ROOT / ref
            snippet = _read_neighborhood(path, question)
            if snippet:
                contexts.append({"path": ref, "snippet": snippet})

    return {
        "question": question,
        "matched_nodes": [
            {
                "id": n["id"],
                "type": n["type"],
                "label": n["label"],
                "score": round(selected.get(n["id"], 0), 3),
                "hint": n.get("hint", ""),
                "refs": n.get("refs") or [],
            }
            for n in hit_nodes[: max(top_k * 3, 12)]
        ],
        "refs": refs,
        "contexts": contexts,
    }
