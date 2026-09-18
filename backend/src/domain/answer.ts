import { classifyScope, OUT_OF_SCOPE_MESSAGE } from "./scope.js";
import { expandDateQuery, parseDateMentions } from "./dates.js";
import { routeSources } from "./router.js";
import type { LlmClient } from "./llm.js";
import { buildSystemPrompt, buildUserPrompt } from "../rag/prompt.js";
import { formatForLine } from "../line/format.js";
import {
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

function offlineAnswer(question: string, retrieved: RetrievedChunk[]): string {
  const lines = ["（オフライン回答）", "", `Q: ${question}`, ""];
  if (retrieved.length === 0) {
    lines.push("コーパスに情報がありません。");
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
    for (const s of findSourcesContaining(mmdds, { prefix: "drive-text/大会/", limit: 6 })) {
      push(s);
    }
  }
  for (const s of baseSources) push(s);
  return out;
}

export async function answerQuestion(
  question: string,
  deps: AnswerDeps = {},
): Promise<AnswerResult> {
  const scope = classifyScope(question);
  if (scope.kind === "out_of_scope") {
    return { kind: "refused", text: scope.message || OUT_OF_SCOPE_MESSAGE };
  }

  const year = deps.defaultYear ?? new Date().getFullYear();
  const expanded = expandDateQuery(question, year);
  const topK = deps.topK ?? 8;

  const kgQuery = deps.kgQuery ?? ((q: string) => queryKnowledgeGraph(q));
  const kg = kgQuery(expanded);

  const route = deps.skipRouter
    ? {
        sources: boostDateMeetSources(expanded, kg.corpus_sources).slice(0, 8),
        focus: question,
        reason: "skip_router",
        via: "fallback" as const,
      }
    : await routeSources(expanded, kg, deps.llm);

  const preferredSources = boostDateMeetSources(expanded, route.sources).slice(0, 10);

  const fromSources = retrieveBySources(preferredSources, {
    query: expanded,
    perSource: 4,
    maxChunks: 12,
  });
  const retrieve = deps.retrieve ?? retrieveContext;
  const fromBm25 = retrieve(expanded, topK);
  const merged = truncateRetrieved(mergeRetrieved(fromSources, fromBm25, topK), 14000);
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
