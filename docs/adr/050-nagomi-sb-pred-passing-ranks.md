# ADR 050: なごみ SB 予想表に通過順位・区間順位を付与

- Status: Accepted
- Date: 2026-09-19

## Context

なごみ駅伝の成績表は各区に「(通過順)通過タイム / (区間順)区間記録」が載る。
SB 予想 MD/PDF（2025・2026）は区間予想タイムだけで、通過順位が見えなかった。

## Decision

1. 参考順位対象チーム間で各区の予想区間順位・通過順位を計算する。
2. 完全記録のみ順位は別ピアで `_full` 接尾辞の順位を持つ（上書きしない）。
3. 順位表セルは `(通過順)通過予想 / (区間順)区間記録`。中央値補完の区間記録は括弧付き。
4. チーム別詳細に「通過予想 / 通過順 / 区間順」列を追加する。
5. 2025・2026 とも同じ `generate_nagomi_order_sb_preview.py` の描画を使う。

## Consequences

- 再生成: `python3 scripts/generate_nagomi_order_sb_preview.py`（2026）
  と `python3 scripts/generate_nagomi_2025_sb_vs_actual.py`（2025）
- 同タイムは安定ソート順（入力順）で順位が分かれる。
