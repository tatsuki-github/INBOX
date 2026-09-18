# ADR 007: 大会翌日は休み（自主練 E まで）

## Status

Accepted

## Context

いだてん岱明の運用では、大会翌日は部の練習を基本休みとし、自主練でも E までとする。practice-ai には大会前日（追い込み禁止）と大会2日前 RP のみがコード化されており、翌日ルールは長期計画メモに散在していた。

## Decision

1. [`input/ai_generation_rules.yaml`](../../input/ai_generation_rules.yaml) に `daiming.post_race` を追加
2. `session_context` が **前日** の大会・記録会・駅伝・ナイターを `prev_race` で検出
3. 検出時はテンプレ `post-race-rest` を優先（週次・単日とも）。**大会2日前 RP より優先**
4. 現場1枚の切上げに「前日が大会 → 休み。自主練も E まで」を追加
5. 練習会は引き続き負荷外（ADR 006）

## Consequences

- 8/30（ナイター翌日）は `post-race-rest` になる
- 9/21（なごみ翌日）も同様
- 例外グループは `--input` に「例外グループ」と書けば上書き可

## Alternatives Considered

- 翌日 E ジョグテンプレ: 却下 — 「基本休み」を優先。E は notes で自主練許可
- `prev_race` で朝練のみ E: 却下 — 朝夕とも休みが方針
