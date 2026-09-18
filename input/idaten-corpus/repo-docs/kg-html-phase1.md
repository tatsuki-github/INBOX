# Phase 1 — 要求（差分）: KG 可視化 HTML

## ユーザーストーリー

コーチ／エージェント運用者として、ナレッジグラフをブラウザで眺めたい。なぜなら JSON だけではノード種別や参照関係を素早く確認しづらいから。

## 受け入れ条件

1. `python3 scripts/build_knowledge_graph.py` 実行後に `out/knowledge-graph.html` が存在する
2. HTML をブラウザで開くと、KG のノード／エッジが force グラフとして表示される（データ埋め込み、オフライン可）
3. ノード種別フィルタと文字列検索ができる
4. ノード選択時に label / hint / refs が表示される
5. 既存の JSON 生成・`--check`・pytest が退行しない

## テストマッピング

| 条件 | テスト |
|:---|:---|
| 1,2 | 単体: HTML 生成パス存在・埋め込みマーカー・CDN 参照 |
| 3,4 | 単体: HTML 内に filter/search/detail 用の要素 id がある |
| 5 | 回帰: 既存 test_knowledge_graph + `--check` |

## In / Out

| In | Out |
|:---|:---|
| 静的 HTML 生成・ビルダー連携・docs 更新 | SPA フレームワーク、編集機能、サーバ |
