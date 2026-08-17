# ADR 006: 練習会は岱明生徒の負荷に数えない

## Status

Accepted

## Context

カレンダー上の「練習会（桃田）」「練習会（岱明）」を、指導者向けシートが **練習会翌日のジョグのみ** / **翌日追い込み禁止** / 信頼度 `review` の根拠にしていた。いだてん岱明の生徒は練習会に **基本不参加** なので、これは誤った疲労考慮である。記録会・選手権は出場する。

### 作業種別（implementation-flow Lite Path）

- **種別**: `extend`
- **検証**: Python / pytest
- **Docs Sync**: `docs/adr/` + `docs/ai-practice-generation.md`
- **スキップ**: Phase 2/4（UI なし）

## Decision

1. [`input/ai_generation_rules.yaml`](../../input/ai_generation_rules.yaml) の `daiming.practice_meets_affect_load: false` を正とする
2. `prev_meet` / `next_meet` は練習会から立てない（負荷フラグにしない）
3. 切上げから「練習会翌日で脚が重い」を外す。翌日のテーパーは **記録会のみ**
4. 大会2日前 RP は翌日練習会では止めない（翌日記録会では止める）
5. 信頼度は練習会前後だけでは `review` にしない

## Consequences

- 8/21 夕練は練習会翌日でもジョグ強制にならない（天候による切上げは残る）
- カレンダーに練習会は残るが、メニューの骨格は通常の GZ 週として組める

## Alternatives Considered

- 練習会をカレンダーから消す: 却下 — 会場情報として残す価値がある
- 例外参加の選手だけ手で切上げ: 採用 — 確認チェックリストの「例外グループ」で足りる
