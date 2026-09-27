# Phase 1（簡略）: 玉名／荒尾三 女子 Bチーム埋め

## ユーザーストーリー
コーチとして、前年A+Bの区間実績で玉名中女子の欠区間を埋め、荒尾三中も前年配置に合わせたい。

## 受け入れ条件
1. 玉名中女子の仮オーダーが5区間すべて埋まる（川原1・水本5含む）。
2. B実績（清藤・亀木・結菜）が `load_prior_year_returners` / 予想に入る。
3. 荒尾三中が福島1・佐藤4・内野5。

## テスト
| AC | テスト |
|:---|:---|
| 1–3 | `TestPriorBTeamTamana` / `test_redistribute_builds_nagasu_men_and_women_clubs` |
