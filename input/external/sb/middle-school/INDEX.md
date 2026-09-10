# 中学生 SB（Season Best）— t-tsuchiyama パイプライン

所有者: `t-tsuchiyama@ilab.pu-kumamoto.ac.jp`（Drive / Notion 記録パイプライン。GitHub 公開リポではない）

正本は外部サービス。本ディレクトリは探索用スナップショット。

## 配置

| パス | 形式 | 内容 | 完全性 |
|:---|:---|:---|:---|
| [`wide/中学生SB.csv`](wide/中学生SB.csv) | ワイド（選手×距離） | Drive `SBデータベース` の `カテゴリー=中学生`（1371 行） | **complete**（現行シーズン正本） |
| [`by-year/`](by-year/) | 年度別・長形式 SB採用 JSON | `SBデータベース/data/output/output_YYYY_中学生_single_table.csv` | **complete**（2012〜2026） |

## 年度別SB

| 年度 | 入力行 | SB採用行 |
|---:|---:|---:|
| 2012 | 4,628 | 2,180 |
| 2013 | 4,219 | 2,046 |
| 2014 | 4,750 | 2,139 |
| 2015 | 5,252 | 2,181 |
| 2016 | 3,991 | 2,021 |
| 2017 | 4,982 | 2,431 |
| 2018 | 5,885 | 2,168 |
| 2019 | 5,733 | 2,065 |
| 2020 | 3,119 | 1,407 |
| 2021 | 4,421 | 1,968 |
| 2022 | 5,406 | 2,300 |
| 2023 | 6,463 | 2,267 |
| 2024 | 6,649 | 2,267 |
| 2025 | 7,395 | 2,662 |
| 2026 | 8,063 | 3,981 |

各年度の `YYYY-sb-adopted.status.json` に入力行数、SB採用行数、収録された暦年、
元CSVに含まれる Unicode 置換文字（`�`）の行数を記録する。年度はファイル名で判定し、
翌年1〜3月の記録も元ファイルの年度に保持する。

## ソース（Drive 生データ）

[`../drive/personal/t-tsuchiyama/sb/`](../drive/personal/t-tsuchiyama/sb/)

- `SBデータベース.csv` — 全カテゴリ 4900（中学生 1371）
- `中学生SB.csv` — 中学生フィルタ
- `by-year/YYYY-single-table.csv` — 2012〜2026年度の長形式エクスポート
- `output_all*.csv` / `output_reg_中学生_*.csv` — 現行年度のワイド／長形式エクスポート

## 再生成

```bash
python3 scripts/build_middle_school_sb_by_year.py
```

## 設計

[`docs/adr/012-middle-school-sb-all-years.md`](../../../docs/adr/012-middle-school-sb-all-years.md)
