# ADR 012: t-tsuchiyama 中学生 SB 全年度の取り込み

## 状況

中学生の Season Best（SB）が Drive（`SBデータベース` / `output_reg_*`）と Notion（年度別大会記録 DB）に分散している。
「t-tsuchiyama リポジトリ」は GitHub 公開リポではなく、所有者 `t-tsuchiyama@ilab.pu-kumamoto.ac.jp` の Drive/Notion 記録パイプラインを指す。
INBOX で年度横断の選手記録探索を完結させたい。

当初は Notion の年度 DB から2024〜2026年を合成していたが、元パイプラインの
`data/output` に2012〜2026年度の長形式CSVが揃っていることが確認できた。

## 決定

1. 正規化スナップショットを `input/external/sb/middle-school/` に置く。
   - `wide/` — 選手×距離の現行ワイド SB（Drive `SBデータベース` の中学生フィルタを正本）
   - `by-year/YYYY-sb-adopted.*` — 2012〜2026年度の長形式 SB採用行
2. 年度別の正本は
   `input/external/drive/personal/t-tsuchiyama/sb/by-year/YYYY-single-table.csv`
   とし、`scripts/build_middle_school_sb_by_year.py` で決定的に再生成する。
3. 年度は行の日付ではなく、元CSVのファイル名で判定する。これによりシーズン末の
   翌年1〜3月の記録を元年度に保持する。
4. 元CSVの `SB採用=true` 行だけを採用し、出力では `__YES__` に正規化する。
   元データに存在するUnicode置換文字は推測修復せず、statusの
   `replacement_character_rows` で可視化する。
5. knowledge-graph の Source に `sb/middle-school/INDEX.md` とワイド CSV を登録する。
6. GitHub 他リポは対象外（ADR 010 踏襲）。

## 不採用

| 案 | 理由 |
|:---|:---|
| ワイドだけを年度別コピー | 年度別の大会・日付・SB採用フラグが失われる |
| Notion ライブ参照のみ | オフライン探索・CI 再現性がない |
| 行の日付年で年度を分割 | 翌年1〜3月を含む元パイプラインのシーズン区分を壊す |
| 文字化けを推測置換 | 選手名・所属名を誤修正するリスクがある |
| 高校生・一般カテゴリまで同 PR | スコープ超過。中学生 SB に限定 |

## テスト戦略

- 単体: 15年度の入力件数・SB採用件数、必須列、カテゴリー、フラグ正規化、
  翌暦年レコードの保持、未対応年度
- 統合: 2012〜2026年のJSON/status/元CSVの存在と件数整合
- 回帰: `build_knowledge_graph.py --check`、既存 `test_external_import`
