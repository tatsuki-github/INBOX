# ADR 001: AI 練習計画生成アーキテクチャ

## Status

Accepted

## Context

岱明練習カレンダーは `practice` フィールドを正とする構造化 YAML だが、コーチの自然言語入力からの生成は未対応だった。LLM 単体生成は形式ミス・距離創作・ペース算数ミスのリスクが高い。

## Decision

1. **テンプレ参照型**: コア items は [`input/practice_templates.yaml`](../../input/practice_templates.yaml) から選択し差分編集する
2. **lint 検証ループ**: 生成後に [`scripts/lint_events.py`](../../scripts/lint_events.py) の `validate_practice_block` を通し、最大 3 回再生成
3. **創作スロット**: `warmup` / `notes` / 週テーマのみ自由生成。`I`/`R` intensity はテンプレ必須（週1 実験除く）
4. **CLI + Agent Skill**: Web UI は作らず `scripts/generate_practice.py` 等と `.agents/skills/practice-ai/` で提供

## Consequences

- 精度はテンプレ + lint で担保、独創性は notes 等に集中
- LLM API キー未設定時はテンプレ選択のみの `--dry-run` フォールバック可能
- 新テンプレ追加が AI 品質向上の主要レバーになる

## Alternatives Considered

- **自由生成のみ**: 却下 — 560m 換算・intensity 語彙の誤りが頻発する見込み
- **ファインチューニング**: 却下 — データ量・運用コストに対し ROI が低い
