# アーキテクチャ設計: KG 強化（差分）

Phase 2 / 4 はスキップ（UI なし）。既存パイプラインに差分追加。

```
Query → queryKnowledgeGraph (score + 2-hop)
      → mapRefsToCorpusSources
      → route / retrieve (既存 preferred ブーストは維持)
```

## アーキテクチャ特性（優先）

1. 検索精度（正本ダイジェストへ誘導）
2. 大会 disambiguation（ジュニア / なごみ / 金栗PROJECT）
3. 後方互換（既存 QueryHint・ジュニア回帰）
4. 運用単純性（ベクトルなし、builder 自動登録）
5. テスト容易性（KG query / mapRefs は純粋）

## コンポーネント

| 層 | 責務 | ファイル |
|:---|:---|:---|
| Business Logic | 分析 MD の Source 化・QueryHint・別名 | `scripts/knowledge_graph/builder.py` |
| Business Logic | ノードスコア（TS / Py 同期） | `backend/src/kg/query.ts`, `scripts/knowledge_graph/query.py` |
| Data Access | repo ref → corpus source | `backend/src/kg/mapRefs.ts` |
| Shared | 同梱 KG | `scripts/sync_backend_kg.py` |

UI Layer 変更なし。

## ファイル構成計画

- `scripts/knowledge_graph/builder.py` — `_register_analysis_digests`
- `backend/src/kg/mapRefs.ts` / `query.ts`
- `backend/tests/kgQuery.test.ts` / `mapRefs.test.ts`
- `tests/test_knowledge_graph.py`
- `docs/adr/046-kg-analysis-digest-routing.md`

テスト: `*.test.ts` / `test_knowledge_graph.py`

## ADR ドラフト

永続化は QE5-7 で `docs/adr/046-kg-analysis-digest-routing.md`。

判断: **out/analysis の md を Source 自動登録し、チームファイルは stem を label にする**。
不採用: 全 Source を全 Topic に全結合（ADR 031 どおり誤誘導）。retrieve の preferred をさらに増やすのは対症療法で、地図が薄いと Router が外れる。

## テスト戦略 ADR（併記）

| 分類 | 対象 | 配置 |
|:---|:---|:---|
| ドメイン | mapRefs 変換、KG スコア結果 | `backend/tests/mapRefs.test.ts`, `kgQuery.test.ts`, `tests/test_knowledge_graph.py` |
| コントローラ | answer/retrieve の既存ブースト | 既存回帰のみ（本スライスでロジック追加しない） |
| 取るに足らない | sync copy | テストなし |
| 過度に複雑 | なし | — |

ピラミッド: 単体（上記）中心。統合は backend `npm test` 全件。E2E（LINE 実機）は Out of Scope。

## QE3

- 3 層分離維持。循環依存なし。
- 金栗PROJECT をなごみ減点から外す設計を ADR に明記。

## R3

- **Approved** — 既存パターン踏襲、ADR + テスト戦略あり、Phase 1 AC と対応。
