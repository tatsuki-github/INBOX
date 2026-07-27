---
name: pdf-convert
description: >
  PDF / DOCX / PPTX 等のドキュメントを高品質な Markdown に変換し、案件の inbox に配置する。
  Docling（ローカル実行）によるテーブル・数式・コード認識、OCR 対応。
  Use when user says「PDFを変換して」「inboxに取り込んで」「ドキュメントをMarkdownにして」
  「RFPをMarkdownに変換して」「顧客資料を変換して」「OCRで変換して」「一括変換して」。
allowed-tools: "Bash(python:*)"
metadata:
  author: KC-Prop-Foundry
  version: 2.0.0
  category: document-conversion
---

# Skill: PDF → Markdown 変換 (pdf-convert)

> **構造を読み解き、知識を取り込む — すべてはテキストから始まる**

CRITICAL: 本スキル実行時は、対象案件の `projects/<案件名>/` を明示すること。

## Instructions

### ワークフロー内の位置

```
顧客 PDF/DOCX/PPTX → [pdf-convert] → distill → 成果物作成
                           ↓
               projects/<案件名>/01_inbox/*.md
```

### 入力

| 形式 | 構造認識 | OCR | 備考 |
|:---|:---|:---|:---|
| PDF（テキスト） | テーブル・数式・コード | — | 最も一般的 |
| PDF（スキャン） | テーブル | `--ocr` 必須 | 紙スキャン文書 |
| DOCX | テーブル | — | 議事録・仕様書 |
| PPTX | スライド | — | プレゼン資料 |
| XLSX | テーブル | — | データ定義書 |
| HTML | 構造 | — | Web ページ |
| PNG/JPG/TIFF/BMP | — | `--ocr` 推奨 | ホワイトボード写真等 |

### 出力

```markdown
---
source: "元のファイル名.pdf"
converted_at: "2026-02-11T12:30:00.000000"
converter: "docling"
---

# ドキュメントタイトル

（変換されたコンテンツ）
```

出力先: `projects/<案件名>/01_inbox/<元ファイル名>.md`

---

## Step 1: 変換前の確認

**チェックリスト**:
- ファイル形式は対応形式か（PDF, DOCX, PPTX, XLSX, HTML, 画像）
- ファイルはパスワード保護されていないか
- PDF の場合: テキスト選択が可能か（不可能なら `--ocr` が必要）
- ファイルサイズが極端に大きくないか（100MB 以上は分割を検討）
- 対象の案件ディレクトリ（`projects/<案件名>/`）が存在するか

**判断フロー**:
```
ファイル受領
  ├── テキスト選択可能？ → Yes → 通常変換（Step 2a）
  │                    → No  → OCR 変換（Step 2b）
  ├── 複数ファイル？   → Yes → 一括変換（Step 2c）
  └── 特殊要件？       → テーブルが重要 → デフォルト（テーブル認識 ON）
                       → 速度重視     → --no-tables オプション
```

---

## Step 2a: 通常の単一ファイル変換

```bash
python scripts/convert_to_md.py <ファイルパス> --project <案件名>
```

例:
```bash
python scripts/convert_to_md.py "C:\Downloads\RFP_教育データ基盤.pdf" --project education-data-platform
```

---

## Step 2b: OCR 変換（スキャン PDF / 画像）

```bash
python scripts/convert_to_md.py <ファイルパス> --project <案件名> --ocr
```

注意: OCR は処理時間が長い（ページ数に依存）。テキスト埋め込み済みの PDF には `--ocr` を使用しないこと。

---

## Step 2c: 一括変換（ディレクトリ）

```bash
python scripts/convert_to_md.py <ディレクトリパス> --project <案件名>
```

---

## Step 3: 変換結果の品質確認

**チェックリスト**:
- 文書の見出し階層（#, ##, ###）が正しいか
- テーブルの列数・行数が元文書と一致するか
- 数式・コードブロックが正しく変換されているか
- 図表のキャプションが正しく抽出されているか
- ページ番号・ヘッダー・フッターが混入していないか
- 文字化け・文字欠けがないか
- 箇条書きのインデントが保持されているか

**よくある修正パターン**:

| 現象 | 原因 | 対処 |
|:---|:---|:---|
| テーブルの列ズレ | 複雑なセル結合 | 手動で Markdown テーブルを修正 |
| ヘッダー/フッター混入 | PDF のレイアウト認識 | 該当行を削除 |
| 数式の文字化け | 特殊フォントの未認識 | LaTeX 形式で再記述 |
| 箇条書きの崩れ | インデント認識の限界 | 手動でインデントを修正 |

---

## Step 4: 後続スキルへの引き渡し

変換・確認が完了したら、`distill` スキルに引き渡す:
```
「distill スキルで、inbox の資料を notes に蒸留して」
```

---

## Advanced Options

### Docling CLI の直接利用

```bash
docling input.pdf              # 基本変換
docling input.pdf --to md      # Markdown 出力
docling input.pdf --to json    # JSON（ロスレス）
docling --pipeline vlm --vlm-model granite_docling input.pdf  # VLM 高精度変換
```

### Python API

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("path/to/file.pdf")
markdown = result.document.export_to_markdown()
```

---

## Examples

### Example 1: RFP の変換

```
「pdf-convert スキルで、顧客から受領した RFP.pdf を education-data-platform の inbox に変換して」
```

### Example 2: 顧客資料フォルダの一括変換

```
「pdf-convert スキルで、C:\Downloads\顧客資料\ フォルダを education-data-platform に一括変換して」
```

### Example 3: スキャン文書の OCR 変換

```
「pdf-convert スキルで、紙スキャンの仕様書を OCR で変換して inbox に配置して」
```

---

## Troubleshooting

| 問題 | 原因 | 解決策 |
|:---|:---|:---|
| `ModuleNotFoundError: docling` | 未インストール | `pip install docling` |
| 初回実行が遅い | ML モデルダウンロード中 | 初回のみ。1-5 分待機 |
| テーブルが崩れる | 複雑なセル結合・入れ子 | 手動修正、または VLM で再試行 |
| OCR 文字化け | 低品質スキャン | 高解像度再スキャン、VLM モデル試行 |
| `案件が見つかりません` | 存在しない案件名 | `ls projects/` で確認。`_template` からコピー |
| メモリ不足 | 大規模 PDF | ファイルを分割して変換 |

---

## Security Notes

- Docling はすべてローカルで処理。顧客の機密 PDF が外部サーバーに送信されることはない
- VLM 使用時: `granite_docling` モデルもローカル動作。クラウド VLM 使用時は機密性に注意

## Related Files

| ファイル | 役割 |
|:---|:---|
| `scripts/convert_to_md.py` | 変換スクリプト本体 |
| `requirements.txt` | Python 依存定義（`docling>=2.70.0`） |
| `.agent/workflows/convert-pdf.md` | エージェントワークフロー定義 |
| `shared/05_decision_log/ADR-002-docling-pdf-conversion.md` | 設計判断記録 |

## Related Skills

| スキル | 関係 | 説明 |
|:---|:---|:---|
| **distill** | 後続 | `01_inbox/` の Markdown を `02_notes/` に蒸留 |
| **review** | 検証 | 変換結果の品質をレビュー |
| **data-validation** | 検証 | テーブルデータの整合性チェック |
