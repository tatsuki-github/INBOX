"""いだてん岱明 外部データ取り込みの受け入れ条件テスト。"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from knowledge_graph.builder import build_knowledge_graph  # noqa: E402

EXTERNAL = ROOT / "input" / "external"


def test_external_root_and_indexes_exist():
    assert (EXTERNAL / "INDEX.md").is_file()
    assert (EXTERNAL / "drive" / "INDEX.md").is_file()
    assert (EXTERNAL / "notion" / "INDEX.md").is_file()
    assert (EXTERNAL / "github" / "INDEX.md").is_file()


def test_roster_csv_has_expected_headers():
    path = EXTERNAL / "drive" / "shared" / "名簿" / "2025年度_岱明中学校陸上競技部_部員名簿.csv"
    assert path.is_file()
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
    assert "姓" in header and "名" in header
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) >= 10


def test_practice_log_markdown_exists():
    path = EXTERNAL / "drive" / "shared" / "練習" / "練習の記録.md"
    text = path.read_text(encoding="utf-8")
    assert "動きづくり" in text
    assert "2025" in text


def test_notion_students_and_records_rows():
    students = json.loads(
        (EXTERNAL / "notion" / "databases" / "いだてん岱明生徒" / "rows.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(students, list) and len(students) >= 10
    records = json.loads(
        (EXTERNAL / "notion" / "databases" / "2026年度中学生記録" / "rows.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(records, list) and len(records) >= 100


def test_skip_policy_documented_in_indexes():
    root = (EXTERNAL / "INDEX.md").read_text(encoding="utf-8")
    assert "スキップ" in root or "市販" in root
    github = (EXTERNAL / "github" / "INDEX.md").read_text(encoding="utf-8")
    assert "対象外" in github or "INBOX" in github


def test_knowledge_graph_registers_external_sources():
    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    ids = {n["id"] for n in graph["nodes"]}
    assert "source:input/external/INDEX.md" in ids
    assert "source:input/external/drive/INDEX.md" in ids
    assert "source:input/external/notion/INDEX.md" in ids
    assert any("input/external" in n["id"] for n in graph["nodes"] if n["type"] == "Source")


def test_media_manifest_and_ekiden_ocr():
    manifest = json.loads((EXTERNAL / "media-manifest.json").read_text(encoding="utf-8"))
    assert manifest["summary"]["ekiden_ocr"] >= 27
    assert manifest["summary"]["analysis_pdfs"] >= 3
    assert manifest["summary"]["photo_binaries"] >= 1
    ocr_dir = EXTERNAL / "notion" / "media" / "ekiden-history" / "ocr"
    assert ocr_dir.is_dir()
    assert len(list(ocr_dir.glob("*.md"))) >= 27
    sample = (ocr_dir / "2025-男子.md").read_text(encoding="utf-8")
    assert "岱明" in sample and "順位" in sample
    analysis = EXTERNAL / "drive" / "shared" / "分析"
    assert (analysis / "関係図_2026.pdf").is_file()
    assert (analysis / "関係図_2026.ocr.md").is_file()


def test_knowledge_graph_registers_media_assets_and_ekiden_topic():
    graph = build_knowledge_graph(generated_at="2026-01-01T00:00:00Z")
    ids = {n["id"] for n in graph["nodes"]}
    assert "topic:ekiden" in ids
    assert "source:input/external/media-manifest.json" in ids
    media_nodes = [n for n in graph["nodes"] if n["type"] == "MediaAsset"]
    assert len(media_nodes) >= 20
    ekiden_media = [n for n in media_nodes if n["id"].startswith("media:ekiden:")]
    assert len(ekiden_media) >= 20
    # LLM がパスを辿れること
    assert any(n.get("refs") for n in ekiden_media)
    assert any("ocr/" in (n.get("hint") or "") or any("ocr" in r for r in n.get("refs") or []) for n in ekiden_media)
