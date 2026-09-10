# Phase 1: 要求分析（簡略）

## ユーザーストーリー

コーチ／分析者として、t-tsuchiyama の中学生 SB（全年度）を INBOX 内で横断検索したい。なぜなら Drive/Notion を都度開かずに年度比較・選手追跡ができるから。

## 受け入れ条件

1. ワイド中学生 SB（≥1000 行、カテゴリー=中学生）が `sb/middle-school/wide/` にある  
2. 2012〜2026年の15年度すべてに by-year SB採用JSONとstatusがある  
3. 15件の年度別生CSVが `drive/personal/t-tsuchiyama/sb/by-year/` にあり INDEX から辿れる  
4. 各年度の件数・SHA-256・年度境界をテストで検証できる  
5. KG に SB INDEX / ワイド CSV / ADR 012 が Source 登録される  

## テストマッピング

| AC | テスト |
|:---|:---|
| 1 | `test_middle_school_wide_sb_csv` |
| 2 | `test_middle_school_sb_year_artifacts_and_index` |
| 3 | `test_all_year_source_csvs_are_preserved` + INDEX 存在 |
| 4 | `test_all_year_generated_counts_and_hashes` |
| 5 | `test_knowledge_graph_registers_middle_school_sb` |

## In / Out

| In | Out |
|:---|:---|
| 中学生ワイド SB・年度別 SB採用 | 高校生・一般 SB |
| Drive/Notion スナップショット | GitHub 他リポ |
| INDEX / ADR / KG | UI |
