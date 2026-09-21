# ADR 052: なごみ SB 予実ギャップ分析（HTML）

- Status: Accepted
- Date: 2026-09-21

## Context

2025 は `予実比較.md`（ADR 049）で差の表があるが、個人・チームが
「予想を大きく上回った／妥当／大きく下回った」かが一目で分からない。
2026 は成績表と SB 予想があるが予実比較が未整備。ユーザーはグラフ付き HTML を希望。
荒尾玉名の比較はクラブ混成が多く、学校対抗で見たい。

## Decision

1. `scripts/nagomi_sb_gap_analysis.py` で差の分類と HTML 描画を担う。
2. `scripts/generate_nagomi_sb_gap_analysis.py` が 2025・2026 をまとめて生成する。
   - 2025: 既存 `build_2025_report`（チーム名突合）
   - 2026: 区間オーダー + `load_sb_index` + 成績の **No. 突合**
3. 出力:
   - 正本 HTML: `out/analysis/nagomi_sb_gap_analysis.html`
   - 大会フォルダ dual-write: `予実比較.md` / `予実比較.html`（2025・2026）
4. 閾値（差 = 実績 − 予想）。soft / hard の 2 段で **5 段階**:
   - 区間 soft/hard: 女子 10/20 秒、男子 15/30 秒
   - 総合 soft/hard: 女子 30/60 秒、男子 60/120 秒
   - `差 <= −hard` → 大きく上回った
   - `−hard < 差 <= −soft` → 少し上回った
   - `|差| < soft` → 妥当
   - `soft <= 差 < hard` → 少し下回った
   - `差 >= hard` → 大きく下回った
5. 荒玉学校対抗:
   - 学校配分は `input/arato_tamana_report.yaml` の
     `school_analysis_affiliation_overrides` /
     `school_analysis_athlete_affiliation_overrides` を正本とする。
   - NJAC は選手 override（濱北愛→長洲中）のみ。他の NJAC は除外。
   - 金栗所属かつ `exclude_name_keywords` 該当選手は除外
     （有尾明莉・秀島恋莉・竹熊紗良など、荒玉地区外）。
   - 配分後、学校ごとに区間実績の上位平均で順位付けし、内訳は配分全員を表示。
     - 女子: **上位5人平均**
     - 男子: **上位6人平均**
   - 平均人数に満たない学校は「参考」として別表示（順位なし）。

## Consequences

- 男子は 3km 換算の系統誤差が大きく、閾値を女子より広く取る。
- 「少し」帯を挟むことで、境界付近のチーム／区間を妥当に押し込めすぎない。
- 欠測 SB の区間・総合は判定不可。補完あり総合は ※。
- 女子は出走人数の都合で平均人数（5人）を揃う学校が少ない場合があり、参考表示が主になることがある。
- 平均枠を超える選手も内訳には全員載せ、平均には含めない。
- 再生成: `python3 scripts/generate_nagomi_sb_gap_analysis.py`
