# Phase 5–6: 2025 なごみ成績と予実

## 実装

- 成績表データ + MD/JSON
- `load_sb_index(as_of, gender, include_nighter=False)`
- 女子/男子 SB予想 MD/PDF と 予実比較 MD/PDF
- QueryHint「2025年のなごみ駅伝の結果は？」
- `岱明の結果.md` の山本哲瑠訂正

## QE5 / 検証

- [x] `pytest tests/test_nagomi_2025_sb_vs_actual.py`
- [x] `pytest scripts/test_nagomi_tamana_nighter_sb.py`（2026 デフォルト退行）
- [ ] `pytest tests/test_knowledge_graph.py`（コーパス再生成後）
- [ ] KG 再生成 + backend 同期

## R5 / Phase 6

- Critical=0（スキャン由来の氏名ゆれは SB 照合済みの分を校正、残りは成績表表記）
- **Approved**（検証コマンド完了後）
