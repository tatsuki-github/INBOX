# ADR 008: Daniels VDOT による GZ / サブ閾値ペース算出

## Status

Accepted

## Context

- ADR 002 では GZ/T ペースを Daniels T から決定論的に導出すると定めたが、VDOT → T の計算モジュールが未整備だった
- エージェントが GZ を 10K 換算等で概算すると、T ペースより速い誤った値（例: 3:23/km）を提示するリスクがあった
- 選手メモ（`input/events.2026.yaml`）には `【ダニエルズ・ペース】` ブロックが既に存在し、VDOT 53.7 → T 4:01/km 等の対応が検証済み

## Decision

1. **VDOT 計算**: [`scripts/ai/daniels_calculator.py`](../../scripts/ai/daniels_calculator.py) に Daniels-Gilbert 式を実装
2. **トレーニングペース**: [`input/daniels_vdot_paces.yaml`](../../input/daniels_vdot_paces.yaml) の 3rd ed. テーブル（sec/mile）を線形補間
3. **GZ 導出**: 既存 [`pace_calculator.py`](../../scripts/ai/pace_calculator.py) の T+offset ロジックを使用（変更なし）
4. **CLI**: [`scripts/daniels_pace.py`](../../scripts/daniels_pace.py) — エージェント・コーチ向け
5. **エージェント規約**: GZ / サブ閾値の質問には **CLI 実行結果を根拠に回答**（[`practice-ai` スキル](../../.agents/skills/practice-ai/references/daniels-gz-guide.md)）

## Consequences

- GZ 回答の一貫性が保証される（レースタイム → VDOT → T → GZ）
- 1500m 4:20 例: VDOT 64.0, T 3:29/km, GZ 600m 2:10–2:13（T+8–12秒/km）
- `update_golden_zone_tables.py` は引き続き T ペース文字列から GZ を更新（VDOT CLI と整合）

## Alternatives Considered

- Web 検索 / LLM 概算: 却下 — 10K ペース基準の過大評価が再発
- VDOT テーブルをコードに直書き: 却下 — YAML 分離でテスト・更新容易
