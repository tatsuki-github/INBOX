# Phase 1: クラブ→学校マッピング再分配

## ユーザーストーリー

コーチとして、ATRC・金栗PROJECT・玉名アスリーツ等のクラブ所属選手を「誰がどこの学校か」に従って各校オーダーへ分配した荒玉SB予想を見たい。

## 受け入れ条件

1. `arato_tamana_report.yaml` の所属／選手マッピングで学校が解決される（例: ATRC今村→岱明、石川→長洲、金栗居石→玉陵）。
2. 男子に長洲中が現れ、石川・米谷が載る。女子に菊水・玉陵が現れ、庄山が荒尾三・居石が玉陵に載る。
3. ユニーク2名未満の学校マッピング校は載せない（1人の全区間埋め偽1位を防ぐ）。
4. `tests/test_aragyoku_sb_preview.py` の `TestSchoolAffiliationMap` が通る。

## テストマッピング

| AC | テスト |
| --- | --- |
| 1 | `test_resolve_atrc_and_kanaguri` |
| 2–3 | `test_redistribute_builds_nagasu_men_and_women_clubs` |
| 4 | unittest 全体 |
