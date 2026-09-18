# Phase 5–6: 実装・検証 — 荒玉駅伝試走カレンダー追加

## 実装内容
- `input/events.2026.yaml` に以下を追加（いずれも 09:00–12:00）
  - 2026-09-29 `荒玉駅伝試走`
  - 2026-10-07 `荒玉駅伝試走`
- タグ: `ランニング` / `荒玉駅伝` / `試走` / `岱明中`（コーパス daiming フィルタ通過用）
- `python3 scripts/generate_calendar.py --year 2026`（KG 自動再生成）
- `python3 scripts/sync_backend_kg.py`（`backend/data/knowledge-graph.json`）
- `python3 scripts/build_idaten_corpus.py`（`events.daiming.yaml` + `rag_index.json`）

## 受け入れ条件チェック

| # | 条件 | 結果 |
|:--|:-----|:-----|
| 1 | 9/29 午前試走 | OK（専用イベント追加。学校行事 description の言及とは別） |
| 2 | 10/7 午前試走 | OK |
| 3 | out/ + KG | OK（370 nodes） |
| 4 | backend KG sync --check | OK |
| 5 | 既存予定退行なし | OK（学校行事・本番 10/14 未変更） |

## 検証
- RAG: `calendar/events.daiming.yaml` チャンクに両日付あり
- `backend` `tests/answer.test.ts`: 6 passed
- 既知: `lint_events.py` は既存の「陸連登録番号: 3170 is not of type 'string'」で失敗（本変更外）

## QE / R（Lite 要約）
- QE0–QE1 / R0–R1: スコープ・受け入れ条件を phase-0/1 に固定 → Approved
- Phase 2/4: UI なしスキップ
- Phase 3: 既存 generate_calendar → sync_backend_kg → corpus パイプライン踏襲（新規 ADR なし）
- QE5 / R5 / Phase 6: 上記検証合格 → **Approved**
