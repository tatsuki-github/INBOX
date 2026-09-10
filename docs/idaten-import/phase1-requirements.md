# Phase 1: 要求分析 — いだてん岱明データ集約

## ユーザーストーリー
コーチ／運営者として、Notion・Google ドライブ・関連リポジトリに散在するいだてん岱明関連データを INBOX リポジトリ一箇所で参照したい。理由は探索・回答・練習計画の根拠を断絶なく辿れるようにするため。

## 受け入れ条件
1. `input/external/` 配下に Drive / Notion / GitHub 由来のスナップショットが配置されている
2. `input/external/**/INDEX.md`（またはルート INDEX）にソース URL・パスの目録がある
3. 部員名簿・練習記録・主要 Notion DB（生徒・記録系）が機械可読（CSV/JSON/MD）で存在する
4. knowledge-graph が `input/external` を Source ノードとして参照できる
5. 無関係データ（学習指導要領・Colab・市販書籍全文）は取り込まない／スタブのみ

## テストマッピング
| AC | テスト |
|:---|:---|
| 1-3 | `tests/test_external_import.py` — 必須パス存在・名簿 CSV ヘッダ |
| 4 | KG 再生成後に `source:input/external` 系ノード or INDEX 参照 |
| 5 | INDEX に skip 理由が記載 |

## In / Out of Scope
| In | Out |
|:---|:---|
| 共有ドライブ `0APcRf6IAzVPGUk9PVA` | 音楽系リポジトリ（melodia 等） |
| 個人フォルダ「いだてん岱明（自分用）」 | 市販書籍 PDF 全文 |
| Notion ワークスペース「いだてん岱明」 | Notion ai_search / meeting notes（プラン外） |
| 既存 `out/analysis/notion_records_2026.json` の継続 | UI 新規開発 |

## 影響ドキュメント
- `README.md`（外部データ節）
- `AGENTS.md`（探索経路）
- `docs/adr/010-external-idaten-import.md`
- knowledge-graph ソース定義
