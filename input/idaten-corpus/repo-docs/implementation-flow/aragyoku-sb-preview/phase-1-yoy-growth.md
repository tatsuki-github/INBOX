# Phase 1（簡略）: 前年コースYOY伸び

## ユーザーストーリー
コーチとして、前年荒玉で走った選手（角田など）の予想に今年の学年アップ伸びを反映し、前年タイムより速く見たい。フォームが同程度なら他選手にも同じ扱いをしたい。

## 受け入れ条件
1. 角田亜美 2.0km 予想 < 7:44（前年3区）。
2. 前年コース＋今年フォームが同程度〜良い選手に伸び適用。明らかに遅い選手は未適用。
3. 単体テスト Green＋再生成 dual-write。

## テストマッピング
| AC | テスト |
|:---|:---|
| 1 | `test_tsunoda_faster_than_prior_year_7_44` |
| 2 | `test_clearly_slower_form_skips_growth` / `test_faster_current_form_uses_growth_floor` / `test_prior_only_light_growth` |
| 3 | `tests.test_aragyoku_sb_preview` 全件 |

## In / Out
- In: `apply_yoy_course_growth`、パイプライン接続、ADR056、再生成
- Out: 人間 YAML の個別 set、UI
