# ADR 036: 学校別 PB 平均と優勝差の正本優先

- Status: Accepted
- Date: 2026-09-19

## Context

crush100-v5 後も未網羅だった質問:

1. 「女子800mで岱明の上位3人平均は？」→ SB CSV / LINE が勝ち、`2026_women_800m_1500m_pb_school_ranking.md` の平均が出ない。
2. 「2025年岱明男子の優勝との差は？」→ `aragyoku_meet_records`（ボード）が先頭になり、focus の「優勝との差」列（+2:51）が offline preview に入らない。

## Decision

1. **学校別 PB 平均**: `上位N人平均` / `学校別` + 800/1500 で学校別ランキング MD を preferred し、SB CSV と LINE を先頭に置かない。
2. **優勝差**: `優勝との差|優勝差|優勝から` で focus / team digest を boostし、meet_records を demote。offline preview は「優勝との差」列付近を優先。
3. **評価**: `questions-crush100-v6.json` で all_of 厳格 100/100。

## Consequences

- 「学校別ランキング」明示がなくても平均質問が正本に当たる。
- 大会記録ボード質問は従来どおり meet_records 優先。
