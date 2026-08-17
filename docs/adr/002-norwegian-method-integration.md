# ADR 002: Norwegian Method 統合方針

## Status

Accepted

## Context

AI 練習計画生成では Norwegian Method（Marius Bakken *The Norwegian Method Applied*）の原則に沿った提案が必要。LLM にペースや physiology を任せると算数ミス・グレーゾーン助長のリスクがある。

## Decision

1. **ペース計算**: [`scripts/ai/pace_calculator.py`](../../scripts/ai/pace_calculator.py) に Ch.2/Ch.5 ロジックを集約。`update_golden_zone_tables.py` も同モジュールを import
2. **テンプレ**: `norwegian-45-15-*`, `evening-light-*` テンプレを GZ/T セッションの選択肢とする
3. **RAG**: `input/memos/norwegian_method_applied_full.txt` と `tmp/norwegian_method_summary.md` を索引
4. **プロンプト**: `norwegian_rules.principles_for_prompt()` と T ペース表を system prompt に注入

## Consequences

- GZ/T ペースは Daniels T から決定論的に導出
- 説明・週テーマは RAG + LLM、数値はコード

## Alternatives Considered

- LLM にペース表全文を記憶させる: 却下 — 算数・形式ミス
- 書籍 PDF をその都度読込: 却下 — 既存 txt/summary で十分
