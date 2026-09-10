# ADR 009: ナレッジグラフ可視化は生成静的 HTML + vis-network

## 状況

`out/knowledge-graph.json` は回答ルーティング用の機械可読地図として存在する。ユーザーがブラウザで構造を確認できる HTML も必要になった。

## 決定

1. `scripts/knowledge_graph/` が JSON と同時に **`out/knowledge-graph.html`** を生成する。
2. データは HTML 内に埋め込む（`file://` でも動くようにする。外部 fetch に依存しない）。
3. 描画は **vis-network**（CDN）の force-directed グラフとする。
4. UI は運用ツール向け: 種別フィルタ、検索、選択ノードの hint/refs 表示。美しさより探索性。

## 不採用

| 案 | 理由 |
|:---|:---|
| React/Next アプリ | リポジトリが Python INBOX。依存・ビルドを増やさない |
| D3 自前力指向 | 実装コスト高。vis-network で十分 |
| JSON を fetch | ローカル file オープン時に CORS/file 制約で失敗しやすい |

## テスト戦略

- 単体: HTML 生成物に埋め込み JSON・必須 DOM id・vis-network CDN 参照があること
- 回帰: 既存 `tests/test_knowledge_graph.py` Green、`--check` は JSON 比較のまま（HTML は生成検証のみ）
- 配置: `tests/test_knowledge_graph.py` に HTML ケース追加
