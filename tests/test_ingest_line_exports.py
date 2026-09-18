"""Tests for scripts/ingest_line_exports.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ingest_line_exports.py"


def _load():
    spec = importlib.util.spec_from_file_location("ingest_line_exports", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_redact_phone_and_postal():
    mod = _load()
    text = mod.redact("連絡先 080-1547-2025 〒869-0224 玉名市岱明町大野下173-1")
    assert "[電話番号]" in text
    assert "[郵便番号]" in text
    assert "[住所]" in text
    assert "080-1547" not in text


def test_parse_keeps_ops_drops_join():
    mod = _load()
    sample = """[LINE] 岱明中長距離のトーク履歴
保存日時：2026/09/18 22:09

2026/09/16(水)
19:28	熊澤先生	和水町三加和公民館に7時集合でお願いします。
19:29		⁨⁨誰か⁩⁩がグループに参加しました。
19:30	熊澤先生	[写真]
"""
    title, saved, messages = mod.parse_line_export(sample)
    assert "岱明中長距離" in title
    assert saved.startswith("2026")
    texts = [m.text for m in messages]
    assert any("三加和" in t for t in texts)
    assert not any("参加しました" in t for t in texts)
