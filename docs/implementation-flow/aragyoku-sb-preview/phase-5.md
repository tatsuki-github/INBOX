# Phase 5–6 完了メモ: 荒玉 SB 予想

## 実装済み

- ジュニア荒玉地区転記・岱明の結果・校別展開予想・岱明シード
- `freshness_days=152`（`generate_nagomi_order_sb_preview.load_sb_index`）
- `calibrate_aragyoku_sb_preview.py` → `out/analysis/aragyoku_sb_calibration.*` + LEG_BIAS_SEC
- `generate_aragyoku_ekiden_sb_preview.py` → 区間オーダー_SB予想.md / coverage
- `generate_aragyoku_sb_gap_analysis.py`（レース後スタブ）
- ADR 056 / unittest 10件 Green
- events.2026.yaml + calendar 2026 + KG 再生成

## 残フォロー（ブロッカー解除待ち）

- 公式スタートリスト到着 → 全チーム本生成（`公式オーダー待ち.md`）
- 公式結果PDFでジュニア転記の突合
- レース後の予実ギャップ本実装
