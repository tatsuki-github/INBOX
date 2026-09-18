# リポジトリ知識コーパス（単一フォルダ）

LINE Q&A バックエンドが参照するテキスト専用コーパス（いだてん岱明＋荒玉＋分析＋docs）。
バイナリ（画像・PDF）は含めない。再生成: `python3 scripts/build_idaten_corpus.py`

## ディレクトリ

- `ekiden-ocr/` — 荒玉駅伝歴代 OCR
- `analysis-ocr/` — 分析 PDF の OCR
- `aragyoku/` — 荒玉構造化テキスト・優勝校要約・transcripts
- `out-analysis/` — `out/analysis` の md/json
- `repo-docs/` — docs 配下の Markdown
- `notion-db/` / `notion-pages/` — Notion スナップショット
- `drive-text/` — Drive テキスト
- `calendar/` / `practice/` — 岱明フィルタ済み予定・練習
- `sb/` — 中学生 SB（全所属。Drive SBデータベース wide）
- `docs/` — 関連 ADR・定義（抜粋）

ファイル数（SOURCES）: 543
