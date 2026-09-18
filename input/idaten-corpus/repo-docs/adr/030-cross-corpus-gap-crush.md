# ADR 030: 横断ギャップ潰し（天気ops・年度プレビュー・snake_case）

## Status

Accepted

## Context

LINE 以外のコーパス横断 Q&A（練習・荒玉距離/ペース履歴・ノルウェー/GZ・天気データ更新 docs・ADR）で未網羅が残っていた。

発見した欠陥:

1. `/天気/` の hard refuse が、リポジトリ内の `docs/tamana-weather.md` 運用質問まで拒否する
2. オフライン preview が表の先頭に張り付き、`2023` 年のペース行を切り落す
3. `formatForLine` の `_italic_` が `practice_meets_affect_load` 等の snake_case を破壊する
4. 夕練開始時刻・`practice_meets_affect_load` が誤ソースに埋もれる

## Decision

1. **Scope**: 天気 hard refuse は維持しつつ、`天気データ` / `1時間間隔` / `保存先` / `Open-Meteo` 等の **repo weather ops** は in_scope
2. **previewForOffline**: ISO 日付の次に `20xx` 年行（`| 2023 |` 等）を優先窓にする
3. **formatForLine**: snake_case 識別子を italic 置換から保護する
4. **retrieve / preferred**: 夕練時刻 → `practice/*.json`、負荷設定 → ADR 006 をブースト
5. **回帰**: `backend/data/eval-gaps/`（50問）+ 既存 `eval-line`（46問）

## Consequences

- 「今日の天気は？」は引き続き拒否
- 「玉名の天気データはどう更新する？」はコーパス回答可能
- 年度付きペース表・設定キー名・夕練 18:00 が offline で安定

## Alternatives Considered

- 天気 hard refuse 全廃止: 却下 — ライブ天気誘導のリスク
- プレビューを常に全文: 却下 — LINE 文字数制約
