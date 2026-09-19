# Phase 1: 2025 なごみ成績 × レース前 SB

## ユーザーストーリー

コーチとして、2025 なごみの全チーム区間記録をリポジトリで参照し、
当時の SB 換算予想が実績からどれだけ外れたかを見たい。
2026 の予想式を過大評価しないため。

## 受け入れ条件

1. 女子 16+OP、男子 34+OP が成績表 MD に載り、岱明女子 31:22・男子A 41:42・男子B 47:37 が一致する。
2. SB 予想は `2025-sb-adopted` かつ日付 ≤ 2025-09-20。村上咲稀の 11 月 1500 は使わない。
3. `予実比較.md/.pdf` に実績・予想・差がチームと区間で出る。
4. コーパス / KG から 2025 なごみ成績表へ辿れる。

## テストマッピング

| 条件 | テスト |
|:-----|:-----|
| 岱明既知タイム | `test_daimyo_women_matches_known_memo` |
| 哲瑠 | `test_daimyo_men_b_is_tetsuru_not_satoru` |
| 区間合計 | `test_official_totals_equal_split_sum` |
| as_of | `test_as_of_excludes_post_race_1500` |
| 生成物 | `test_generated_preview_and_gap_files_exist` |
| KG | `test_query_routes_nagomi_2025_results` |

## In / Out

- In: 文字起こし、Drive/corpus、SB 予想 MD/PDF、予実、ADR 049、KG hint
- Out: 2026 予想式の変更、LINE UI、ベクトル DB、自動コミット
