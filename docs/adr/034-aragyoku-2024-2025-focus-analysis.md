# ADR 034: 荒玉 2024–2025 4校深掘り分析と KG QueryHint

## 状況

2024/2025 荒玉駅伝について、岱明・玉名付属（transcript 表記は玉高附属）・天水・有明への
前年比・区間・区間新の質問に、チーム別 MD の表だけでは読み取りが薄く、KG も概要・歴代に寄りがちだった。

## 決定

1. **生成スクリプト** `scripts/generate_aragyoku_2024_2025_focus_analysis.py`
   - 正本: `out/analysis/aragyoku_2024_2025_focus_teams.md`
   - transcripts から 4 校の区間明細・前年比・優勝差・読み取りを生成
2. **チーム MD**（岱明 / 玉高附属 / 天水 / 有明）に 2024–2025 前年比セクションを追記
3. **KG**: SourceDocument + QueryHint（玉名付属エイリアス含む）を `builder.py` に登録
4. **corpus**: `build_idaten_corpus.py` の再生成対象に focus 分析スクリプトを追加

## 不採用

| 案 | 理由 |
|:---|:---|
| 手書きのみの Markdown | 再生成時に transcripts と乖離する |
| 全校に同レベルの読み取り | スコープ過大。本スライスは指定 4 校 |

## 結果

- 再実行:
  - `/opt/miniconda3/bin/python scripts/generate_aragyoku_2024_2025_focus_analysis.py`
  - `/opt/miniconda3/bin/python scripts/generate_team_record_markdowns.py --aragyoku-only`
  - `/opt/miniconda3/bin/python scripts/build_knowledge_graph.py`
  - `/opt/miniconda3/bin/python scripts/build_idaten_corpus.py`（out-analysis 同期）

## 関連

- ADR 016（KG 先行）、027（チーム別 MD）、031（QueryHint）
