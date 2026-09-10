# 中学生 SB（Season Best）— t-tsuchiyama パイプライン

所有者: `t-tsuchiyama@ilab.pu-kumamoto.ac.jp`（Drive / Notion 記録パイプライン。GitHub 公開リポではない）

正本は外部サービス。本ディレクトリは探索用スナップショット。

## 配置

| パス | 形式 | 内容 | 完全性 |
|:---|:---|:---|:---|
| [`wide/中学生SB.csv`](wide/中学生SB.csv) | ワイド（選手×距離） | Drive `SBデータベース` の `カテゴリー=中学生`（1371 行） | **complete**（現行シーズン正本） |
| [`by-year/2024-sb-adopted.json`](by-year/2024-sb-adopted.json) | 長形式 SB採用 | Notion `2024年度中学生` の SB採用行 | エクスポート進行中（status 参照） |
| [`by-year/2025-sb-adopted.json`](by-year/2025-sb-adopted.json) | 長形式 SB採用 | Notion `2025年度中学生記録` partial から抽出 | **partial**（403 / 目標 ~2505） |
| [`by-year/2026-sb-adopted.json`](by-year/2026-sb-adopted.json) | 長形式 SB採用 | Drive + `output_reg` + Notion 補完 | **complete**（635） |
| [`by-year/2026-reg-sb.csv`](by-year/2026-reg-sb.csv) | 長形式 | Drive `output_reg_中学生_single_table` 由来 | complete |

## ソース（Drive 生データ）

[`../drive/personal/t-tsuchiyama/sb/`](../drive/personal/t-tsuchiyama/sb/)

- `SBデータベース.csv` — 全カテゴリ 4900（中学生 1371）
- `中学生SB.csv` — 中学生フィルタ
- `output_all*.csv` / `output_reg_中学生_*.csv` — ワイド／長形式エクスポート

## 設計

[`docs/adr/012-middle-school-sb-all-years.md`](../../../docs/adr/012-middle-school-sb-all-years.md)
