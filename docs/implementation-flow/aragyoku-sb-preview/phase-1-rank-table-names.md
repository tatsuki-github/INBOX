# Phase 1/5/6: 総合順位表に選手名

## 受け入れ条件

1. `fmt_leg_pred_cell` が選手名（空白除去）を先頭に付ける
2. 総合順位 MD の各区セルに名前が入る
3. 凡例が `選手名 (通過順)通過予想 / (区間順)区間記録` になる

## 実装

- `scripts/generate_aragyoku_ekiden_sb_preview.py` の `fmt_leg_pred_cell`
- テスト `TestRankTableNames`
- ADR 056 追記・再生成 dual-write

## 検証

58 tests OK。例: `松野凛空 (4)9:20.0 / (4)9:20.0`
