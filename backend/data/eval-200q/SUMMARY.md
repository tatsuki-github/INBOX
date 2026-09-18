# eval-200q summary

- Date: 2026-09-18
- Result: **200/200 PASS** (20 rounds × 10 questions)
- Mode: offline repo-grounding (`answerQuestion` without LLM; `offline` accepted as grounded `answered`)
- Runner: `npx tsx scripts/eval-200q/run.ts`
- Bank: `backend/data/eval-200q/questions.json`
- ADR: `docs/adr/023-eval-200q-repo-grounding.md`

## Rounds

| Round | Theme | Pass |
|------:|:---|:---:|
| 1 | sb-daiming | 10/10 |
| 2 | sb-other-schools | 10/10 |
| 3 | clarify-pb | 10/10 |
| 4 | calendar-events | 10/10 |
| 5 | meet-result-urls | 10/10 |
| 6 | sb-named-honorific | 10/10 |
| 7 | out-of-scope | 10/10 |
| 8 | aragyoku | 10/10 |
| 9 | practice | 10/10 |
| 10 | meet-urls-natural | 10/10 |
| 11 | sb-edge | 10/10 |
| 12 | dates-relative | 10/10 |
| 13 | named-pb-should-answer | 10/10 |
| 14 | meta-club | 10/10 |
| 15 | sb-other-2 | 10/10 |
| 16 | bbq-plan-detail | 10/10 |
| 17 | scope-mix | 10/10 |
| 18 | meet-url-year | 10/10 |
| 19 | practice-detail-2 | 10/10 |
| 20 | paraphrase-stress | 10/10 |
