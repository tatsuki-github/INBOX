# Phase 5–6: 実装・検証・統合レビュー — なごみ駅伝 プログラム/エントリー

## Phase 5 実装内容

| 成果物 | 内容 |
|:---|:---|
| `.../プログラム.pdf` + `.pdf.md` | 大会プログラム原本＋構造化（日程・招集・駐車場・応援） |
| `.../エントリーリスト.pdf` + `.pdf.md` | 男女エントリー＋岱明 A/B No. |
| `当日スケジュール.md` | 集合 **7:00**、チーム数、招集、駐車場、応援ルール |
| `開催要項.md` | 当日運用追記をプログラム/エントリー準拠に更新 |
| `input/events.2026.yaml` | なごみイベント description を同期 |
| 生成物 | corpus / rag_index / out/2026 / KG / backend KG sync |

TS コード変更なし（データ正本 + パイプライン再生成のみ）。

## QE5 / 検証

| 項目 | 結果 |
|:---|:---|
| `build_idaten_corpus.py` | 461 sources / 4661 chunks |
| `generate_calendar.py --year 2026` | 成功（KG 自動再生成含む） |
| `sync_backend_kg.py` | OK |
| `backend npm test` | 60/60 pass |
| AC1 集合7:00 | 正本・corpus・calendar・rag に反映。7:15 は「不採用」注記のみ |
| AC2–3 PDF 構造化 | プログラム／エントリー md 存在 |
| AC4 RAG | `集合7:00` 3 chunks、`岱明中学校 A` 3 chunks 等 |

## Docs Sync（QE5-7）

- `docs/implementation-flow/nagomi-2026-program-entry/phase-0.md`
- `docs/implementation-flow/nagomi-2026-program-entry/phase-1.md`
- `docs/implementation-flow/nagomi-2026-program-entry/phase-5-6.md`
- 新規 ADR なし（既存 Drive→corpus パイプラインの運用データ更新）

## Phase 6 統合レビュー

| 基準 | 判定 |
|:---|:---|
| A-1 要件カバレッジ | Pass（AC すべて充足） |
| A-2 章間整合 | Pass（開催要項＝スケジュール＝events） |
| A-5 Docs↔Code | Pass（データ正本と生成物一致） |
| B-6 / B-7 | Pass（vitest 全件、TS 変更なし） |
| Critical / Major | 0 |

**判定: Approved**

## スキップ確認（Lite）

Phase 2 / 4 スキップ妥当（UI なし）。Phase 3 は既存パイプライン再利用で簡略。
