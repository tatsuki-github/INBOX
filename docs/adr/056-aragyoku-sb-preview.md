# ADR 056: 荒玉駅伝 SB 区間予想（5ヶ月鮮度・歴代キャリブ）

- Status: Accepted
- Date: 2026-09-27

## Context

なごみ／ジュニア駅伝では区間オーダー×SB換算の予想パイプラインがあるが、荒玉には未整備だった。
荒玉は区間距離が長く差が大きく、トラックSBの楽観が女子で顕著（ジュニア2026岱明: 予想34:54→実績36:52）。
公式オーダー未着でも岱明確定区間とジュニア地区結果で部分予想・展開シナリオを先に残したい。

## Decision

1. **生成**: `scripts/generate_aragyoku_ekiden_sb_preview.py`
   - なごみ換算式を再利用し、[docs/aragyoku-ekiden-distance-definitions.md](../aragyoku-ekiden-distance-definitions.md) の2024以降距離で比例。
   - 男子3000m閾値は30秒（ジュニア踏襲）。
   - 岱明は `TAIMEI_KNOWN_LEGS` で女1–5・男1–4のみシード。男5–6は空欄。
2. **SB鮮度**: `load_sb_index(..., freshness_days=152)`（≒5ヶ月）。
   - as_of 以前かつ152日以内の記録のみ。日付欠落は不採用。
   - なごみ／ジュニアは `freshness_days=None`（従来どおり）。
3. **キャリブ**: `scripts/calibrate_aragyoku_sb_preview.py` が2024–2025 transcripts×当時SBで区間中央値ギャップを推定し、`LEG_BIAS_SEC` と `out/analysis/aragyoku_sb_calibration.*` を更新。
4. **ジュニア地区転記**: 荒玉 keywords 校を優先文字起こし。全県完全起こしは公式PDF後。
5. **展開**: `校別展開予想.md` に附・南関・岱明を軸にしたシナリオを残す。

## Consequences

- 鮮度窓により古いSBだけの選手は欠測になり、coverage で穴が見える（精度のため意図的）。
- 公式オーダー到着後に他校行を追加し、シードを OVERRIDES へ移行する。
- 女子はジュニア予実からスタミナ系統の楽観に注意。男子はジュニアで予想一致のため過補正しない。

## Commands

```bash
python3 scripts/calibrate_aragyoku_sb_preview.py
python3 scripts/generate_aragyoku_ekiden_sb_preview.py --as-of 2026-09-27
python3 -m unittest tests.test_aragyoku_sb_preview
```
