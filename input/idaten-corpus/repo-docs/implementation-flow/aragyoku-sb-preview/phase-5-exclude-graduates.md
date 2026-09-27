# Phase 5–6: 卒業生除外

## 実装

- `projected_current_grade` / `is_graduated_by_grade_history` / `load_graduated_school_names`
- `EXCLUDED_GRADUATES`（山本悠斗）
- `load_prior_year_returners` と `build_school_athlete_pools` で除外

## 検証

- `pytest tests/test_aragyoku_sb_preview.py` → 62 passed
- 再生成後、Drive/コーパス出力に「山本悠斗」なし。天水1区=中村七皇

## レビュー

Approved（Critical=0, Major=0）
