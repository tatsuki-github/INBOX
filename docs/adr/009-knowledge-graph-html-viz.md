# ADR 009: ナレッジグラフ可視化は生成静的 HTML + vis-network

## 状況

`out/knowledge-graph.json` は回答ルーティング用の機械可読地図として存在する。ユーザーがブラウザで構造を確認できる HTML も必要になった。

## 決定

1. `scripts/knowledge_graph/` が JSON と同時に **`out/knowledge-graph.html`** を生成する。
2. 同じ生成で **`out/knowledge-graph.pdf`**（印刷用ノード一覧スナップショット）も出力する。
3. データは HTML 内に埋め込む（`file://` でも動くようにする。外部 fetch に依存しない）。
4. 描画は **vis-network**（CDN）の force-directed グラフとする。
5. UI は運用ツール向け: 種別フィルタ、検索、選択ノードの hint/refs 表示。美しさより探索性。
6. PDF は ReportLab + リポジトリ同梱 NotoSansJP（対話グラフではなく一覧）。

## 不採用

| 案 | 理由 |
|:---|:---|
| React/Next アプリ | リポジトリが Python INBOX。依存・ビルドを増やさない |
| D3 自前力指向 | 実装コスト高。vis-network で十分 |
| JSON を fetch | ローカル file オープン時に CORS/file 制約で失敗しやすい |

## テスト戦略

- 単体: HTML 生成物に埋め込み JSON・必須 DOM id・vis-network CDN 参照があること
- 単体: PDF が `%PDF` ヘッダを持ち十分なサイズであること
- 回帰: 既存 `tests/test_knowledge_graph.py` Green、`--check` は JSON 比較のまま（HTML/PDF は生成検証）
- 配置: `tests/test_knowledge_graph.py` に HTML / PDF ケース追加
