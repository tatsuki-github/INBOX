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

## 単日生成（現場1枚）

既定出力は指導者向けシート。`--date` で前後3日・天候を注入する。

```bash
python3 scripts/generate_practice.py \
  --input "夕練、軽いポイント" \
  --date 2026-08-21 \
  --dry-run

python3 scripts/generate_practice.py \
  --input "夕練、軽いポイント" \
  --date 2026-08-21 \
  --apply
```

`--format yaml` / `json` で機械出力。信頼度 `withhold` のときは `--apply` しない。

秒タイムは T ペース（`--t-pace`、既定 4:01）から決定論的に算出する。

## 週次計画

```bash
python3 scripts/generate_weekly_plan.py --week 2026-03-09 --dry-run --format sheet
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
- [004-coach-ready-practice-sheet.md](adr/004-coach-ready-practice-sheet.md)
- [005-pre-race-rp-stimulus.md](adr/005-pre-race-rp-stimulus.md)
- [006-practice-meets-not-load.md](adr/006-practice-meets-not-load.md)

## 大会2日前の RP 刺激

`--date` が大会の2日前（夕練）なら、クエリより先に RP 1本を選ぶ。連続疾走は 1000m まで。

| 2日後の種目 | 刺激 |
|---|---|
| 800m | 600m×1 RP |
| 1500m | 900m×1 RP（入力に 1000 があれば 1000m×1） |
| 種目不明 | 900m×1 RP（現場シートで種目確認） |

練習会・研究大会は大会に数えない。**練習会は生徒が基本不参加のため疲労・テーパーにも使わない**（記録会の翌日は追い込み禁止のまま）。

## 大会翌日

前日が記録会・選手権・駅伝・ナイターなら `post-race-rest`：**部の練習は休み**。自主練も E まで。設定は `input/ai_generation_rules.yaml` の `daiming.post_race`。
