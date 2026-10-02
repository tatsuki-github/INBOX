import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { answerQuestion } from "../src/domain/answer.js";
import { loadPreparedQa, normalizePreparedQuestion, matchPreparedAnswer, type PreparedQaEntry } from "../src/domain/preparedQa.js";
const dir = resolve(process.cwd(), "../input/faq/full-knowledge-qa");
const batches = readdirSync(dir).filter(f => /^reviewed-\d+\.json$/.test(f)).sort();
const candidates: PreparedQaEntry[] = batches.flatMap(f => JSON.parse(readFileSync(resolve(dir, f), "utf8")).entries);
const baseline = loadPreparedQa();
const ids = new Set(baseline.map(e => e.id));
const pending = candidates.filter(e => !ids.has(e.id));
const entries = [...baseline, ...pending];
const owners = new Map<string, Set<string>>();
for (const e of entries) for (const q of e.questions) {
  const key = normalizePreparedQuestion(q);const set = owners.get(key) ?? new Set<string>();set.add(e.id);owners.set(key,set);
}
const published = process.argv.includes("--published");
if (published && pending.length) throw new Error("Unpublished reviewed entries");
for (const e of candidates) for (const q of e.questions) {
  if (owners.get(normalizePreparedQuestion(q))?.size !== 1) throw new Error(`Normalized question collision: ${e.id}`);
  if (published && matchPreparedAnswer(q)?.id !== e.id) throw new Error(`Prepared answer routing mismatch: ${e.id}`);
}
console.log(JSON.stringify({reviewed:candidates.length,pending:pending.length,normalizedCollisions:0,routingChecked:published,routingErrors:published ? 0 : null}));

if (process.argv.includes("--answers")) {
  if (!published) throw new Error("Answer checks require --published");
  const failures: string[] = [];
  for (const e of candidates) for (const q of e.questions) {
    const result = await answerQuestion(q, {
      skipRouter: true,
      retrieve: () => { throw new Error("Unexpected retrieval: " + e.id); },
      kgQuery: () => { throw new Error("Unexpected KG fallback: " + e.id); },
      llm: { complete: async () => { throw new Error("Unexpected LLM: " + e.id); } },
    });
    if (result.kind !== "answered" || !result.sources.includes("prepared:" + e.id))
      failures.push(e.id + " " + result.kind + " " + ("sources" in result ? result.sources.join(",") : ""));
  }
  if (failures.length) throw new Error("Answer path mismatches: " + failures.length + "\n" + failures.join("\n"));
  console.log(JSON.stringify({ answered: candidates.length, answerPathErrors: 0 }));
}
