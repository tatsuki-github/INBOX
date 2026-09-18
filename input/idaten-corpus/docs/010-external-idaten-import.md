# ADR 010: いだてん岱明外部データのリポジトリ取り込み

## 状況
いだてん岱明の運用データが Notion・Google ドライブ（共有＋個人）に分散しており、INBOX だけでは探索が完結しない。

## 決定
1. スナップショットを `input/external/{drive,notion,github}/` に置く（正本は外部、リポは検索可能なコピー）。
2. 各ファイルに `.meta.json`（id, title, mimeType, viewUrl, modifiedTime）を併置する。
3. テキスト化可能な Google Docs/Sheets は MD/CSV で保存。巨大 PDF（>8MB）や市販書籍はメタデータスタブのみ。
4. Notion DB は schema + rows JSON を保存。カレンダー全件は既存 YAML 正本と重複するため INDEX リンク優先、差分補完のみ。
5. knowledge-graph の Source に `input/external/**` と INDEX を登録する。
6. **メディア例外（詳細は ADR 011）**: 荒玉駅伝結果画像・分析 PDF・フォト画像はバイナリ＋OCR を保存し、KG の `MediaAsset` からパス参照する。

## 不採用
| 案 | 理由 |
|:---|:---|
| Git LFS で全バイナリ | 運用コスト高。必要分のみ |
| 外部 API ライブ参照のみ | オフライン探索・CI 再現性がない |
| Notion カレンダー全ページ個別 MD | 件数過多。既存 `input/events.*.yaml` が正本 |

## テスト戦略
- 単体: 必須アーティファクト存在・名簿 CSV パース
- 回帰: `build_knowledge_graph.py --check`、既存 KG テスト
