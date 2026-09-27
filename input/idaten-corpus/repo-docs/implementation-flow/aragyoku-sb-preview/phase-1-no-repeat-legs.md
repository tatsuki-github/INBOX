# Phase 1（簡略）: 同一選手複数区間禁止＋一昨年復帰

## ユーザーストーリー
コーチとして、仮区間オーダーで同一選手が複数区間に出ないようにし、不足は去年・一昨年の復帰候補で埋めたい。現実的なオーダー予想にするため。

## 受け入れ条件
1. 任意校の仮オーダーで、空欄以外の選手名に重複がない
2. 候補不足の区間は空欄（欠測）であり、同一名の繰り返しで埋めない
3. `load_prior_year_returners` は 2025（学年1–2）と 2024（学年1）を含む
4. 玉陵女子などプールが足りる校はユニーク選手で全区間を埋める

## テストマッピング
| AC | テスト |
|:---|:---|
| 1–2 | `test_no_duplicate_athletes_across_legs`, `test_legs_from_ranked_no_repeat_when_short` |
| 3 | `test_load_includes_grade_1_2_only`, `test_eligible_max_grade` |
| 4 | `test_redistribute_builds_nagasu_men_and_women_clubs`（玉陵に居石） |

## In / Out
- In: legs 配置、prior-year ローダ、build_team 空欄、ADR056、再生成 dual-write
- Out: 公式オーダー、中央値補完の復活、UI
