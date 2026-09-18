# Phase 1: 要求分析 — なごみ駅伝 プログラム/エントリー取り込み

## ユーザーストーリー

コーチ／保護者として、なごみ駅伝の **正しい集合時刻（7:00）** と、プログラム・エントリーリストに載っている当日情報をリポジトリと LINE Q&A から知りたい。なぜならホワイトボード誤記や未取り込み PDF だと、集合や駐車場でミスるから。

## 受け入れ条件

1. 正本（`開催要項.md` / `当日スケジュール.md` / `input/events.2026.yaml`）の集合が **7:00** であり、7:15 を正としていない
2. `プログラム.pdf.md` に日程・招集・駐車場・応援ルールが構造化されている
3. `エントリーリスト.pdf.md` に男子38・女子25チームと岱明 A/B の No. が記載されている
4. `input/idaten-corpus` と `backend/data/rag_index.json` に上記テキストが反映されている
5. カレンダー生成物（`out/2026`）のなごみイベント説明に集合 7:00 と追加情報が含まれる

## テストマッピング

| AC | 検証 |
|:---|:---|
| 1 | ソース grep: なごみフォルダに「集合.*7:15」なし、「集合.*7:00」あり |
| 2–3 | ファイル存在 + 必須キーワード存在チェック |
| 4 | corpus パス存在 + rag_index に「集合7:00」「岱明中学校 A」等が含まれる |
| 5 | `generate_calendar.py --year 2026` 成功後、events 説明に 7:00 |

## In / Out of Scope

Phase 0 と同義。

## 影響ドキュメント

- `input/external/drive/shared/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/*`
- `input/events.2026.yaml`
- `input/idaten-corpus/`（生成）
- `backend/data/rag_index.json`（生成）
- `out/2026/*` / `out/knowledge-graph.json`（生成）
- `docs/implementation-flow/nagomi-2026-program-entry/`

## 技術アプローチ

1. pymupdf で PDF テキスト抽出 → 人手で構造化 Markdown
2. 既存 Drive フォルダへ PDF + md 配置（corpus は `.md` のみコピー）
3. `build_idaten_corpus.py` → `generate_calendar.py --year 2026` → `build_knowledge_graph.py` → `sync_backend_kg.py`
4. backend `npm test` で退行確認
