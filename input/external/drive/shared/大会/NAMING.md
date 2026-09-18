# 大会フォルダ・ファイル命名規約

リポジトリ内の `drive-text/大会/`（および正本 `input/external/drive/shared/大会/`）で、人が辿りやすく・KG / Q&A が拾いやすい名前に揃える。

## フォルダ

```
大会/
  {YYYY}年度/
    {MMDD}_{大会名}/
    {MMDD}-{MMDD}_{大会名}/   # 複数日
```

- 大会名は通称でよいが、**検索に使う語を含める**（例: 荒玉・ジュニア・なごみ）。
- 別名がある場合は括弧で併記: `1015_荒玉中体連駅伝（玉名荒尾）`。

## クラブ結果（必須の正規名）

大会フォルダ**直下**:

```
岱明の結果.md
```

別名（`結果.md` / `いだてん岱明結果.md` / `{大会名}_岱明の結果.md` / `結果/いだてん岱明の結果.md`）は使わない。

## その他のクラブ文書

| 用途 | 正規名 |
|:-----|:-------|
| 出場 | `岱明の出場.md` |
| 出場予定 | `岱明の出場予定.md` / `岱明の出場予定.pdf.md` |
| 参加計画 | `岱明の参加計画.pdf.md` |

## 公式結果・OCR

- `結果_*.pdf.md`（種目別）
- または `結果/` 配下の種目別 OCR（クラブ要約は直下の `岱明の結果.md` に置く）

## 根拠

- KG builder は `岱明の結果.md` を meet ノードの preferred ref にする（`scripts/knowledge_graph/builder.py`）
- LINE Q&A の `meetResultPathBoost` はパスに `岱明の結果` があると加点（`backend/src/domain/meets.ts`）
- 詳細: `docs/adr/019-meet-naming-convention.md`
