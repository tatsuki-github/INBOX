/**
 * Check authored chunk QA candidates without publishing them into the catalog.
 * Quote support + human context review do not claim machine proof of semantics.
 */
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { matchPreparedAnswer, normalizePreparedQuestion, resetPreparedQaCache,
  type PreparedQaEntry } from "../src/domain/preparedQa.js";
import { classifyScope } from "../src/domain/scope.js";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const evidenceDir = join(root, "out/qa-chunks");
const authoredDir = join(root, "input/faq/chunk-qa");
const catalogPath = join(root, "backend/data/prepared-qa.json");
const sha = (data: string | Buffer) => createHash("sha256").update(data).digest("hex");
type Chunk = {
  id: string; source: string; source_sha256: string;
  evidence: { kind: string; text?: string; units?: unknown[] };
};
type Authored = PreparedQaEntry & {
  chunk_id: string; source_sha256: string;
  evidence: Array<{ kind: string; text: string }>;
  review: { method: string; status: string };
};
const chunks = new Map<string, Chunk>();
for (const file of readdirSync(evidenceDir).filter(f => /^chunks-\d+\.jsonl$/.test(f)).sort()) {
  for (const line of readFileSync(join(evidenceDir, file), "utf8").trim().split("\n")) {
    const row = JSON.parse(line) as Chunk;
    if (chunks.has(row.id)) throw new Error("Duplicate chunk: " + row.id);
    chunks.set(row.id, row);
  }
}
const original = readFileSync(catalogPath, "utf8");
const catalog = JSON.parse(original) as { entries: PreparedQaEntry[]; total: number };
const summary = JSON.parse(readFileSync(join(evidenceDir, "summary.json"), "utf8"));
if (catalog.entries.length !== summary.baseline_prepared_qa_count ||
  sha(readFileSync(join(root, "input/faq/prepared-qa.v1.yaml"))) !== summary.baseline_prepared_qa_sha256) {
  throw new Error("Existing catalog changed: recheck the pinned baseline before authoring.");
}
const authored: Authored[] = [];
for (const file of readdirSync(authoredDir).filter(f => /^authored-\d+\.json$/.test(f)).sort()) {
  authored.push(...JSON.parse(readFileSync(join(authoredDir, file), "utf8")).entries);
}
const existingIds = new Set(catalog.entries.map(e => e.id));
const owners = new Map<string, Set<string>>();
const register = (e: PreparedQaEntry) => {
  for (const q of e.questions) {
    const n = normalizePreparedQuestion(q, { defaultYear: 2026 });
    const set = owners.get(n) ?? new Set<string>();
    set.add(e.id);
    owners.set(n, set);
  }
};
for (const entry of catalog.entries) register(entry);
const counts = new Map<string, number>();
const sourceHashes = new Map<string, string>();
const problems: string[] = [];
for (const entry of authored) {
  const chunk = chunks.get(entry.chunk_id);
  if (!chunk) { problems.push(entry.id + ": unknown chunk"); continue; }
  if (existingIds.has(entry.id)) problems.push(entry.id + ": duplicate entry ID");
  existingIds.add(entry.id);
  if (entry.sources.length !== 1 || entry.sources[0] !== chunk.source ||
    entry.source_sha256 !== chunk.source_sha256) problems.push(entry.id + ": source identity mismatch");
  if (!sourceHashes.has(chunk.source)) {
    sourceHashes.set(chunk.source, sha(readFileSync(join(root, chunk.source))));
  }
  if (sourceHashes.get(chunk.source) !== chunk.source_sha256) problems.push(entry.id + ": source drift");
  if (!entry.review || entry.review.method !== "manual-context-review") {
    problems.push(entry.id + ": missing human context review");
  }
  const text = chunk.evidence.kind === "text" ? chunk.evidence.text! :
    JSON.stringify(chunk.evidence.units);
  if (!entry.evidence.length || entry.evidence.some(e => e.kind !== "quote" || !text.includes(e.text))) {
    problems.push(entry.id + ": unsupported quote");
  }
  if (entry.answer.length < 12 || entry.answer.length > 900 ||
    /(?:^|[\s「])(?:input|out|docs|scripts|backend)\//.test(entry.answer) ||
    /\b(?:None|unknown|mimeType|parentId)\b/.test(entry.answer) ||
    /コーチに直接聞いてください/.test(entry.answer)) problems.push(entry.id + ": answer quality");
  if (!entry.questions.length || entry.questions.some(q => !q.trim() || q.length > 180 ||
    classifyScope(q).kind !== "in_scope")) problems.push(entry.id + ": question scope or wording");
  for (const q of entry.questions) {
    const n = normalizePreparedQuestion(q, { defaultYear: 2026 });
    if (owners.has(n)) problems.push(entry.id + ": normalized question already owned by " + [...owners.get(n)!].join(", "));
  }
  register(entry);
  counts.set(entry.chunk_id, (counts.get(entry.chunk_id) ?? 0) + 1);
}
for (const [id, count] of counts) if (count !== 3) problems.push(id + ": must have exactly 3 authored entries");
let hits = 0;
if (!problems.length) {
  // Exercise the production cache and exact-match path against the complete
  // existing+candidate index; restore the tracked artifact byte-for-byte.
  const merged = {
    ...catalog, total: catalog.entries.length + authored.length,
    entries: [...catalog.entries, ...authored.map(e => ({
      id: e.id, questions: e.questions, answer: e.answer, sources: e.sources,
      tags: ["knowledge-chunk", "manual-context-reviewed"],
    }))],
  };
  try {
    writeFileSync(catalogPath, JSON.stringify(merged) + "\n");
    resetPreparedQaCache();
    for (const entry of authored) for (const q of entry.questions) {
      if (matchPreparedAnswer(q, { defaultYear: 2026 })?.id !== entry.id) {
        problems.push(entry.id + ": wrong production prepared match");
      } else hits += 1;
    }
  } finally {
    writeFileSync(catalogPath, original);
    resetPreparedQaCache();
  }
}
const pending = [...chunks.keys()].filter(id => counts.get(id) !== 3);
const report = {
  version: 1, baseline_count: catalog.entries.length, chunks: chunks.size,
  required_new_qa: chunks.size * 3, authored_candidates: authored.length,
  validated_candidates: problems.length ? 0 : authored.length,
  chunks_with_three_candidates: [...counts.values()].filter(c => c === 3).length,
  pending_chunks: pending.length, prepared_exact_hits: hits,
  problems, complete: !pending.length && !problems.length,
  limitations: ["Quote presence plus manual context review; not an automated proof of every prose proposition.",
    "Candidates remain unpublished until all chunks and independent final audits pass."],
};
writeFileSync(join(evidenceDir, "qa-progress.json"), JSON.stringify(report, null, 2) + "\n");
writeFileSync(join(evidenceDir, "pending-chunks.json"), JSON.stringify(pending, null, 2) + "\n");
process.stdout.write(JSON.stringify(report) + "\n");
if (problems.length) process.exitCode = 1;
