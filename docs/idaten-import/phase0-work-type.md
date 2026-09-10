# Phase 0: 作業種別記録（いだてん岱明データ集約）

## 作業種別
- **判定**: `extend`（Lite Path）
- **理由**: 既存 INBOX リポジトリへ外部ソース由来データを追加する拡張。API/契約破壊なし。

## ゴール
Notion・Google ドライブ共有ドライブ（いだてん）・関連個人フォルダ・関連リポジトリから、いだてん岱明に関係するデータを本リポジトリへ取り込み、検索可能な形で配置する。

## 技術スタック
- Python 3 / YAML・JSON・Markdown 正本
- Drive/Notion MCP 経由の読み取り・エクスポート
- 既存 `input/` / `out/analysis/` / knowledge-graph 連携

## Docs Sync
- **有効**: Docs Root = `docs/`
- ADR 永続化先: `docs/adr/`（次番号 010）

## 検証対象
- `backend`（Python テスト・`build_knowledge_graph.py --check`）
- frontend N/A

## スキップ
- Phase 2/4: 新規 UI なし（取り込み・索引のみ）→ 簡略
- Phase 1/3: Lite Path で簡略（配置 ADR は残す）

## Out of Scope（初回）
- 著作権のある市販 PDF の全文複製（例: ランナーズバイブル）— メタデータのみ
- 無関係な Colab/学習指導要領/Index.zip
- Notion Business 必須ツール（ai_search / meeting notes）
