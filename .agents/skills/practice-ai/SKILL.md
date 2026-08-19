````skill
---
name: practice-ai
description: >
  岱明練習の AI 練習計画生成。自然言語から practice YAML を生成し、
  テンプレ参照 + lint 検証 + Norwegian Method 原則 + RAG 説明に対応。
  Use when user says「練習メニューを生成して」「夕練のメニューを作って」
  「週間練習計画を立てて」「GZ とは何？」「ゴールデンゾーンのペースは？」
  「サブ閾値のペース」「閾値ペースを教えて」「VDOT から GZ」
  「Norwegian Method で説明して」「practice-ai」「AI練習計画」。
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
| **GZ / サブ閾値（必須）** | `python3 scripts/daniels_pace.py --race 1500m 4:20` |
| RAG 索引 | `python3 scripts/build_rag_index.py` |

## 設計原則

1. **骨格はテンプレ選択** — [`input/practice_templates.yaml`](../../input/practice_templates.yaml)
2. **創作は notes/warmup** — コーチの意図・状況判断
3. **lint 必須** — `validate_practice_block` 通過まで最大 3 回再生成
4. **ペースは LLM 禁止** — [`scripts/ai/daniels_calculator.py`](../../scripts/ai/daniels_calculator.py) → [`pace_calculator.py`](../../scripts/ai/pace_calculator.py)
5. **GZ / サブ閾値の質問** — 必ず `daniels_pace.py` を実行。10K 換算・Web 概算禁止 → [daniels-gz-guide.md](references/daniels-gz-guide.md)
6. **大会2日前は RP 1本** — 800m→600m、1500m→900m（または1000m）。連続≤1000m
7. **練習会は負荷に数えない** — いだてん岱明は基本不参加。記録会の疲労・テーパーだけ見る
8. **大会翌日は休み** — 部練習は休み。自主練も E まで（`post-race-rest` テンプレ）
9. **現場1枚** — 読み上げ文 + 秒タイム + 切上げ。選手名は推測しない
10. **`--apply`** — `description` と `practice` を同時更新。`withhold` は拒否

- [docs/adr/004-coach-ready-practice-sheet.md](../../docs/adr/004-coach-ready-practice-sheet.md)
- [docs/adr/005-pre-race-rp-stimulus.md](../../docs/adr/005-pre-race-rp-stimulus.md)
- [docs/adr/006-practice-meets-not-load.md](../../docs/adr/006-practice-meets-not-load.md)
- [docs/adr/007-post-race-rest.md](../../docs/adr/007-post-race-rest.md)

## 週1 実験

- 週に最大 1 セッション
- `notes` は `【実験】` で開始
- `I`/`R` intensity 禁止
- 新規 item 最大 2 つ

## GZ / サブ閾値ペース（Daniels 基準）

ユーザーが GZ・ゴールデンゾーン・サブ閾値・閾値ペースを聞いた場合:

1. **必ず** `python3 scripts/daniels_pace.py --race <距離> <タイム>` を実行
2. 出力の VDOT・T ペース・GZ ブロックをそのまま根拠に回答
3. 10K 換算・頭算・Web 検索でペースを推定しない

詳細: [references/daniels-gz-guide.md](references/daniels-gz-guide.md)

## ドキュメント

- [docs/ai-practice-generation.md](../../docs/ai-practice-generation.md)
- [docs/adr/001-ai-practice-generation-architecture.md](../../docs/adr/001-ai-practice-generation-architecture.md)
- [docs/adr/008-daniels-vdot-gz-guidance.md](../../docs/adr/008-daniels-vdot-gz-guidance.md)

````
