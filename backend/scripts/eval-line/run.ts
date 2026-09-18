/**
 * line-chats gap (~N) repo-grounded QA evaluation harness.
 *
 * Usage:
 *   cd backend && npx tsx scripts/eval-line/run.ts [--round N] [--retry-failed] [--concurrency 8]
 */
import { config as loadDotenv } from "dotenv";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadConfig, hasLlmCredentials } from "../../src/config.js";
import { createLlmClient } from "../../src/domain/llm.js";
import { answerQuestion, type AnswerResult } from "../../src/domain/answer.js";
import { MISSING_INFO_MESSAGE } from "../../src/rag/prompt.js";

loadDotenv();

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");
const DATA = join(ROOT, "data/eval-line");
const QUESTIONS_PATH = join(DATA, "questions.json");

type Expect = {
  kinds?: Array<"answered" | "refused" | "offline" | "error">;
  any_of?: string[];
  all_of?: string[];
  forbid?: string[];
  sources_any?: string[];
};

type Question = {
  id: string;
  q: string;
  expect: Expect;
};

type Round = {
  id: number;
  theme: string;
  questions: Question[];
};

type Bank = {
  version: number;
  total: number;
  defaultYear: number;
  rounds: Round[];
};

type CaseResult = {
  id: string;
  round: number;
  theme: string;
  q: string;
  pass: boolean;
  reasons: string[];
  kind: AnswerResult["kind"];
  text: string;
  sources: string[];
  ms: number;
};

function parseArgs(argv: string[]) {
  let round: number | null = null;
  let retryFailed = false;
  let concurrency = 4;
  let offline = false;
  let llm = false;
  let delayMs = 0;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]!;
    if (a === "--round") round = Number(argv[++i]);
    else if (a === "--retry-failed") retryFailed = true;
    else if (a === "--concurrency") concurrency = Number(argv[++i]);
    else if (a === "--offline") offline = true;
    else if (a === "--llm") llm = true;
    else if (a === "--delay-ms") delayMs = Number(argv[++i]);
  }
  // Default: grounded offline (repo excerpts). Use --llm for live model answers.
  if (!llm) offline = true;
  return { round, retryFailed, concurrency, offline, llm, delayMs };
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function norm(s: string): string {
  return s.normalize("NFKC");
}

function evaluate(result: AnswerResult, expect: Expect): { pass: boolean; reasons: string[] } {
  const reasons: string[] = [];
  const text = norm(result.text ?? "");
  const sources =
    result.kind === "answered" || result.kind === "offline" ? result.sources : [];

  if (expect.kinds && expect.kinds.length > 0 && !expect.kinds.includes(result.kind)) {
    reasons.push(`kind=${result.kind} not in [${expect.kinds.join(",")}]`);
  }

  if (expect.any_of && expect.any_of.length > 0) {
    const hit = expect.any_of.some((t) => text.includes(norm(t)));
    if (!hit) reasons.push(`missing any_of: ${expect.any_of.slice(0, 5).join("|")}`);
  }

  if (expect.all_of) {
    for (const t of expect.all_of) {
      if (!text.includes(norm(t))) reasons.push(`missing all_of: ${t}`);
    }
  }

  if (expect.forbid) {
    for (const t of expect.forbid) {
      if (text.includes(norm(t))) reasons.push(`forbid hit: ${t}`);
    }
  }

  if (expect.sources_any && expect.sources_any.length > 0) {
    const hit = expect.sources_any.some((p) => sources.some((s) => s.includes(p)));
    if (!hit) {
      reasons.push(
        `sources missing any of [${expect.sources_any.join("|")}]; got ${sources.slice(0, 5).join(",")}`,
      );
    }
  }

  return { pass: reasons.length === 0, reasons };
}

async function mapPool<T, R>(
  items: T[],
  concurrency: number,
  fn: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let next = 0;
  async function worker() {
    while (true) {
      const i = next++;
      if (i >= items.length) return;
      out[i] = await fn(items[i]!, i);
    }
  }
  await Promise.all(Array.from({ length: Math.max(1, concurrency) }, () => worker()));
  return out;
}

function loadFailedIds(): Set<string> {
  const path = join(DATA, "latest-failed.json");
  if (!existsSync(path)) return new Set();
  const ids = JSON.parse(readFileSync(path, "utf8")) as string[];
  return new Set(ids);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  mkdirSync(DATA, { recursive: true });

  const bank = JSON.parse(readFileSync(QUESTIONS_PATH, "utf8")) as Bank;
  let rounds = bank.rounds;
  if (args.round != null) {
    rounds = rounds.filter((r) => r.id === args.round);
  }

  let cases: Array<{ round: Round; question: Question }> = [];
  for (const round of rounds) {
    for (const question of round.questions) {
      cases.push({ round, question });
    }
  }

  if (args.retryFailed) {
    const failed = loadFailedIds();
    cases = cases.filter((c) => failed.has(c.question.id));
    console.log(`retry-failed: ${cases.length} cases`);
  }

  const config = loadConfig();
  const llmClient =
    args.offline || !args.llm ? null : createLlmClient(config);
  if (args.llm && !hasLlmCredentials(config)) {
    console.warn("WARN: --llm requested but no credentials; falling back to offline");
  }
  console.log(
    `eval start: ${cases.length} questions, concurrency=${args.concurrency}, llm=${Boolean(llmClient)}, year=${bank.defaultYear}`,
  );

  const results = await mapPool(cases, args.concurrency, async ({ round, question }) => {
    const t0 = Date.now();
    let result: AnswerResult = { kind: "error", text: "no result" };
    const expect: Expect = {
      ...question.expect,
      kinds: (() => {
        const base = question.expect.kinds ?? [];
        if (base.includes("answered") && !base.includes("offline")) {
          return [...new Set([...base, "offline" as const])];
        }
        return base;
      })(),
    };
    try {
      const maxAttempts = llmClient ? 4 : 1;
      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        if (args.delayMs > 0) await sleep(args.delayMs);
        result = await answerQuestion(question.q, {
          llm: llmClient,
          defaultYear: bank.defaultYear,
          skipRouter: !llmClient,
        });
        if (result.kind !== "error" || !llmClient) break;
        const wait = Math.min(60_000, 2_000 * 2 ** (attempt - 1));
        console.warn(`retry ${question.id} attempt=${attempt} wait=${wait}ms`);
        await sleep(wait);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      result = { kind: "error", text: msg };
    }
    const { pass, reasons } = evaluate(result, expect);
    const sources =
      result.kind === "answered" || result.kind === "offline" ? result.sources : [];
    const row: CaseResult = {
      id: question.id,
      round: round.id,
      theme: round.theme,
      q: question.q,
      pass,
      reasons,
      kind: result.kind,
      text: result.text.slice(0, 800),
      sources,
      ms: Date.now() - t0,
    };
    const mark = pass ? "PASS" : "FAIL";
    console.log(
      `[${mark}] ${question.id} (${row.ms}ms) ${question.q.slice(0, 40)}${reasons.length ? " :: " + reasons[0] : ""}`,
    );
    return row;
  });

  const passed = results.filter((r) => r.pass).length;
  const failed = results.filter((r) => !r.pass);
  const missingInfoHits = results.filter((r) =>
    norm(r.text).includes(norm(MISSING_INFO_MESSAGE.replace(/。$/, ""))),
  );
  // Only count as "false-ish coach refuse" when expect was answered/offline (not clarify/oos)
  const groundedExpected = results.filter((r) => {
    // recover expect kinds from bank is heavy; use pass+forbid pattern: non-refused kinds in id themes
    return r.kind !== "refused";
  });
  const missingInfoOnGrounded = missingInfoHits.filter((r) => r.kind !== "refused");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const outPath = join(DATA, `results-${stamp}.json`);
  const summary = {
    stamp,
    total: results.length,
    passed,
    failed: failed.length,
    passRate: results.length ? passed / results.length : 0,
    missingInfo: {
      count: missingInfoHits.length,
      rate: results.length ? missingInfoHits.length / results.length : 0,
      groundedCount: missingInfoOnGrounded.length,
      groundedRate: groundedExpected.length
        ? missingInfoOnGrounded.length / groundedExpected.length
        : 0,
      note: "Rate of answers containing コーチに直接聞いてください (MISSING_INFO_MESSAGE).",
    },
    byRound: Object.fromEntries(
      [...new Set(results.map((r) => r.round))].map((rid) => {
        const rs = results.filter((r) => r.round === rid);
        return [
          rid,
          {
            theme: rs[0]?.theme,
            passed: rs.filter((r) => r.pass).length,
            failed: rs.filter((r) => !r.pass).length,
          },
        ];
      }),
    ),
    results,
  };
  writeFileSync(outPath, JSON.stringify(summary, null, 2), "utf8");
  writeFileSync(join(DATA, "latest.json"), JSON.stringify(summary, null, 2), "utf8");
  writeFileSync(
    join(DATA, "latest-failed.json"),
    JSON.stringify(failed.map((f) => f.id), null, 2),
    "utf8",
  );
  writeFileSync(
    join(DATA, "latest-failed-detail.json"),
    JSON.stringify(failed, null, 2),
    "utf8",
  );
  writeFileSync(
    join(DATA, "latest-missing-info.json"),
    JSON.stringify(
      {
        count: missingInfoHits.length,
        rate: summary.missingInfo.rate,
        ids: missingInfoHits.map((r) => r.id),
      },
      null,
      2,
    ),
    "utf8",
  );

  console.log("\n=== SUMMARY ===");
  console.log(`passed ${passed}/${results.length} (${(summary.passRate * 100).toFixed(1)}%)`);
  console.log(
    `missingInfo ${missingInfoHits.length}/${results.length} (${(summary.missingInfo.rate * 100).toFixed(1)}%)` +
      ` [grounded ${missingInfoOnGrounded.length}/${groundedExpected.length}]`,
  );
  console.log(`wrote ${outPath}`);
  if (failed.length) {
    console.log("failed ids:", failed.map((f) => f.id).join(", "));
  }
  process.exitCode = failed.length ? 1 : 0;
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
