# Phase 3: 2025 なごみ予実

## 特性

1. 後知恵防止（as_of）
2. 2026 予想式との比較可能性
3. 成績表のトレーサビリティ
4. 性別衝突の回避

## 構成

- Data: `nagomi_2025_results_data.py`
- Generate: `generate_nagomi_2025_sb_vs_actual.py`
- Shared formula: `generate_nagomi_order_sb_preview.py` の `load_sb_index` / `predict_*`

## テスト戦略

ドメイン単体（pytest）が主。統合は生成ファイルの存在と KG refs。
