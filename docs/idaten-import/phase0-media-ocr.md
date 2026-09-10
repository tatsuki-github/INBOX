# Phase 0 — 作業種別記録（画像・OCR・KG）

## 作業種別
- **判定**: `extend`（Lite Path）
- **理由**: 既存 `input/external` 取り込みを拡張し、画像バイナリ・OCR・KG Media ノードを追加する。API/契約破壊なし。

## ゴール
荒玉駅伝で勝つために、いだてん岱明の**結果画像・分析資料・関連フォト**をリポジトリに保存し、OCR テキストとローカルパスをナレッジグラフから辿れるようにする。

## 技術スタック
- 既存: Python KG ビルダー、pytest、Notion/Drive MCP
- OCR: Google Drive `read_file_content` / contentSnippet（ローカル tesseract は任意フォールバック）

## Docs Sync
- 有効。Docs Root: `docs/`、ADR: `docs/adr/`（次番 011）

## スキップ
| Phase | 扱い |
|:---|:---|
| 2 UX | 新規 UI なし → スキップ（探索は INDEX/KG） |
| 4 UI | スキップ |

## 検証対象
- Python テスト + `build_knowledge_graph.py --check`（npm 対象外）
