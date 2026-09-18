# いだてん岱明コーパス（単一フォルダ）

LINE Q&A バックエンドが参照するテキスト専用コーパス。
バイナリ（画像・PDF）は含めない。再生成: `python3 scripts/build_idaten_corpus.py`

## ディレクトリ

- `ekiden-ocr/` — 荒玉駅伝歴代 OCR
- `analysis-ocr/` — 分析 PDF の OCR
- `aragyoku/` — 荒玉構造化テキスト
- `notion-db/` / `notion-pages/` — Notion スナップショット
- `drive-text/` — Drive テキスト
- `calendar/` / `practice/` / `sb/` — 岱明フィルタ済み予定・練習・SB
- `docs/` — 関連 ADR・定義

ファイル数（SOURCES）: 411
