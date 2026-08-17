# ADR 003: AI モジュール テスト戦略

## Status

Accepted

## Context

AI 練習計画生成は LLM 依存部分と決定論的部分が混在する。CI で外部 API を呼べない。

## Decision

| 分類 | 対象 | 手法 |
|---|---|---|
| ドメイン | `creative_rules`, `template_selector`, `pace_calculator`, `validator`, `pre_race_stimulus`, `attendance_rules` | pytest TDD |
| オーケストレータ | `practice_generator`, `weekly_planner` | MockLLMClient |
| RAG | `chunker`, `BM25Retriever` | 固定フィクスチャ + tmp_path |
| CLI | `generate_practice.py` 等 | subprocess（将来） |
| 統合 LLM | 実 API | `@pytest.mark.integration`、CI 除外 |

検証コマンド: `python3 -m pytest tests/ -v`

## Consequences

- 退行は pytest で検出、LLM 品質は手動/統合マーカーで確認
