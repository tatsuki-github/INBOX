# 外部ソース取り込み INDEX（いだてん岱明）

本ディレクトリは Notion / Google ドライブ / 他リポジトリから取得した **検索可能なスナップショット** です。正本は各外部サービスにあり、リポジトリは探索用コピーです。

| ソース | パス | 備考 |
|:---|:---|:---|
| Google ドライブ（共有＋個人） | [`drive/INDEX.md`](drive/INDEX.md) | Docs/Sheets は MD/CSV。分析 PDF・フォト画像はバイナリ可（ADR 011） |
| Notion（ワークスペース「いだてん岱明」） | [`notion/INDEX.md`](notion/INDEX.md) | DB schema + rows。駅伝メディアは [`notion/media/`](notion/media/) |
| メディア索引 | [`media-manifest.json`](media-manifest.json) | 画像・OCR・PDF のパス一覧（KG `MediaAsset`） |
| 中学生 SB（t-tsuchiyama） | [`sb/middle-school/INDEX.md`](sb/middle-school/INDEX.md) | ワイド＋年度別 SB採用。Drive/Notion 由来 |
| GitHub 他リポ | [`github/INDEX.md`](github/INDEX.md) | INBOX 以外は対象外 |

## スキップ方針

- 市販書籍 PDF 全文 → メタスタブのみ
- フォトの**動画** → メタスタブ（画像は保存）
- Colab / 学習指導要領 / Index.zip → 対象外
- Notion `query_data_sources` 上限時 → view モード＋search/fetch で補完（一部 DB は partial。詳細は notion/INDEX.md）
- 高校生・一般カテゴリの SB は本スライス対象外（中学生のみ）

## メディア（荒玉駅伝優先）

| 種別 | 状態 | パス |
|:---|:---|:---|
| 駅伝歴代 構造化 OCR | ✅ 27 件 | [`notion/media/ekiden-history/ocr/`](notion/media/ekiden-history/ocr/) |
| 駅伝歴代 画像 PNG | ⏳ Notion attachment 未配布（Drive 空） | [`notion/media/ekiden-history/`](notion/media/ekiden-history/) |
| 分析 PDF + OCR | ✅ 3 件 | [`drive/shared/分析/`](drive/shared/分析/) |
| フォト画像 | ✅ 29 件 | [`drive/shared/フォト/`](drive/shared/フォト/) |

設計: [ADR 010](../../docs/adr/010-external-idaten-import.md) / [ADR 011](../../docs/adr/011-idaten-media-ocr-kg.md) / [ADR 012](../../docs/adr/012-middle-school-sb-all-years.md)
