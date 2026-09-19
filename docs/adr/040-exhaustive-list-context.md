# ADR 040: 「全て提示」系の網羅コンテキスト渡し

- Status: Accepted
- Date: 2026-09-19

## Context

「〇〇を全て提示して」「全部出して」などの質問が弱い。BM25 と広い hub（OCR・out-analysis）が
散発ヒットし、回答に足る正本ダイジェストが埋もれる。オフライン preview も針で切りすぎて
一覧表を欠くことがある。

## Decision

1. `isExhaustiveListQuery` で網羅意図（全て / すべて / 全部 / 漏れなく 等）を検出する。
2. 検出時は `narrowExhaustiveSources` で **正本 exact ファイルを最大 4 件**に絞る
   （例: 優勝校 → `winners-by-year.md`、ペース → `all_teams_average_pace.md`）。
3. `retrieveBySources({ coverage: "full" })` で当該正本を **文書順・全文寄り**に取る。
4. `mergeRetrieved({ preferPrimaryOrder: true })` で preferred 順を保ち、BM25 は薄い filler。
5. LLM prompt に「要約で間引かず列挙」指示を足す。offline preview 予算を広げる。

## Consequences

- 「全て」質問は的を絞った正本で網羅できるコンテキストが渡る。
- OCR / 無関係分析が先頭に来にくくなる。
- 巨大正本（92 chunks 級）は maxChars 内で可能な限り文書順に供給する。
