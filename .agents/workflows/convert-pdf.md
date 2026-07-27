---
description: PDF/ドキュメントを Markdown に変換して 01_inbox に配置する（エンジニアリングワークフローの Phase 0）
---

# PDF → Markdown 変換ワークフロー

> エンジニアリングワークフロー全体については [engineering-workflow.md](engineering-workflow.md) を参照。

## 前提条件

1. Python 3.10 以上がインストールされていること
```bash
python --version
```

2. docling がインストールされていること
```bash
pip install docling
```

## 変換手順

### 単一ファイルを案件の 01_inbox に配置

```bash
python scripts/convert_to_md.py <PDFファイルパス> --project <案件名>
```

### 複数ファイルを一括変換

```bash
python scripts/convert_to_md.py <PDFディレクトリ> --project <案件名>
```

### スキャン PDF の変換（OCR 有効）

```bash
python scripts/convert_to_md.py <スキャンPDF> --project <案件名> --ocr
```

## 変換後の作業

1. 01_inbox に配置された Markdown ファイルの品質を確認
2. `distill` スキルで 01_inbox の内容を 02_notes に蒸留

```
「distill スキルで、01_inbox の資料を 02_notes に蒸留して」
```

以降の工程（distill → story-map → 実装 → 品質検証 → リリース）は [engineering-workflow.md](engineering-workflow.md) を参照。
