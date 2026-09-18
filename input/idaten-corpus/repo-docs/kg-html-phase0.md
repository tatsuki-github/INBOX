# Phase 0 — 作業種別記録: ナレッジグラフ可視化 HTML

| 項目 | 内容 |
|:---|:---|
| **機能要求** | 既存のリポジトリ検索ルート地図（`out/knowledge-graph.json`）をブラウザで見られる HTML 可視化を追加する |
| **作業種別** | `extend`（Lite Path） |
| **判定** | Q1 バグ否 / Q2 新機能あり → 改善のみではない / Q3 既存リポジトリへの追加 / Q4 契約破壊なし → **extend** |
| **技術スタック** | Python 生成スクリプト → 単一静的 HTML（CDN: vis-network）。既存 `scripts/knowledge_graph/` を拡張 |
| **検証対象** | Python（pytest）。フロントの npm なし |
| **Docs Sync** | 有効。Docs Root=`docs/`、ADR=`docs/adr/`（次番号 009） |
| **スキップ** | Phase 1/3 簡略化。Phase 2/4 は新規 HTML 画面のみ。既存 JSON ルーティング契約は不変 |

## ゴール

エージェント／人が `out/knowledge-graph.html` を開き、ノード種別・検索・参照パスを確認できる。

## Out of Scope

- Google ドライブ取り込み
- KG データモデルの破壊的変更
- 人間向けの装飾過多なランディング UI
