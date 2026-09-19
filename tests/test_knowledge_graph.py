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
    html = tmp_path / "knowledge-graph.html"
    pdf = tmp_path / "knowledge-graph.pdf"
    path, min_path, html_path, pdf_path, graph = write_knowledge_graph(
        out,
        min_path=mini,
        html_path=html,
        pdf_path=pdf,
        generated_at="2026-01-01T00:00:00Z",
    )
    assert path.exists() and min_path.exists() and html_path.exists() and pdf_path.exists()
    committed = json.loads(path.read_text(encoding="utf-8"))
    fresh = build_knowledge_graph(generated_at=committed["generated_at"])
    assert normalize_graph_for_compare(committed) == normalize_graph_for_compare(fresh)
    assert len(json.loads(min_path.read_text(encoding="utf-8"))["nodes"]) == len(graph["nodes"])
    html_text = html_path.read_text(encoding="utf-8")
    assert 'id="kg-data"' in html_text
    assert 'id="kg-search"' in html_text
    assert 'id="kg-filters"' in html_text
    assert 'id="kg-detail"' in html_text
    assert 'id="list-fallback"' in html_text
    assert "open_knowledge_graph.py" in html_text
    assert "vis-network" in html_text
    assert '"version":1' in html_text or '"version": 1' in html_text
    # Embedded JSON must be script-safe
    assert "</script>" not in html_text.split('id="kg-data"', 1)[1].split("</script>", 1)[0]
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert pdf_path.stat().st_size > 1000


def test_html_renderer_embeds_graph():
    from knowledge_graph.html_renderer import render_knowledge_graph_html

    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    html = render_knowledge_graph_html(graph)
    assert "INBOX Knowledge Graph" in html
    assert "application/json" in html
    assert any(n["id"] in html for n in graph["nodes"][:3])


def test_pdf_renderer_writes_japanese_snapshot(tmp_path: Path):
    from knowledge_graph.pdf_renderer import write_knowledge_graph_pdf

    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    pdf_path = write_knowledge_graph_pdf(graph, tmp_path / "kg.pdf")
    data = pdf_path.read_bytes()
    assert data.startswith(b"%PDF")
    assert b"INBOX" in data or b"/Type" in data
    assert pdf_path.stat().st_size > 2000


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


def test_query_routes_school_average_to_pb_ranking():
    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    result = query_knowledge_graph(
        "女子800mで岱明の上位3人平均は？",
        graph=graph,
        include_context=False,
    )
    joined = " ".join(result["refs"]) + " ".join(n["id"] for n in result["matched_nodes"])
    assert "2026_women_800m_1500m_pb_school_ranking" in joined


def test_query_routes_kikui_leg_to_team_digest():
    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    result = query_knowledge_graph(
        "菊水の荒玉駅伝の1区は誰？",
        graph=graph,
        include_context=False,
    )
    joined = " ".join(result["refs"])
    assert "aragyoku-teams/菊水.md" in joined


def test_query_routes_kanaguri_project_not_nagomi():
    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    result = query_knowledge_graph(
        "金栗PROJECT所属選手の全記録",
        graph=graph,
        include_context=False,
    )
    joined = " ".join(result["refs"])
    assert "arato-tamana-teams/金栗PROJECT.md" in joined
    assert not any("なごみ" in r for r in result["refs"][:12])
    top = result["matched_nodes"][:8]
    assert not any("なごみ" in (n.get("label") or "") for n in top)


def test_query_routes_unnamed_leg_not_start_list():
    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    result = query_knowledge_graph(
        "案浦竜士は何区を走った？",
        graph=graph,
        include_context=False,
    )
    joined = " ".join(result["refs"])
    assert "aragyoku-teams" in joined
    first = result["refs"][0] if result["refs"] else ""
    assert "スタートリスト" not in first
    assert "通信陸上" not in first


def test_query_routes_nagomi_order_not_kanaguri_ekiden():
    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    result = query_knowledge_graph(
        "なごみ駅伝の岱明男子1区は誰？",
        graph=graph,
        include_context=False,
    )
    joined = " ".join(result["refs"])
    assert "なごみ" in joined
    first = result["refs"][0] if result["refs"] else ""
    assert "0315_金栗駅伝" not in first
    assert "金栗記念" not in first


def test_query_routes_nagomi_2025_results():
    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    result = query_knowledge_graph(
        "2025年のなごみ駅伝の結果は？",
        graph=graph,
        include_context=False,
    )
    joined = " ".join(result["refs"])
    assert "2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会" in joined
    assert "成績表" in joined or "予実比較" in joined
    first = result["refs"][0] if result["refs"] else ""
    assert "0315_金栗駅伝" not in first
    assert "金栗記念" not in first


def test_schema_validation_if_jsonschema_available():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "knowledge-graph.schema.json").read_text(encoding="utf-8"))
    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    jsonschema.Draft202012Validator(schema).validate(graph)
