import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { loadPreparedQa, normalizePreparedQuestion } from "../src/domain/preparedQa.js";

const dir = resolve(process.cwd(), "../input/faq/full-knowledge-qa");
const batches = readdirSync(dir).filter((f) => /^reviewed-\d+\.json$/.test(f)).sort();
const candidates = batches.flatMap((f) => JSON.parse(readFileSync(resolve(dir, f), "utf8")).entries);
const baseline = loadPreparedQa();
const ids = new Set(baseline.map((e) => e.id));
const pending = candidates.filter((e) => !ids.has(e.id));
const entries = [...baseline, ...pending];
const owners = new Map<string, Set<string>>();
for (const e of entries) {
  for (const q of e.questions) {
    const key = normalizePreparedQuestion(q);
    const set = owners.get(key) ?? new Set<string>();
    set.add(e.id);
    owners.set(key, set);
  }
}
const failures: { id: string; key: string; owners: string[] }[] = [];
for (const e of candidates) {
  for (const q of e.questions) {
    const key = normalizePreparedQuestion(q);
    const set = owners.get(key);
    if (!set || set.size !== 1) {
      failures.push({ id: e.id, key, owners: set ? [...set] : [] });
    }
  }
}
console.log(JSON.stringify({ pending: pending.length, failureCount: failures.length, failures }, null, 2));
