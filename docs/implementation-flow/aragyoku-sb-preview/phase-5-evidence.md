# Phase 5 相当: 事実エビデンス実装メモ

## 変更点

- `fmt_race_fact` / `fmt_sb_mark_fact`: 大会・記録・日付の事実文字列
- `predict_leg`: `SB:種目 記録@日付→式→区間km=タイム`
- `blend_with_recent_form`: `駅伝加味:事実→比例(w=…)→加重`
- `apply_yoy_course_growth`: `前年伸び:事実→比例×-N%→採用`
- MD 列名: 備考 → **エビデンス**
- 全予想区間末尾に `→予想M:SS.s`

## 検証

```bash
.venv/bin/python -m unittest tests.test_aragyoku_sb_preview
.venv/bin/python scripts/generate_aragyoku_ekiden_sb_preview.py --as-of 2026-09-27
```
