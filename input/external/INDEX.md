# 外部ソース取り込み INDEX（いだてん岱明）

本ディレクトリは Notion / Google ドライブ / 他リポジトリから取得した **検索可能なスナップショット** です。正本は各外部サービスにあり、リポジトリは探索用コピーです。

| ソース | パス | 備考 |
|:---|:---|:---|
| Google ドライブ（共有＋個人） | [`drive/INDEX.md`](drive/INDEX.md) | Docs/Sheets は MD/CSV。巨大 PDF はメタのみ |
| Notion（ワークスペース「いだてん岱明」） | [`notion/INDEX.md`](notion/INDEX.md) | DB schema + rows。カレンダー全件は既存 YAML 正本 |
| GitHub 他リポ | [`github/INDEX.md`](github/INDEX.md) | INBOX 以外は対象外 |

## スキップ方針

- 市販書籍 PDF 全文 → メタスタブのみ
- フォトフォルダの画像バイナリ → リンクのみ
- Colab / 学習指導要領 / Index.zip → 対象外
- Notion `query_data_sources` 上限時 → view モード＋search/fetch で補完（一部 DB は partial。詳細は notion/INDEX.md）

設計: [`docs/adr/010-external-idaten-import.md`](../../docs/adr/010-external-idaten-import.md)
