# 荒玉駅伝 SB 予実ギャップ分析

ステータス: **レース前スタブ**（2026-10-14 開催予定）

## 予定ワークフロー

1. 成績を `岱明の結果.md` および男女成績表に転記する。
2. レース前の `区間オーダー_SB予想.md`（as_of＝大会前日）を固定する。
3. 本スクリプトを拡張し、差＝実績−予想の表／HTML を生成する（なごみ ADR 052 準拠）。
4. `calibrate_aragyoku_sb_preview.py` に2026を加えて区間バイアスを更新する。

## 現状の事前材料

- 予想: `/Users/t-tsuchiyama/Desktop/INBOX/input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝/区間オーダー_SB予想.md`
- 展開: `/Users/t-tsuchiyama/Desktop/INBOX/input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝/校別展開予想.md`
- ジュニア予実（参考）: ジュニア大会フォルダの `岱明の結果.md`
