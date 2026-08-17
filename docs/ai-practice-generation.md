# AI 練習計画生成

岱明練習の `practice` YAML を、テンプレート参照 + lint 検証 + Norwegian Method 原則で AI 生成する。

## セットアップ

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # または OPENAI_API_KEY
export AI_PROVIDER=anthropic   # anthropic | openai
```

LLM 未設定時は `--dry-run` でテンプレ選択のみ動作する。

## RAG 索引

```bash
python3 scripts/build_rag_index.py
# → out/ai/rag_index.json
```

## 単日生成

```bash
python3 scripts/generate_practice.py \
  --input "夕練、600m×2、軽め" \
  --dry-run

python3 scripts/generate_practice.py \
  --input "夕練、600m×2、軽め" \
  --apply --year 2026 --date 2026-03-15
```

## 週次計画

```bash
python3 scripts/generate_weekly_plan.py --week 2026-03-09 --dry-run
```

## 説明（Q&A）

```bash
python3 scripts/explain_practice.py --question "なぜ夕練はGZ？" --dry-run
```

## アーキテクチャ

- **固定層**: 560m 換算、intensity 語彙、ペース形式
- **可変層**: reps ±2、pace ±10 秒/km、rest ±30 秒（[`input/ai_generation_rules.yaml`](../input/ai_generation_rules.yaml)）
- **創作層**: `warmup`, `notes`, 週テーマ。週1 実験は `【実験】` プレフィックス必須

## Norwegian Method

- ペース: [`scripts/ai/pace_calculator.py`](../scripts/ai/pace_calculator.py)（Bakken Ch.2/Ch.5）
- 原則: [`scripts/ai/norwegian_rules.py`](../scripts/ai/norwegian_rules.py)
- ソース: `input/memos/norwegian_method_applied_full.txt`

## ADR

- [001-ai-practice-generation-architecture.md](adr/001-ai-practice-generation-architecture.md)
- [002-norwegian-method-integration.md](adr/002-norwegian-method-integration.md)
- [003-test-strategy-ai-module.md](adr/003-test-strategy-ai-module.md)
