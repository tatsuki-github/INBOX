# ADR 012: t-tsuchiyama 中学生 SB 全年度の取り込み

## 状況

中学生の Season Best（SB）が Drive（`SBデータベース` / `output_reg_*`）と Notion（年度別大会記録 DB）に分散している。
「t-tsuchiyama リポジトリ」は GitHub 公開リポではなく、所有者 `t-tsuchiyama@ilab.pu-kumamoto.ac.jp` の Drive/Notion 記録パイプラインを指す。
INBOX で年度横断の選手記録探索を完結させたい。

## 決定

1. 正規化スナップショットを `input/external/sb/middle-school/` に置く。
   - `wide/` — 選手×距離の現行ワイド SB（Drive `SBデータベース` の中学生フィルタを正本）
   - `by-year/YYYY-sb-adopted.*` — 年度別・長形式の SB採用行
2. 生データは `input/external/drive/personal/t-tsuchiyama/sb/` に併置（`.meta.json` 付き）。
3. Notion 年度 DB（2024/2025/2026）は既存 `input/external/notion/databases/` に schema + rows。SQL 上限時は view ページング。partial は `export.status.json` / `*.status.json` で明示。
4. knowledge-graph の Source に `sb/middle-school/INDEX.md` とワイド CSV を登録する。
5. GitHub 他リポは対象外（ADR 010 踏襲）。

## 不採用

| 案 | 理由 |
|:---|:---|
| ワイドだけを年度別コピー | 年度別の大会・日付・SB採用フラグが失われる |
| Notion ライブ参照のみ | オフライン探索・CI 再現性がない |
| 高校生・一般カテゴリまで同 PR | スコープ超過。中学生 SB に限定 |

## テスト戦略

- 単体: ワイド中学生 CSV の行数・ヘッダ・カテゴリー、by-year status の存在
- 回帰: `build_knowledge_graph.py --check`、既存 `test_external_import`
