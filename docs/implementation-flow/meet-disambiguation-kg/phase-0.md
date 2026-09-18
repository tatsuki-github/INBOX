# Phase 0: 作業種別 — 大会種別の誤誘導修正（ジュニア≠荒玉）

| 項目 | 値 |
|:---|:---|
| 作業種別 | `extend`（Lite Path）※誤答修正だがルーティング/KG 設計変更が必要 |
| ゴール | 「去年のジュニア駅伝の岱明の結果」等で荒玉結果が返らないこと。なごみ等の類似誤誘導も防ぐ |
| 検証 | `backend` test + build |
| Docs Sync | `docs/adr/` + implementation-flow |

## 原因（調査）

`boostEkidenYearSources` が `/駅伝/` だけで aragyoku transcripts を先頭注入するため、ジュニア質問でも荒玉が優先される。

## スキップ

Phase 2/4 スキップ（UI なし）
