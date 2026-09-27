# Phase 1/5/6: 男子 遅→5・次遅→2（岱明除外）

## 受け入れ条件

1. `legs_from_ranked_athletes(..., women_aces=False)` が `[最速, 次遅, …, 最遅@5区, …]`
2. 岱明男子の6区間が従来どおり（松野・山本・今村・田上・中尾・松本）
3. 荒尾第四の藤井が5区（遅→5）
4. 女子配置（aces）は不変

## 実装

- `legs_from_ranked_athletes` 男子分岐
- `_apply_men_slow_leg_placement`（岱明スキップ）を locked / seed 経路に適用
- テスト・再生成
