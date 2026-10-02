import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { loadPreparedQa, normalizePreparedQuestion } from "../src/domain/preparedQa.js";

const dir = resolve(process.cwd(), "../input/faq/full-knowledge-qa");
const batches = readdirSync(dir).filter((f) => /^reviewed-\d+\.json$/.test(f)).sort();
const candidates = batches.flatMap((f) => JSON.parse(readFileSync(resolve(dir, f), "utf8")).entries);
const baseline = loadPreparedQa();
const entries = [...baseline, ...candidates];
const owners = new Map<string, Set<string>>();
for (const e of entries) {
  for (const q of e.questions) {
    const key = normalizePreparedQuestion(q);
    const set = owners.get(key) ?? new Set<string>();
    set.add(e.id);
    owners.set(key, set);
  }
}
const collisions = [...owners.entries()].filter(([, s]) => s.size > 1);
console.log(JSON.stringify({ collisions: collisions.length, samples: collisions.slice(0, 30).map(([k, s]) => ({ key: k, ids: [...s] })) }, null, 2));
