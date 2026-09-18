# Unique exhausted QA eval

- **Bank**: `questions.json` — 4639 unique questions (464 rounds of 10, last round 9)
- **Generator**: `../scripts/eval-unique/generate_bank.py`
- **Runner**: `../scripts/eval-unique/run.ts`
- **Result (2026-09-18, context 100k)**: offline **4639/4639 PASS**, missingInfo **0%**
- **Breakdown**: sb 4079, cal 297, meet 22, arag 155, clarify 25, oos 37, prac 24

```bash
cd backend
python3 scripts/eval-unique/generate_bank.py
npx tsx scripts/eval-unique/run.ts --offline --concurrency 12
# optional LLM refuse-rate: npx tsx scripts/eval-unique/run.ts --llm
```

See `docs/adr/024-eval-unique-exhausted-qa.md` and `docs/adr/026-context-100k.md`.
