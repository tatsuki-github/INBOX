# Phase 1: 卒業生除外

## ユーザーストーリー

コーチとして、卒業済みの選手を仮オーダーに載せたくない。今年度の中学生だけ見たい。

## 受け入れ条件

1. 山本悠斗が天水オーダー／プール／復帰候補に現れない
2. 2025中3（例: 米谷慶吾）は除外される
3. 学年揺れのみ（例: 本戸優貴 2024(2)/2025(2)）は在籍扱いで残る
4. テストが上記を固定する

## テストマッピング

| AC | テスト |
|:---|:---|
| 1–3 | `test_excludes_graduated_yamamoto_yuto` / `test_projected_current_grade` |
| 4 | `test_redistribute_builds_nagasu_men_and_women_clubs`（長洲男子非掲載） |
