# ADR 039: 荒玉駅伝・全チーム平均ペース正本

- Status: Accepted
- Date: 2026-09-19

## Context

「〇位の平均ペースは？」など計算系の質問が弱い。既存の
`aragyoku_top6_historical_average_pace.md` は総合1〜6位のみで、下位や「全チーム」の要求に足りない。

## Decision

1. `scripts/generate_aragyoku_all_teams_average_pace.py` で transcripts 全件から
   **総合タイム ÷ 当年コース総距離** を算出し、
   `out/analysis/aragyoku_all_teams_average_pace.md` に格納する。
2. 距離は `docs/aragyoku-ekiden-distance-definitions.md` に従う（男子は2024前後で切替）。
3. 同スクリプトで top6 要約ファイルも再生成し、互換を保つ。
4. preferred / retrieve / KG QueryHint で「平均ペース」「〇位」を全チーム正本へ寄せる。
5. `build_idaten_corpus.py` の生成パイプラインに組み込む。

## Consequences

- 年度×全順位×全校の平均ペースが事前計算され、オフラインでも答えられる。
- ランタイムでのその場計算に依存しない。
