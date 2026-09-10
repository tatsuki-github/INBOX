# 中学生SB 2012〜2026年度取り込み

## Phase 0 — 作業種別

- 種別: `extend`（Lite Path）
- ゴール: t-tsuchiyama `SBデータベース/data/output` の年度別CSVを正本として、
  2012〜2026年度のSB採用データを再生成可能な形で保存する
- 技術: Python 3 / CSV / JSON / pytest
- 検証対象: データ処理スクリプトと外部データ取り込みテスト
- Docs Sync: 有効（`docs/`、ADRは `docs/adr/`）
- Phase 2 / 4: UIを変更しないためスキップ
- R0: Approved（単一データワークフローで、既存契約を破壊しない）

## Phase 1 — 要求と受け入れ条件

ユーザーストーリー: 記録を分析する利用者として、全年度の中学生SBを同じ形式で
参照したい。なぜなら駅伝選手の同年トラック走力を年度横断で比較したいから。

| 受け入れ条件 | テスト |
|:---|:---|
| 添付された2012〜2026年度の15ファイルが保存される | 統合テストで全元CSVの存在を確認 |
| 各年度で `SB採用=true` の全行がJSONになる | 年度別の入力・採用件数を単体テスト |
| 翌年1〜3月を含むシーズン区分が維持される | 2012年度に2013年日付が残ることを単体テスト |
| 必須列欠落や未対応年度を黙って処理しない | 異常系単体テスト |
| 文字化けの存在を隠さない | statusに置換文字を含む行数を記録 |

R1: Approved（全条件が自動テストへ対応済み）。

## Phase 3 — 設計

入力CSV → スキーマ検証 → 中学生・SB採用行抽出 → フラグ正規化 →
安定ソート → 年度別JSON/status、という一方向パイプラインとする。
年度境界とテスト戦略は ADR 012 に記録した。

R3: Approved（外部入力、ドメイン変換、永続出力の責務が分離されている）。

## Phase 5 / 6 — 実装・統合レビュー

- 生成器: `scripts/build_middle_school_sb_by_year.py`
- 単体テスト: `tests/test_build_middle_school_sb_by_year.py`
- 統合テスト: `tests/test_external_import.py`
- 永続仕様: `input/external/sb/middle-school/INDEX.md`
- ADR: `docs/adr/012-middle-school-sb-all-years.md`

品質ゲートはテスト、生成物再生成差分、knowledge graph checkで検証する。
