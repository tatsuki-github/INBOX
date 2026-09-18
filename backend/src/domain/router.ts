/** Router LLM: pick corpus sources from KG candidates. */

import type { LlmClient } from "./llm.js";
import type { KgQueryResult } from "../kg/query.js";
import { isAllowedCorpusSource } from "../kg/mapRefs.js";
import {
  detectMeetKind,
  isAragyokuCorpusSource,
  meetResultPathBoost,
} from "./meets.js";
import { RETRIEVAL_BUDGET } from "../rag/budget.js";

export type RouteDecision = {
  sources: string[];
  focus: string;
  reason: string;
  via: "llm" | "fallback";
};

function buildRouterSystemPrompt(): string {
  return [
    "あなたはリポジトリ知識コーパス Q&A の検索ルーターです。",
    "候補ソース一覧から、質問に答えるために読むべき source パスだけを選んでください。",
    "必ず次の JSON のみを返してください（説明文禁止）:",
    '{"sources":["corpus/相対パス"],"focus":"短い焦点","reason":"短い理由"}',
    `sources は候補に含まれるパスだけ。最大 ${RETRIEVAL_BUDGET.routeSources} 件。`,
    "日付質問なら calendar と該当大会フォルダを優先。",
    "ジュニア駅伝・なごみ・金栗など固有大会名があるときは drive-text/大会/ の該大会フォルダのみ選び、荒玉・aragyoku・ekiden-ocr は選ばない。",
    "明示の荒玉・優勝・歴代・区間・チーム順位なら aragyoku/transcripts・out-analysis/aragyoku-teams・winners-by-year・該当年 ekiden-ocr を優先。",
    "荒尾玉名の所属・トラック記録なら out-analysis/arato-tamana-teams と sb/ を優先。",
    "抜け漏れ防止のため関連ソースを多めに選ぶ。",
  ].join("\n");
}

function buildRouterUserPrompt(question: string, kg: KgQueryResult): string {
  const nodes = kg.matched_nodes
    .slice(0, 10)
    .map((n) => `- ${n.id} (${n.type}) ${n.label}: ${n.hint}`)
    .join("\n");
  const sources = kg.corpus_sources.slice(0, RETRIEVAL_BUDGET.routeSources).join("\n");
  return [
    `質問: ${question}`,
    "",
    "KG ヒット:",
    nodes || "(なし)",
    "",
    "候補 corpus sources:",
    sources || "(なし)",
  ].join("\n");
}

function parseRouterJson(raw: string): { sources: string[]; focus: string; reason: string } | null {
  const trimmed = raw.trim();
  const start = trimmed.indexOf("{");
  const end = trimmed.lastIndexOf("}");
  if (start < 0 || end <= start) return null;
  try {
    const obj = JSON.parse(trimmed.slice(start, end + 1)) as {
      sources?: unknown;
      focus?: unknown;
      reason?: unknown;
    };
    const sources = Array.isArray(obj.sources)
      ? obj.sources.filter((s): s is string => typeof s === "string")
      : [];
    return {
      sources,
      focus: typeof obj.focus === "string" ? obj.focus : "",
      reason: typeof obj.reason === "string" ? obj.reason : "",
    };
  } catch {
    return null;
  }
}

function sourcePreferScore(source: string, question: string): number {
  const years = [...question.matchAll(/\b(20\d{2})\b/g)].map((m) => m[1]!);
  const kind = detectMeetKind(question);
  let score = 0;

  if (kind === "junior" || kind === "nagomi" || kind === "other") {
    if (isAragyokuCorpusSource(source)) score -= 80;
    if (source.startsWith("drive-text/大会/")) score += 50;
    score += meetResultPathBoost(source, question);
    if (kind === "junior" && source.includes("ジュニア")) score += 70;
    if (kind === "nagomi" && /なごみ|金栗/.test(source)) score += 70;
  } else if (kind === "aragyoku") {
    if (source.includes("winners-by-year")) score += 80;
    if (source.startsWith("aragyoku/transcripts/")) score += 60;
    if (source.startsWith("aragyoku/")) score += 40;
    if (source === "aragyoku") score += 35;
    if (/優勝|歴代|荒玉/.test(question) && source.startsWith("ekiden-ocr/")) score += 10;
  }

  for (const y of years) {
    if (source.includes(y)) score += 50;
  }
  // Deprioritize old OCR years when the question already specifies a year
  if (years.length > 0 && source.startsWith("ekiden-ocr/") && !years.some((y) => source.includes(y))) {
    score -= 40;
  }
  if (/予定|大会/.test(question) && source.includes("calendar")) score += 30;
  return score;
}

function fallbackRoute(question: string, kg: KgQueryResult): RouteDecision {
  const sources = [...kg.corpus_sources];
  // Date / meet queries: always include calendar + drive-text 大会 when available via BM25 later;
  // ensure calendar is present if KG mapped it.
  if (!sources.includes("calendar/events.daiming.yaml") && /予定|大会|\d{1,2}\/\d{1,2}|月.*日/.test(question)) {
    sources.unshift("calendar/events.daiming.yaml");
  }
  sources.sort((a, b) => sourcePreferScore(b, question) - sourcePreferScore(a, question));
  return {
    sources: sources.slice(0, RETRIEVAL_BUDGET.routeSources),
    focus: question.slice(0, 80),
    reason: "kg_fallback",
    via: "fallback",
  };
}

export async function routeSources(
  question: string,
  kg: KgQueryResult,
  llm: LlmClient | null | undefined,
): Promise<RouteDecision> {
  const allow = new Set(kg.corpus_sources.filter(isAllowedCorpusSource));
  // Always allow calendar for schedule bots
  allow.add("calendar/events.daiming.yaml");

  if (!llm || kg.corpus_sources.length === 0) {
    return fallbackRoute(question, kg);
  }

  try {
    const raw = await llm.complete(
      buildRouterSystemPrompt(),
      buildRouterUserPrompt(question, kg),
    );
    const parsed = parseRouterJson(raw);
    if (!parsed) return fallbackRoute(question, kg);
    const sources = parsed.sources
      .map((s) => s.trim())
      .filter((s) => isAllowedCorpusSource(s) && (allow.has(s) || s.startsWith("drive-text/") || s.startsWith("notion-db/") || s.startsWith("ekiden-ocr/") || s.startsWith("aragyoku/") || s.startsWith("out-analysis/")))
      .slice(0, RETRIEVAL_BUDGET.routeSources);
    if (sources.length === 0) return fallbackRoute(question, kg);
    return {
      sources,
      focus: parsed.focus || question.slice(0, 80),
      reason: parsed.reason || "router",
      via: "llm",
    };
  } catch {
    return fallbackRoute(question, kg);
  }
}
