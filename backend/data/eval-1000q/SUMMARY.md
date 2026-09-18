# eval-1000q summary

- Date: 2026-09-18
- Result: **1000/1000 PASS** (100 rounds × 10 questions)
- Mode: offline repo-grounding (`answerQuestion` without LLM; `offline` accepted as grounded `answered`)
- Runner: `npx tsx scripts/eval-1000q/run.ts`
- Bank: `backend/data/eval-1000q/questions.json`
- Unique question texts: ~684 / 1000 (clarify / OOS / meet templates intentionally reuse phrasing)
- ADR: `docs/adr/023-eval-200q-repo-grounding.md`（1000問へ拡張）

## Themes (rotating)

SB（岱明/他校）、clarify、calendar（コーパス予定のみ）、meet URL、OOS、aragyoku、practice、言い換え
