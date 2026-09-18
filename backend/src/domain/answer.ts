import { classifyScope, OUT_OF_SCOPE_MESSAGE } from "./scope.js";
import { expandDateQuery, parseDateMentions, resolveRelativeYears } from "./dates.js";
import { matchCannedAnswer } from "./canned.js";
import {
  detectMeetKind,
  isAragyokuCorpusSource,
  meetDriveTokens,
  meetResultPathBoost,
  type MeetKind,
} from "./meets.js";
import { routeSources } from "./router.js";
import type { LlmClient } from "./llm.js";
import { buildSystemPrompt, buildUserPrompt, MISSING_INFO_MESSAGE } from "../rag/prompt.js";
import { formatForLine } from "../line/format.js";
import {
  expandWithNeighbors,
  findSourcesContaining,
  mergeRetrieved,
  retrieveBySources,
  retrieveContext,
  truncateRetrieved,
  type RetrievedChunk,
} from "../rag/retrieve.js";
import { queryKnowledgeGraph, type KgQueryResult } from "../kg/query.js";

export type AnswerResult =
  | { kind: "refused"; text: string }
  | { kind: "answered"; text: string; sources: string[] }
  | { kind: "offline"; text: string; sources: string[] }
  | { kind: "error"; text: string };

export type AnswerDeps = {
  retrieve?: (question: string, topK?: number) => RetrievedChunk[];
  llm?: LlmClient | null;
  topK?: number;
  /** Inject KG query for tests */
  kgQuery?: (question: string) => KgQueryResult;
  /** Skip router LLM (use KG fallback sources) */
  skipRouter?: boolean;
  defaultYear?: number;
};

const DEFAULT_TOP_K = 16;
const DEFAULT_MAX_CHARS = 28000;
const DEFAULT_ROUTE_SOURCES = 14;
const DEFAULT_PER_SOURCE = 6;
const DEFAULT_MAX_CHUNKS = 28;

function offlineAnswer(question: string, retrieved: RetrievedChunk[]): string {
  const lines = ["（オフライン回答）", "", `Q: ${question}`, ""];
  if (retrieved.length === 0) {
    lines.push(MISSING_INFO_MESSAGE);
  } else {
    for (const [i, r] of retrieved.entries()) {
      const preview = r.chunk.text.replace(/\s+/g, " ").slice(0, 280);
      lines.push(`${i + 1}. ${preview}`);
    }
  }
  return formatForLine(lines.join("\n"));
}

function boostDateMeetSources(expandedQuery: string, baseSources: string[]): string[] {
  const mentions = parseDateMentions(expandedQuery);
  const out: string[] = [];
  const seen = new Set<string>();
  const push = (s: string) => {
    if (!s || seen.has(s)) return;
    seen.add(s);
    out.push(s);
  };

  if (mentions.length > 0) {
    push("calendar/events.daiming.yaml");
    const mmdds = mentions.map((m) => m.mmdd);
    for (const s of findSourcesContaining(mmdds, { prefix: "drive-text/大会/", limit: 12 })) {
      push(s);
    }
  }
  for (const s of baseSources) push(s);
  return out;
}

function sortMeetDriveSources(sources: string[], query: string): string[] {
  return [...sources].sort(
    (a, b) => meetResultPathBoost(b, query) - meetResultPathBoost(a, query),
  );
}

/**
 * Meet-aware source boost.
 * - 荒玉 / bare 駅伝 / 優勝・歴代 → aragyoku transcripts for resolved years
 * - ジュニア / なごみ 等の固有大会 → drive-text の該大会のみ（荒玉を先頭に入れない）
 */
function boostMeetYearSources(
  expandedQuery: string,
  baseSources: string[],
  defaultYear: number,
): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  const push = (s: string) => {
    if (!s || seen.has(s)) return;
    seen.add(s);
    out.push(s);
  };

  const kind: MeetKind = detectMeetKind(expandedQuery);
  const years = resolveRelativeYears(expandedQuery, defaultYear);
  const driveTokens = meetDriveTokens(kind);

  if (driveTokens.length > 0 && kind !== "aragyoku") {
    const driveHits = sortMeetDriveSources(
      findSourcesContaining(driveTokens, { prefix: "drive-text/大会/", limit: 16 }),
      expandedQuery,
    );
    for (const s of driveHits) {
      if (years.length === 0 || years.some((y) => s.includes(String(y)) || s.includes(`${y}年度`))) {
        push(s);
      }
    }
    // If year filter emptied the list (path uses 年度 folder), retry without year filter
    if (out.length === 0) {
      for (const s of driveHits) push(s);
    }
  }

  if (kind === "aragyoku") {
    push("aragyoku/winners-by-year.md");
    for (const y of years) {
      for (const g of ["男子", "女子"] as const) {
        push(`aragyoku/transcripts/${y}-${g}.json`);
        push(`aragyoku/ocr_raw/${y}-${g}.md`);
        push(`ekiden-ocr/${y}-${g}.md`);
      }
    }
    if (years.length === 0) {
      push("aragyoku");
    }
  }

  const rest =
    kind === "junior" || kind === "nagomi" || kind === "other"
      ? baseSources.filter((s) => !isAragyokuCorpusSource(s))
      : baseSources;
  for (const s of rest) push(s);
  return out;
}

function kgSuggestsInScope(kg: KgQueryResult): boolean {
  if (kg.matched_nodes.some((n) => n.score >= 4)) return true;
  if (
    kg.matched_nodes.some(
      (n) =>
        (n.type === "Athlete" || n.type === "Entity" || n.id.startsWith("meet:")) &&
        n.score >= 2,
    )
  ) {
    return true;
  }
  return kg.corpus_sources.length > 0 && kg.matched_nodes.length > 0;
}

export async function answerQuestion(
  question: string,
  deps: AnswerDeps = {},
): Promise<AnswerResult> {
  const year = deps.defaultYear ?? new Date().getFullYear();
  const expanded = expandDateQuery(question, year);
  const topK = deps.topK ?? DEFAULT_TOP_K;

  const canned = matchCannedAnswer(question);
  if (canned) {
    return {
      kind: "answered",
      text: formatForLine(canned.text),
      sources: [`canned:${canned.id}`],
    };
  }

  const kgQuery =
    deps.kgQuery ??
    ((q: string) => queryKnowledgeGraph(q, { topK: 16, expandHops: 2 }));
  const kg = kgQuery(expanded);

  let scope = classifyScope(question);
  if (
    scope.kind === "out_of_scope" &&
    !scope.hard &&
    kgSuggestsInScope(kg)
  ) {
    scope = { kind: "in_scope", reason: "kg_match" };
  }
  if (scope.kind === "out_of_scope") {
    return { kind: "refused", text: scope.message || OUT_OF_SCOPE_MESSAGE };
  }

  const route = deps.skipRouter
    ? {
        sources: boostMeetYearSources(
          expanded,
          boostDateMeetSources(expanded, kg.corpus_sources),
          year,
        ).slice(0, DEFAULT_ROUTE_SOURCES),
        focus: question,
        reason: "skip_router",
        via: "fallback" as const,
      }
    : await routeSources(expanded, kg, deps.llm);

  const preferredSources = boostMeetYearSources(
    expanded,
    boostDateMeetSources(expanded, route.sources),
    year,
  ).slice(0, DEFAULT_ROUTE_SOURCES);

  const fromSources = retrieveBySources(preferredSources, {
    query: expanded,
    perSource: DEFAULT_PER_SOURCE,
    maxChunks: DEFAULT_MAX_CHUNKS,
  });
  const retrieve = deps.retrieve ?? retrieveContext;
  const fromBm25 = retrieve(expanded, topK);
  const mergedCore = mergeRetrieved(fromSources, fromBm25, topK);
  const withNeighbors = expandWithNeighbors(mergedCore, { radius: 2, maxExtra: 32 });
  const merged = truncateRetrieved(withNeighbors, DEFAULT_MAX_CHARS);
  const sources = [
    ...new Set(
      merged.map((r) => {
        const m = r.chunk.source.match(/^(.*):\d+$/);
        return m ? m[1]! : r.chunk.source;
      }),
    ),
  ];

  if (!deps.llm) {
    return { kind: "offline", text: offlineAnswer(question, merged), sources };
  }

  try {
    const focusNote =
      route.focus && route.focus !== question ? `\n検索焦点: ${route.focus}` : "";
    const text = await deps.llm.complete(
      buildSystemPrompt(),
      buildUserPrompt(question + focusNote, merged),
    );
    return { kind: "answered", text: formatForLine(text), sources };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error("answerQuestion llm failed:", msg.slice(0, 300));
    return {
      kind: "error",
      text: "回答生成中にエラーが起きました。しばらくしてから、もう一度短い質問で試してください。",
    };
  }
}
