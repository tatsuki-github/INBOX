"""Tests for repository knowledge graph builder and query router."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from knowledge_graph.builder import (  # noqa: E402
    build_knowledge_graph,
    normalize_graph_for_compare,
    write_knowledge_graph,
)
from knowledge_graph.query import query_knowledge_graph  # noqa: E402


def test_build_knowledge_graph_has_topics_and_sources():
    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    assert graph["version"] == 1
    ids = {n["id"] for n in graph["nodes"]}
    assert "topic:practice" in ids
    assert "topic:calendar" in ids
    assert "source:input/practice_templates.yaml" in ids
    assert any(n["type"] == "Source" and n["id"].startswith("source:input/events.") for n in graph["nodes"])
    assert graph["edges"]


def test_write_and_check_roundtrip(tmp_path: Path):
    out = tmp_path / "knowledge-graph.json"
    mini = tmp_path / "knowledge-graph.min.json"
    path, min_path, graph = write_knowledge_graph(out, min_path=mini, generated_at="2026-01-01T00:00:00Z")
    assert path.exists() and min_path.exists()
    committed = json.loads(path.read_text(encoding="utf-8"))
    fresh = build_knowledge_graph(generated_at=committed["generated_at"])
    assert normalize_graph_for_compare(committed) == normalize_graph_for_compare(fresh)
    assert len(json.loads(min_path.read_text(encoding="utf-8"))["nodes"]) == len(graph["nodes"])


def test_query_routes_athlete_to_absentee_refs():
    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    # Use an athlete known to appear in absentees for recent years
    athletes = [n["label"] for n in graph["nodes"] if n["type"] == "Athlete"]
    assert athletes
    name = "松野" if "松野" in athletes else athletes[0]
    result = query_knowledge_graph(
        f"{name}の欠席",
        graph=graph,
        include_context=False,
        top_k=8,
    )
    assert result["matched_nodes"]
    assert result["matched_nodes"][0]["type"] == "Athlete"
    assert any("practice_absentees.csv" in r or "events." in r for r in result["refs"])


def test_query_routes_gz_to_norwegian_or_pace():
    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    result = query_knowledge_graph(
        "GZペースの決め方",
        graph=graph,
        include_context=False,
    )
    joined = " ".join(result["refs"]) + " ".join(n["id"] for n in result["matched_nodes"])
    assert "norwegian" in joined or "daniels" in joined or "pace" in joined or "kpace" in joined


def test_schema_validation_if_jsonschema_available():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "knowledge-graph.schema.json").read_text(encoding="utf-8"))
    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    jsonschema.Draft202012Validator(schema).validate(graph)
