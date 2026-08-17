````skill
---
name: practice-ai
description: >
  岱明練習の AI 練習計画生成。自然言語から practice YAML を生成し、
  テンプレ参照 + lint 検証 + Norwegian Method 原則 + RAG 説明に対応。
  Use when user says「練習メニューを生成して」「夕練のメニューを作って」
  「週間練習計画を立てて」「GZ とは何？」「Norwegian Method で説明して」
  「practice-ai」「AI練習計画」。
  Do NOT use for: カレンダー CSV 生成（→ generate_calendar.py）、
  既存 description の backfill（→ backfill_practice.py）。
metadata:
  author: KC-Prop-Foundry
  version: 1.0.0
  category: operations
---

# Skill: Practice AI（岱明練習 AI 生成）

## クイックリファレンス

| タスク | コマンド |
|:---|:---|
| 単日生成（現場1枚） | `python3 scripts/generate_practice.py --input "夕練 軽め" --date 2026-08-21 --dry-run` |
| 単日生成（LLM なし YAML） | `python3 scripts/generate_practice.py --input "..." --dry-run --format yaml` |
| 単日生成（LLM） | `ANTHROPIC_API_KEY=... python3 scripts/generate_practice.py --input "..." --date YYYY-MM-DD` |
| カレンダーへ採用 | `python3 scripts/generate_practice.py --input "..." --date YYYY-MM-DD --apply` |
| 週次計画 | `python3 scripts/generate_weekly_plan.py --week YYYY-MM-DD --dry-run --format sheet` |
| 説明 | `python3 scripts/explain_practice.py --question "..." --dry-run` |
| RAG 索引 | `python3 scripts/build_rag_index.py` |

## 設計原則

1. **骨格はテンプレ選択** — [`input/practice_templates.yaml`](../../input/practice_templates.yaml)
2. **創作は notes/warmup** — コーチの意図・状況判断
3. **lint 必須** — `validate_practice_block` 通過まで最大 3 回再生成
4. **ペースは LLM 禁止** — [`scripts/ai/pace_calculator.py`](../../scripts/ai/pace_calculator.py)
6. **現場1枚** — 読み上げ文 + 秒タイム + 切上げ。選手名は推測しない
7. **`--apply`** — `description` と `practice` を同時更新。`withhold` は拒否

- [docs/adr/004-coach-ready-practice-sheet.md](../../docs/adr/004-coach-ready-practice-sheet.md)

## 週1 実験

- 週に最大 1 セッション
- `notes` は `【実験】` で開始
- `I`/`R` intensity 禁止
- 新規 item 最大 2 つ

## ドキュメント

- [docs/ai-practice-generation.md](../../docs/ai-practice-generation.md)
- [docs/adr/001-ai-practice-generation-architecture.md](../../docs/adr/001-ai-practice-generation-architecture.md)

````
